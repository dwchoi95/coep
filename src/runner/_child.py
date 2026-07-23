"""Child process that executes one candidate program against a test suite.

Invoked by ``src.runner.testing.run_tests`` with a JSON payload path. Prints a
single JSON line: ``{passed, total, failures, error}``. Never raises out of the
student program: any exception becomes a failure record.
"""
import contextlib
import copy
import io
import json
import signal
import sys

# Algorithmic submissions recurse far deeper than CPython's default 1000;
# judges raise this, so a correct program must not be failed for it.
sys.setrecursionlimit(20000)


# ---------------------------------------------------------------- comparison
def _jsonable(x):
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (str, int, bool, float)) or x is None:
        return x
    return repr(x)


def _eq(a, b, tol):
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


def _num(tok):
    try:
        return float(tok)
    except (TypeError, ValueError):
        return None


def _stdout_eq(got, want, tol):
    """Judge-style comparison: whitespace-normalized, numeric tokens by tolerance."""
    g, w = got.split(), want.split()
    if len(g) != len(w):
        return False
    for a, b in zip(g, w):
        if a == b:
            continue
        fa, fb = _num(a), _num(b)
        if fa is None or fb is None or abs(fa - fb) > tol:
            return False
    return True


# ---------------------------------------------------------------- execution
def _run_call(src, entry, tests, tol, stop_early):
    ns = {}
    try:
        exec(compile(src, "<candidate>", "exec"), ns)
    except BaseException as e:  # syntax errors, import errors, top-level crashes
        return None, f"{type(e).__name__}: {e}"
    failures, passed = [], 0
    for i, t in enumerate(tests):
        fn = ns.get(t.get("entry", entry))
        if not callable(fn):
            failures.append({"index": i, "error": "NameError: entry not defined"})
            if stop_early:
                break
            continue
        args = copy.deepcopy(t.get("args", []))
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                got = fn(*args)
        except BaseException as e:
            failures.append({"index": i, "error": f"{type(e).__name__}: {e}"})
            if stop_early:
                break
            continue
        if _eq(_jsonable(got), _jsonable(t.get("expected")), tol):
            passed += 1
        else:
            failures.append({"index": i, "got": _jsonable(got),
                             "expected": _jsonable(t.get("expected"))})
            if stop_early:
                break
    return (passed, failures), None


class _Timeout(Exception):
    pass


def _make_stdin(text):
    """stdin that supports BOTH ``input()`` and ``sys.stdin.buffer.read()``.

    Competitive submissions routinely use the binary fast-I/O idiom, so a plain
    StringIO (no ``.buffer``) would mark correct programs as crashing.
    """
    return io.TextIOWrapper(io.BytesIO(text.encode()), encoding="utf-8",
                            newline=None)


def _run_stdio(src, tests, tol, stop_early, per_test):
    try:
        code = compile(src, "<candidate>", "exec")
    except BaseException as e:
        return None, f"{type(e).__name__}: {e}"
    failures, passed = [], 0
    real_stdin = sys.stdin

    def _alarm(signum, frame):
        raise _Timeout()

    have_timer = hasattr(signal, "setitimer")
    if have_timer:
        signal.signal(signal.SIGALRM, _alarm)

    for i, t in enumerate(tests):
        buf = io.StringIO()
        sys.stdin = _make_stdin(t.get("stdin", ""))
        if have_timer:
            signal.setitimer(signal.ITIMER_REAL, per_test)
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, {"__name__": "__main__"})
        except SystemExit:
            pass  # judge programs legitimately call exit()
        except _Timeout:
            failures.append({"index": i, "timeout": True})
            if stop_early:
                break
            continue
        except BaseException as e:
            failures.append({"index": i, "error": f"{type(e).__name__}: {e}"})
            if stop_early:
                break
            continue
        finally:
            if have_timer:
                signal.setitimer(signal.ITIMER_REAL, 0)
            sys.stdin = real_stdin
        got = buf.getvalue()
        if _stdout_eq(got, t.get("expected", ""), tol):
            passed += 1
        else:
            failures.append({"index": i, "got": got[:400],
                             "expected": str(t.get("expected", ""))[:400]})
            if stop_early:
                break
    sys.stdin = real_stdin
    return (passed, failures), None


def main():
    payload = json.load(open(sys.argv[1]))
    tests = payload["tests"]
    tol, stop_early = payload["tol"], payload["stop_early"]
    per_test = payload.get("per_test", 2.0)
    if payload["mode"] == "stdio":
        out, err = _run_stdio(payload["source"], tests, tol, stop_early, per_test)
    else:
        out, err = _run_call(payload["source"], payload["entry"], tests, tol, stop_early)
    if err is not None:
        print(json.dumps({"passed": 0, "total": len(tests), "failures": [], "error": err}))
        return
    passed, failures = out
    print(json.dumps({"passed": passed, "total": len(tests),
                      "failures": failures, "error": None}))


if __name__ == "__main__":
    main()
