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

DEFAULT_TIMEOUT = 10.0
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
    if problem.get("mode") in ("call", "stdio"):
        return problem["mode"]
    tests = problem.get("tests") or []
    if tests and "stdin" in tests[0]:
        return "stdio"
    return "call"


def run_tests(source: str, problem: dict, timeout: float = DEFAULT_TIMEOUT,
              stop_early: bool = False) -> TestResult:
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
    }
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


def passes(source: str, problem: dict, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """True iff ``source`` passes every test. Used by generated tools."""
    return run_tests(source, problem, timeout=timeout, stop_early=True).all_pass


def load_problem(pid: str, root: str | Path = "data") -> dict:
    return json.loads((Path(root) / pid / "problem.json").read_text())
