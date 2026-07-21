```python
"""Local, LLM-free automatic repair for the `fibonacci(n)` assignment.

Strategy:
  1. Enumerate candidate fixes: the original program, problem-specific AST
     rewrites targeting the classic misconceptions for this assignment
     (wrong return variable, wrong list/pair initialization, off-by-one loop
     bounds, `seq[-1]` vs `seq[n]`, sequential instead of simultaneous
     assignment, misspelled function name), their pairwise compositions with
     each other and with the generic 1-edit search, and finally the generic
     2-edit search.
  2. Pre-filter every candidate with a step/time-limited sandboxed run of the
     full visible test suite (protects against infinite loops / recursion).
  3. Hand only surviving candidates to `first_passing`, which enforces the
     test suite and the patch-size cap (rps <= 0.35) authoritatively.
"""

import ast
import contextlib
import io
import sys
import time

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "fibonacci"

TESTS = [
    {"args": [0], "expected": 0},
    {"args": [1], "expected": 1},
    {"args": [2], "expected": 1},
    {"args": [3], "expected": 2},
    {"args": [4], "expected": 3},
    {"args": [5], "expected": 5},
    {"args": [6], "expected": 8},
    {"args": [7], "expected": 13},
    {"args": [8], "expected": 21},
    {"args": [10], "expected": 55},
    {"args": [12], "expected": 144},
    {"args": [15], "expected": 610},
    {"args": [20], "expected": 6765},
    {"args": [24], "expected": 46368},
]


class _StepLimit(Exception):
    pass


def _run_limited(fn, args, max_events, max_seconds):
    """Run fn(*args) under a settrace-based event and wall-clock limit."""
    state = {"n": 0}
    stop_at = time.monotonic() + max_seconds

    def tracer(frame, event, arg):
        state["n"] += 1
        if state["n"] > max_events:
            raise _StepLimit()
        if (state["n"] & 1023) == 0 and time.monotonic() > stop_at:
            raise _StepLimit()
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        return fn(*args)
    finally:
        sys.settrace(old)


def _passes_guarded(src, deadline):
    """True iff `src` defines a callable ENTRY passing all TESTS, safely."""
    try:
        code = compile(src, "<candidate>", "exec")
    except Exception:
        return False
    ns = {"__name__": "__student__", "input": lambda *a, **k: ""}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            _run_limited(exec, (code, ns), 20000, 0.5)
    except Exception:
        return False
    fn = ns.get(ENTRY)
    if not callable(fn):
        return False
    for t in TESTS:  # ascending n: cheap tests reject bad candidates fast
        n = t["args"][0]
        if n > 12 and time.monotonic() > deadline + 1.0:
            return False
        ev, sec = (60000, 0.6) if n <= 12 else (2500000, 2.5)
        try:
            with contextlib.redirect_stdout(buf):
                got = _run_limited(fn, list(t["args"]), ev, sec)
        except Exception:
            return False
        try:
            ok = (got == t["expected"]) and isinstance(got, int)
        except Exception:
            return False
        if not ok:
            return False
    return True


def _is_const_int(e):
    if isinstance(e, ast.Constant) and isinstance(e.value, int):
        return True
    if (isinstance(e, ast.UnaryOp) and isinstance(e.op, (ast.USub, ast.UAdd))
            and isinstance(e.operand, ast.Constant)
            and isinstance(e.operand.value, int)):
        return True
    return False


def _targeted(source):
    """Problem-specific single rewrites for this assignment. Never raises."""
    out = []
    try:
        base = ast.parse(source)
        base_text = ast.unparse(base)
    except Exception:
        return out
    try:
        nodes = list(ast.walk(base))
        seen = set()

        func = None
        for nd in nodes:
            if isinstance(nd, ast.FunctionDef) and nd.name == ENTRY:
                func = nd
                break
        if func is None:
            for nd in nodes:
                if isinstance(nd, ast.FunctionDef):
                    func = nd
                    break

        param = "n"
        if func is not None and getattr(func.args, "args", None):
            param = func.args.args[0].arg

        scope = func if func is not None else base
        assigned = set()
        listvars = set()
        for nd in ast.walk(scope):
            if isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Store):
                assigned.add(nd.id)
            if isinstance(nd, ast.Assign) and isinstance(nd.value, ast.List):
                for tgt in nd.targets:
                    if isinstance(tgt, ast.Name):
                        listvars.add(tgt.id)
        assigned.discard("_")

        def add(text):
            if text and text != base_text and text not in seen:
                seen.add(text)
                out.append(text)

        def expr(text):
            return ast.parse(text, mode="eval").body

        def variant(idx, fix):
            try:
                tree = ast.parse(source)
                node = list(ast.walk(tree))[idx]
                if not fix(node):
                    return
                ast.fix_missing_locations(tree)
                add(ast.unparse(tree))
            except Exception:
                pass

        # Misspelled / wrongly named function -> rename to ENTRY everywhere.
        for nd in nodes:
            if isinstance(nd, ast.FunctionDef) and nd.name != ENTRY:
                old = nd.name
                try:
                    tree = ast.parse(source)
                    for sub in ast.walk(tree):
                        if isinstance(sub, ast.FunctionDef) and sub.name == old:
                            sub.name = ENTRY
                        elif isinstance(sub, ast.Name) and sub.id == old:
                            sub.id = ENTRY
                    ast.fix_missing_locations(tree)
                    add(ast.unparse(tree))
                except Exception:
                    pass

        for i, node in enumerate(nodes):
            # 1) Return-expression fixes: wrong variable, seq[-1] vs seq[n],
            #    returning a bare list, or a constant instead of n.
            if isinstance(node, ast.Return) and node.value is not None:
                repls = set()
                if isinstance(node.value, ast.Name):
                    for other in assigned:
                        if other != node.value.id:
                            repls.add(other)
                    if node.value.id in listvars:
                        for ix in (param, "-1"):
                            repls.add("%s[%s]" % (node.value.id, ix))
                if (isinstance(node.value, ast.Subscript)
                        and isinstance(node.value.value, ast.Name)):
                    bv = node.value.value.id
                    for ix in (param, "-1", "-2", "0",
                               param + " - 1", param + " + 1"):
                        repls.add("%s[%s]" % (bv, ix))
                if (isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, int)):
                    repls.add(param)
                for r in sorted(repls):
                    def fix(nd, r=r):
                        if not isinstance(nd, ast.Return) or nd.value is None:
                            return False
                        nd.value = expr(r)
                        return True
                    variant(i, fix)

            # 2) Wrong seed list, e.g. [1, 1] or [-1, 1] -> [0, 1].
            if (isinstance(node, ast.List) and isinstance(node.ctx, ast.Load)
                    and 2 <= len(node.elts) <= 3
                    and all(_is_const_int(e) for e in node.elts)):
                def fixlist(nd):
                    if not (isinstance(nd, ast.List)
                            and 2 <= len(nd.elts) <= 3):
                        return False
                    if len(nd.elts) == 2:
                        nd.elts = [ast.Constant(0), ast.Constant(1)]
                    else:
                        nd.elts = [ast.Constant(0), ast.Constant(1),
                                   ast.Constant(1)]
                    return True
                variant(i, fixlist)

            # 3) Wrong constant pair init, e.g. a, b = 1, 1 -> a, b = 0, 1.
            if (isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Tuple)
                    and len(node.value.elts) == 2
                    and all(_is_const_int(e) for e in node.value.elts)):
                def fixtup(nd):
                    if not (isinstance(nd, ast.Assign)
                            and isinstance(nd.value, ast.Tuple)
                            and len(nd.value.elts) == 2):
                        return False
                    nd.value.elts = [ast.Constant(0), ast.Constant(1)]
                    return True
                variant(i, fixtup)

            # 4) Loop-count off-by-one: retune the range() stop expression.
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "range"
                    and 1 <= len(node.args) <= 2 and not node.keywords):
                argpos = len(node.args) - 1
                try:
                    cur = ast.unparse(node.args[argpos])
                except Exception:
                    cur = ""
                for newtext in (param, param + " - 1",
                                param + " + 1", param + " - 2"):
                    if newtext == cur:
                        continue
                    def fixrange(nd, newtext=newtext, argpos=argpos):
                        if not (isinstance(nd, ast.Call)
                                and len(nd.args) >= argpos + 1):
                            return False
                        nd.args[argpos] = expr(newtext)
                        return True
                    variant(i, fixrange)

            # 5) While-bound fixes: < vs <= and bound shifted by one.
            if (isinstance(node, ast.While)
                    and isinstance(node.test, ast.Compare)
                    and len(node.test.ops) == 1):
                for newop in (ast.Lt, ast.LtE):
                    if isinstance(node.test.ops[0], newop):
                        continue
                    def fixop(nd, newop=newop):
                        if not (isinstance(nd, ast.While)
                                and isinstance(nd.test, ast.Compare)
                                and len(nd.test.ops) == 1):
                            return False
                        nd.test.ops = [newop()]
                        return True
                    variant(i, fixop)
                try:
                    cur = ast.unparse(node.test.comparators[0])
                except Exception:
                    cur = ""
                if cur:
                    for delta in (" + 1", " - 1"):
                        def fixcmp(nd, cur=cur, delta=delta):
                            if not (isinstance(nd, ast.While)
                                    and isinstance(nd.test, ast.Compare)
                                    and len(nd.test.ops) == 1):
                                return False
                            nd.test.comparators[0] = expr(
                                "(" + cur + ")" + delta)
                            return True
                        variant(i, fixcmp)

            # 6) Sequential updates (a = b; b = a + b) -> simultaneous
            #    tuple assignment inside a loop body.
            if isinstance(node, (ast.For, ast.While)):
                for j in range(len(node.body) - 1):
                    s1, s2 = node.body[j], node.body[j + 1]
                    if (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)
                            and len(s1.targets) == 1 and len(s2.targets) == 1
                            and isinstance(s1.targets[0], ast.Name)
                            and isinstance(s2.targets[0], ast.Name)
                            and s1.targets[0].id != s2.targets[0].id):
                        def fixmerge(nd, j=j):
                            if (not isinstance(nd, (ast.For, ast.While))
                                    or len(nd.body) < j + 2):
                                return False
                            a, b = nd.body[j], nd.body[j + 1]
                            if not (isinstance(a, ast.Assign)
                                    and isinstance(b, ast.Assign)
                                    and len(a.targets) == 1
                                    and len(b.targets) == 1):
                                return False
                            merged = ast.Assign(
                                targets=[ast.Tuple(
                                    elts=[a.targets[0], b.targets[0]],
                                    ctx=ast.Store())],
                                value=ast.Tuple(
                                    elts=[a.value, b.value], ctx=ast.Load()))
                            nd.body[j:j + 2] = [merged]
                            return True
                        variant(i, fixmerge)
    except Exception:
        pass
    return out


def _safe_iter(make_iter):
    """Iterate a generator factory, swallowing any exception it raises."""
    try:
        it = iter(make_iter())
    except Exception:
        return
    while True:
        try:
            item = next(it)
        except StopIteration:
            return
        except Exception:
            return
        yield item


def _candidate_stream(source):
    # Priority order: original, targeted fixes, generic 1-edit, targeted
    # pairs, targeted + generic 1-edit, generic 2-edit.
    yield source
    targeted = _targeted(source)
    for t in targeted:
        yield t
    yield from _safe_iter(lambda: candidates_generic(source, max_edits=1))
    for t in targeted:
        for t2 in _targeted(t):
            yield t2
    for t in targeted:
        yield from _safe_iter(
            lambda t=t: candidates_generic(t, max_edits=1))
    yield from _safe_iter(
        lambda: candidates_generic(source, max_edits=2, budget=4000))


def _passing_stream(source, deadline):
    """Yield only deduplicated candidates that pass the guarded test run."""
    seen = set()
    checked = 0
    for cand in _candidate_stream(source):
        if time.monotonic() > deadline or checked > 20000:
            return
        if not isinstance(cand, str):
            try:
                cand = str(cand)
            except Exception:
                continue
        key = cand.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        checked += 1
        if _passes_guarded(cand, deadline):
            yield cand


def repair(source):
    try:
        if not isinstance(source, str) or not source.strip():
            return None
        try:
            ast.parse(source)
        except Exception:
            return None
        deadline = time.monotonic() + 6.0
        result = first_passing(
            _passing_stream(source, deadline), ENTRY, TESTS, source)
        if result is None:
            return None
        if isinstance(result, str):
            return result
        return str(result)
    except Exception:
        return None
```
