"""Sandboxed execution of candidate programs against a problem's test suite.

Each problem defines a single entry function. A test case is
``{"args": [...], "expected": ...}``; results are compared after JSON
normalization (so tuples and lists compare equal) with a small float
tolerance. All tests for one program run in a single subprocess with a
wall-clock timeout, so infinite loops in student code cannot hang the
harness.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

RUNNER = r'''
import json, sys, copy, io, contextlib

def _normalize(x):
    return json.loads(json.dumps(_jsonable(x)))

def _jsonable(x):
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (str, int, bool)) or x is None:
        return x
    if isinstance(x, float):
        return x
    return repr(x)

def _eq(a, b, tol=1e-6):
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= tol
        except (TypeError, ValueError):
            return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_eq(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_eq(a[k], b[k], tol) for k in a)
    return a == b

def main():
    payload = json.load(open(sys.argv[1]))
    src, entry, tests = payload["source"], payload["entry"], payload["tests"]
    ns = {}
    results = []
    try:
        exec(compile(src, "<student>", "exec"), ns)
    except BaseException as e:
        print(json.dumps({"error": "compile/exec: %s" % e, "results": []}))
        return
    fn = ns.get(entry)
    if not callable(fn):
        print(json.dumps({"error": "missing entry function %r" % entry, "results": []}))
        return
    for t in tests:
        args = copy.deepcopy(t["args"])
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                out = fn(*args)
            got = _normalize(out)
            ok = _eq(got, t["expected"])
            results.append({"ok": bool(ok), "got": got})
        except BaseException as e:
            results.append({"ok": False, "got": None, "error": "%s: %s" % (type(e).__name__, e)})
    print(json.dumps({"error": None, "results": results}))

main()
'''


@dataclass
class RunResult:
    compiled: bool
    passed: int
    total: int
    failures: list = field(default_factory=list)  # per failing test: {index, args, expected, got/error}
    error: str | None = None
    timeout: bool = False

    @property
    def all_pass(self) -> bool:
        return self.compiled and not self.timeout and self.passed == self.total


def run_tests_inproc(source: str, entry: str, tests: list[dict],
                     timeout: float = 1.5) -> RunResult:
    """Fast in-process variant for candidate search inside repairers.

    Uses SIGALRM for the timeout, so it must run on the main thread (true for
    repairer subprocesses). Final evaluation always uses the subprocess-based
    `run_tests`.
    """
    import contextlib
    import copy
    import io
    import json as _json
    import signal

    def _jsonable(x):
        if isinstance(x, (list, tuple)):
            return [_jsonable(v) for v in x]
        if isinstance(x, dict):
            return {str(k): _jsonable(v) for k, v in x.items()}
        if isinstance(x, (str, int, bool, float)) or x is None:
            return x
        return repr(x)

    def _eq(a, b, tol=1e-6):
        if isinstance(a, float) or isinstance(b, float):
            try:
                return abs(float(a) - float(b)) <= tol
            except (TypeError, ValueError):
                return False
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(_eq(x, y, tol) for x, y in zip(a, b))
        return a == b

    def _on_alarm(signum, frame):
        raise TimeoutError

    ns: dict = {}
    old = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        try:
            exec(compile(source, "<student>", "exec"), ns)
        except BaseException as e:
            return RunResult(compiled=False, passed=0, total=len(tests), error=str(e))
        fn = ns.get(entry)
        if not callable(fn):
            return RunResult(compiled=False, passed=0, total=len(tests),
                             error=f"missing entry function {entry!r}")
        passed = 0
        failures = []
        for i, t in enumerate(tests):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    out = fn(*copy.deepcopy(t["args"]))
                got = _json.loads(_json.dumps(_jsonable(out)))
                if _eq(got, t["expected"]):
                    passed += 1
                else:
                    failures.append({"index": i, "args": t["args"],
                                     "expected": t["expected"], "got": got})
            except TimeoutError:
                return RunResult(compiled=True, passed=passed, total=len(tests),
                                 failures=failures, timeout=True, error="timeout")
            except BaseException as e:
                failures.append({"index": i, "args": t["args"], "expected": t["expected"],
                                 "got": None, "error": f"{type(e).__name__}: {e}"})
        return RunResult(compiled=True, passed=passed, total=len(tests), failures=failures)
    except TimeoutError:
        return RunResult(compiled=False, passed=0, total=len(tests), timeout=True,
                         error="timeout during exec")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def run_tests(source: str, entry: str, tests: list[dict], timeout: float = 6.0) -> RunResult:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"source": source, "entry": entry, "tests": tests}, f)
        payload_path = f.name
    try:
        proc = subprocess.run(
            [sys.executable, "-c", RUNNER, payload_path],
            capture_output=True, text=True, timeout=timeout,
            env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"},
        )
    except subprocess.TimeoutExpired:
        return RunResult(compiled=True, passed=0, total=len(tests), timeout=True,
                         error="timeout after %.1fs" % timeout)
    finally:
        os.unlink(payload_path)
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    try:
        out = json.loads(line)
    except json.JSONDecodeError:
        return RunResult(compiled=False, passed=0, total=len(tests),
                         error="runner crash: %s" % (proc.stderr[-500:] or proc.stdout[-500:]))
    if out["error"]:
        return RunResult(compiled=False, passed=0, total=len(tests), error=out["error"])
    failures = []
    passed = 0
    for i, (t, r) in enumerate(zip(tests, out["results"])):
        if r["ok"]:
            passed += 1
        else:
            failures.append({"index": i, "args": t["args"], "expected": t["expected"],
                             "got": r.get("got"), "error": r.get("error")})
    return RunResult(compiled=True, passed=passed, total=len(tests), failures=failures)
