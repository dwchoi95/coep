"""Shared test runner for candidate programs.

Two execution models are supported, because assignment corpora use both:

* ``call``  — the problem designates an entry function; a test is
  ``{"args": [...], "expected": ...}`` and the return value is compared after
  JSON normalization with a float tolerance. Individual tests may override the
  callee with ``"entry"`` (assignments that require several functions).
  This is the Refactory-style model.

* ``stdio`` — the program reads stdin and writes stdout; a test is
  ``{"stdin": "...", "expected": "..."}`` and stdout is compared after
  whitespace normalization, with a float tolerance applied token-wise.
  This is the online-judge model used by CodeNet/LSGen, where 99% of
  submissions read stdin.

The mode is declared per problem (``problem.json: {"mode": "call"|"stdio"}``)
and inferred when absent. All tests for one program run in a single
subprocess with a wall-clock timeout, so infinite loops cannot hang the
harness. Generated tools import this module so that a tool's own validation
and the evaluation harness apply exactly the same oracle.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PER_TEST_TIMEOUT = 2.0   # judge-style per-test wall clock
TIMEOUT_OVERHEAD = 5.0   # interpreter start-up + I/O
FLOAT_TOL = 1e-6

_RUNNER = Path(__file__).with_name("_child.py")


@dataclass
class TestResult:
    """Outcome of running one program against a whole suite."""
    passed: int = 0
    total: int = 0
    failures: list[dict] = field(default_factory=list)
    error: str | None = None
    seconds: float = 0.0

    @property
    def all_pass(self) -> bool:
        return self.error is None and self.total > 0 and self.passed == self.total

    def signature(self) -> tuple[str, ...]:
        """Per-test outcome classes, used as the behavioural clustering view.

        One entry per test in suite order: ``pass``, ``wrong``, ``timeout`` or
        ``err:<ExceptionName>``.
        """
        cls = ["pass"] * self.total
        for f in self.failures:
            i = f.get("index")
            if i is None or not (0 <= i < self.total):
                continue
            if f.get("timeout"):
                cls[i] = "timeout"
            elif f.get("error"):
                cls[i] = "err:" + str(f["error"]).split(":", 1)[0].split("(")[0].strip()
            else:
                cls[i] = "wrong"
        return tuple(cls)


def infer_mode(problem: dict) -> str:
    """Execution model for a problem; explicit field wins, else inferred."""
    if problem.get("mode") in ("call", "stdio", "file"):
        return problem["mode"]
    tests = problem.get("tests") or []
    if tests and "stdin" in tests[0]:
        return "stdio"
    return "call"


def _budget(n_tests: int, per_test: float) -> float:
    """Harness timeout scaled to the suite; one hung test cannot eat the rest."""
    return min(per_test * max(1, n_tests) + TIMEOUT_OVERHEAD, 180.0)


def run_tests(source: str, problem: dict, timeout: float | None = None,
              stop_early: bool = False, per_test: float = PER_TEST_TIMEOUT) -> TestResult:
    """Run ``source`` against ``problem['tests']`` in a fresh subprocess.

    ``stop_early`` returns as soon as one test fails, which is what the
    rule-combination search wants (it only needs pass/fail); the evaluation
    harness leaves it off so that the full failure signature is available for
    clustering and diagnosis.
    """
    payload = {
        "source": source,
        "mode": infer_mode(problem),
        "entry": problem.get("entry"),
        "tests": problem.get("tests") or [],
        "stop_early": bool(stop_early),
        "tol": FLOAT_TOL,
        "per_test": per_test,
    }
    if timeout is None:
        timeout = _budget(len(payload["tests"]), per_test)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(payload, fh)
        path = fh.name
    import time
    t0 = time.time()
    try:
        proc = subprocess.run([sys.executable, str(_RUNNER), path],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return TestResult(total=len(payload["tests"]), error="harness timeout",
                          seconds=time.time() - t0)
    finally:
        Path(path).unlink(missing_ok=True)
    elapsed = time.time() - t0
    line = (proc.stdout or "").strip().splitlines()
    if not line:
        return TestResult(total=len(payload["tests"]),
                          error=f"no output ({(proc.stderr or '')[-200:]})",
                          seconds=elapsed)
    try:
        out = json.loads(line[-1])
    except json.JSONDecodeError:
        return TestResult(total=len(payload["tests"]),
                          error="unparseable runner output", seconds=elapsed)
    res = TestResult(passed=out.get("passed", 0), total=out.get("total", 0),
                     failures=out.get("failures", []), error=out.get("error"),
                     seconds=elapsed)
    return res


def run_batch(sources: list[str], problem: dict,
              per_candidate_timeout: float = 3.0,
              per_test: float = PER_TEST_TIMEOUT,
              max_pass: int = 1) -> list[bool]:
    """Test many candidate programs in ONE child process; return all_pass each.

    Spawning a subprocess per candidate dominates repair time when a search
    tries hundreds of candidates. The child stops once ``max_pass`` candidates
    have passed every test, so ``max_pass=1`` returns at the first hit (the
    search wants one), while a larger value collects several passing candidates
    (e.g. to pick the smallest-RPS among them). Order candidates best-first.
    """
    if not sources:
        return []
    payload = {
        "batch": True,
        "sources": sources,
        "mode": infer_mode(problem),
        "entry": problem.get("entry"),
        "tests": problem.get("tests") or [],
        "tol": FLOAT_TOL,
        "per_test": per_test,
        "max_pass": max_pass,
    }
    # whole-batch wall clock: at most one full candidate budget past the first
    # hit, bounded so a pathological batch cannot hang the search.
    timeout = min(per_candidate_timeout * len(sources)
                  + _budget(len(payload["tests"]), per_test), 300.0)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(payload, fh)
        path = fh.name
    try:
        proc = subprocess.run([sys.executable, str(_RUNNER), path],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return [False] * len(sources)
    finally:
        Path(path).unlink(missing_ok=True)
    line = (proc.stdout or "").strip().splitlines()
    if not line:
        return [False] * len(sources)
    try:
        out = json.loads(line[-1])
    except json.JSONDecodeError:
        return [False] * len(sources)
    flags = out.get("pass", [])
    return (flags + [False] * len(sources))[:len(sources)]


def passes(source: str, problem: dict, timeout: float | None = None) -> bool:
    """True iff ``source`` passes every test. Used by generated tools."""
    return run_tests(source, problem, timeout=timeout, stop_early=True).all_pass


def load_problem(pid: str, root: str | Path = "data") -> dict:
    return json.loads((Path(root) / pid / "problem.json").read_text())
