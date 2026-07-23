```python
"""Local, LLM-free automatic repair for the gcd assignment (round 2).

Root-cause analysis of the round-1 failures (all "no_patch", including
mutant_06 whose fix `b != 1` -> `b == 0` was *provably generated* by the
problem-specific rewriter):

  1. The single validation call `first_passing(..., max_rps=..., max_checks=...)`
     was wrapped in a bare try/except that returned None.  If that call
     raises for any reason (e.g. an unexpected keyword argument such as
     `max_checks`, or a different positional arity), EVERY submission
     silently becomes "no_patch" -- exactly the observed outcome.  The fix:
     try a ladder of call signatures (full kwargs -> fewer kwargs -> bare),
     rebuilding a fresh candidate stream for each attempt, and only give up
     after all of them fail; as a last resort validate candidates locally
     (subprocess with timeout, then a step-limited in-process runner).
     The relative-patch-size cap (0.35) is additionally enforced inside the
     candidate stream itself via coep.evaluate.rps, so the cap holds no
     matter which signature variant ends up being used.

  2. `_int_const_compares` only matched `ast.Constant` comparators, but the
     AST for `b != -1` (mutant_01) is `UnaryOp(USub, Constant(1))`, so the
     negative-constant base case was invisible to the rewriter.  Now
     negative literals (and constants on the left side) are recognised.

  3. Missing rules for two whole bug families:
       - swapped non-commutative binop operands, e.g. `temp = b % a`
         instead of `a % b` (crafted_03);
       - "forgot to recurse": computing the remainder but returning it
         directly instead of `return gcd(b, remainder)` (crafted_07).
     Both are added as targeted, cheap AST rewrites, together with an
     explicit comparison-operator flip (`while a == b` -> `while a != b`,
     mutant_07) so none of these depend on the generic edit search.

Everything is validated through `first_passing` (full visible test suite +
patch-size cap) whenever it is callable; candidates are deduplicated and
ordered original -> problem-specific -> generic 1-edit -> generic 2-edit so
repairs stay as close as possible to the student's own approach.
"""

import ast
import subprocess
import sys

try:
    from coep.repairlib import first_passing as _first_passing
except Exception:
    _first_passing = None
try:
    from coep.repairlib import candidates_generic as _candidates_generic
except Exception:
    _candidates_generic = None
try:
    from coep.evaluate import rps as _rps
except Exception:
    _rps = None

ENTRY = "gcd"

TESTS = [
    {"args": [48, 18], "expected": 6},
    {"args": [18, 48], "expected": 6},
    {"args": [0, 5], "expected": 5},
    {"args": [5, 0], "expected": 5},
    {"args": [0, 0], "expected": 0},
    {"args": [7, 7], "expected": 7},
    {"args": [1, 999], "expected": 1},
    {"args": [12, 8], "expected": 4},
    {"args": [100, 75], "expected": 25},
    {"args": [13, 17], "expected": 1},
    {"args": [270, 192], "expected": 6},
    {"args": [1000000, 999999], "expected": 1},
    {"args": [36, 60], "expected": 12},
    {"args": [2, 4], "expected": 2},
]

MAX_RPS = 0.35


# ---------------------------------------------------------------------------
# Patch-size guard (defensive: unknown argument order -> take the min of
# both orders; if rps itself is unusable, defer entirely to first_passing).
# ---------------------------------------------------------------------------

def _rps_ok(original, candidate):
    if candidate == original:
        return True
    if _rps is None:
        return True
    vals = []
    for x, y in ((original, candidate), (candidate, original)):
        try:
            v = _rps(x, y)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vals.append(float(v))
        except Exception:
            pass
    if not vals:
        return True
    return min(vals) <= MAX_RPS + 1e-9


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _int_const(node):
    """Int value of a literal, including negative literals like -1; else None."""
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    ):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, int)
        and not isinstance(node.operand.value, bool)
    ):
        return -node.operand.value
    return None


def _variants(source, collect, mutators):
    """Yield one rewritten source per (site, mutator), each on a fresh parse."""
    try:
        count = len(collect(ast.parse(source)))
    except Exception:
        return
    for i in range(count):
        for mutate in mutators:
            try:
                tree = ast.parse(source)
                nodes = collect(tree)
                if i >= len(nodes):
                    continue
                if mutate(nodes[i]) is False:
                    continue
                ast.fix_missing_locations(tree)
                yield ast.unparse(tree)
            except Exception:
                continue


# --- rule 1: botched integer base cases -> {==,!=} x {0,1} -----------------

def _collect_const_compares(tree):
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and len(node.comparators) == 1
        ):
            if (
                _int_const(node.comparators[0]) is not None
                or _int_const(node.left) is not None
            ):
                out.append(node)
    return out


def _const_compare_mutators():
    muts = []
    for op_cls in (ast.Eq, ast.NotEq):
        for cval in (0, 1):
            def mutate(node, _op=op_cls, _c=cval):
                node.ops[0] = _op()
                if _int_const(node.comparators[0]) is not None:
                    node.comparators[0] = ast.Constant(_c)
                else:
                    node.left = ast.Constant(_c)
                return True
            muts.append(mutate)
    return muts


# --- rule 2: flipped comparison operators (e.g. while a == b) --------------

_CMP_ALTS = (ast.Eq, ast.NotEq, ast.Lt, ast.Gt, ast.LtE, ast.GtE)


def _collect_compares(tree):
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Compare) and len(n.ops) == 1
    ]


def _compare_op_mutators():
    muts = []
    for op_cls in _CMP_ALTS:
        def mutate(node, _op=op_cls):
            if isinstance(node.ops[0], _op):
                return False
            node.ops[0] = _op()
            return True
        muts.append(mutate)
    return muts


# --- rule 3: swapped operands of non-commutative binops (b % a) ------------

_NONCOMMUTATIVE = (ast.Mod, ast.Sub, ast.Div, ast.FloorDiv, ast.Pow)


def _collect_swappable_binops(tree):
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.BinOp) and isinstance(n.op, _NONCOMMUTATIVE)
    ]


def _swap_operands(node):
    node.left, node.right = node.right, node.left
    return True


# --- rule 4: swapped arguments in two-argument calls -----------------------

def _collect_two_arg_calls(tree):
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and len(n.args) == 2 and not n.keywords
    ]


def _swap_call_args(node):
    node.args[0], node.args[1] = node.args[1], node.args[0]
    return True


# --- rule 5: "forgot to recurse" -------------------------------------------
# `remainder = a % b; return remainder`  ->  `return gcd(b, remainder)`

def _recursion_completion(source):
    try:
        tree = ast.parse(source)
    except Exception:
        return
    fn = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == ENTRY),
        None,
    )
    if fn is None or len(fn.args.args) != 2:
        return
    params = [a.arg for a in fn.args.args]

    def collect(t):
        f = next(
            (n for n in ast.walk(t)
             if isinstance(n, ast.FunctionDef) and n.name == ENTRY),
            None,
        )
        if f is None:
            return []
        rets = []
        for n in ast.walk(f):
            if isinstance(n, ast.Return) and n.value is not None:
                v = n.value
                if isinstance(v, ast.Call):
                    continue  # already recursing (or calling something)
                if isinstance(v, ast.Name) and v.id in params:
                    continue  # base case `return a` -- leave it alone
                if isinstance(v, (ast.Name, ast.BinOp)):
                    rets.append(n)
        return rets

    def mutate(node):
        node.value = ast.Call(
            func=ast.Name(id=ENTRY, ctx=ast.Load()),
            args=[ast.Name(id=params[1], ctx=ast.Load()), node.value],
            keywords=[],
        )
        return True

    yield from _variants(source, collect, [mutate])


# ---------------------------------------------------------------------------
# Generic edit search (best-effort: tolerate signature differences)
# ---------------------------------------------------------------------------

def _generic(source, edits, budget):
    if _candidates_generic is None:
        return iter(())
    for call in (
        lambda: _candidates_generic(source, max_edits=edits, budget=budget),
        lambda: _candidates_generic(source, edits, budget),
        lambda: _candidates_generic(source),
    ):
        try:
            return call()
        except TypeError:
            continue
        except Exception:
            return iter(())
    return iter(())


# ---------------------------------------------------------------------------
# Prioritized, deduplicated, rps-capped candidate stream
# ---------------------------------------------------------------------------

def _candidate_stream(source):
    seen = set()

    def gens():
        yield iter((source,))
        yield _variants(source, _collect_const_compares, _const_compare_mutators())
        yield _variants(source, _collect_compares, _compare_op_mutators())
        yield _variants(source, _collect_swappable_binops, [_swap_operands])
        yield _variants(source, _collect_two_arg_calls, [_swap_call_args])
        yield _recursion_completion(source)
        yield _generic(source, 1, 1500)
        yield _generic(source, 2, 3000)

    for gen in gens():
        try:
            for cand in gen:
                if not isinstance(cand, str) or cand in seen:
                    continue
                seen.add(cand)
                if not _rps_ok(source, cand):
                    continue
                yield cand
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Validation, primary path: first_passing with a signature ladder.
# Each attempt gets a FRESH stream (generators are single-use).
# ---------------------------------------------------------------------------

def _coerce_result(result):
    if result is None:
        return None
    if isinstance(result, str):
        return result
    if isinstance(result, (tuple, list)):
        for item in result:
            if isinstance(item, str):
                try:
                    ast.parse(item)
                    return item
                except Exception:
                    continue
        return None
    for attr in ("source", "candidate", "patched", "code"):
        val = getattr(result, attr, None)
        if isinstance(val, str):
            return val
    return None


def _validate_with_first_passing(source):
    if _first_passing is None:
        raise RuntimeError("first_passing unavailable")
    attempts = (
        lambda: _first_passing(
            _candidate_stream(source), ENTRY, TESTS, source,
            max_rps=MAX_RPS, max_checks=3000,
        ),
        lambda: _first_passing(
            _candidate_stream(source), ENTRY, TESTS, source,
            max_rps=MAX_RPS,
        ),
        lambda: _first_passing(_candidate_stream(source), ENTRY, TESTS, source),
        lambda: _first_passing(_candidate_stream(source), ENTRY, TESTS),
    )
    last_exc = None
    for attempt in attempts:
        try:
            result = attempt()
        except Exception as exc:  # wrong signature or internal failure: retry
            last_exc = exc
            continue
        coerced = _coerce_result(result)
        if coerced is not None or result is None:
            return coerced
        # Call "succeeded" but returned something unusable: treat as broken.
        last_exc = RuntimeError("uninterpretable first_passing result")
        break
    raise last_exc if last_exc is not None else RuntimeError("no attempt ran")


# ---------------------------------------------------------------------------
# Validation, last-resort fallback (only if every first_passing attempt
# raised): run the visible tests ourselves, safely.
# ---------------------------------------------------------------------------

def _passes_subprocess(candidate):
    harness = (
        "\nimport sys\n"
        "_TESTS = " + repr(TESTS) + "\n"
        "_fn = globals().get(" + repr(ENTRY) + ")\n"
        "if not callable(_fn):\n"
        "    sys.exit(1)\n"
        "for _t in _TESTS:\n"
        "    try:\n"
        "        _out = _fn(*_t['args'])\n"
        "    except Exception:\n"
        "        sys.exit(1)\n"
        "    if _out != _t['expected']:\n"
        "        sys.exit(1)\n"
        "sys.stdout.write('ALL_OK')\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", candidate + "\n" + harness],
        capture_output=True, text=True, timeout=10,
    )
    return res.returncode == 0 and "ALL_OK" in (res.stdout or "")


class _StepLimit(Exception):
    pass


def _passes_inprocess(candidate, limit=5_000_000):
    try:
        code = compile(candidate, "<candidate>", "exec")
    except Exception:
        return False
    env = {}
    try:
        exec(code, env)  # noqa: S102 - local grading of student code
    except Exception:
        return False
    fn = env.get(ENTRY)
    if not callable(fn):
        return False
    for test in TESTS:
        counter = [0]

        def tracer(frame, event, arg):
            counter[0] += 1
            if counter[0] > limit:
                raise _StepLimit()
            return tracer

        old = sys.gettrace()
        sys.settrace(tracer)
        try:
            out = fn(*test["args"])
        except Exception:
            return False
        finally:
            sys.settrace(old)
        if out != test["expected"]:
            return False
    return True


def _validate_locally(source):
    use_subproc = True
    for i, cand in enumerate(_candidate_stream(source)):
        if i >= 400:
            break
        ok = False
        if use_subproc:
            try:
                ok = _passes_subprocess(cand)
            except subprocess.TimeoutExpired:
                ok = False  # candidate loops forever; keep using subprocess
            except Exception:
                use_subproc = False  # subprocess unavailable here
        if not use_subproc:
            try:
                ok = _passes_inprocess(cand)
            except Exception:
                ok = False
        if ok:
            return cand
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def repair(source):
    try:
        if not isinstance(source, str):
            return None
        try:
            ast.parse(source)
        except Exception:
            return None
        try:
            return _validate_with_first_passing(source)
        except Exception:
            pass
        return _validate_locally(source)
    except Exception:
        return None
```
