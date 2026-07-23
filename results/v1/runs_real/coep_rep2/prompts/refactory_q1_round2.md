You previously wrote the following per-assignment repair module for the assignment "refactory_q1":

```python
"""Automatic repair for the "Sequential Search" assignment (local, LLM-free).

`search(x, seq)` must return the leftmost insertion point of `x` in the
sorted sequence `seq`: the first index i with x <= seq[i], len(seq) when x
is greater than every element, and 0 for an empty sequence.

Approach: problem-specific AST rewrite rules targeting the misconceptions
students commonly have for THIS assignment --
  * falling off the end of the function (missing final `return len(seq)`),
  * a wrong trailing return such as `return i + 1` / `return len(seq) - 1`,
  * missing empty-sequence handling (IndexError / NameError on []),
  * wrong last-element boundary (`elif x >= seq[-1]: return len(seq) - 1`),
  * off-by-one on returned loop indices (`return j` vs `return j + 1`),
  * loops that `break` and then mishandle the not-found case (add for-else),
-- chained with the generic mutation search (single edits, rule+edit
combinations, then two-edit search), and always validated through
`first_passing`, which enforces the full visible test suite and the
rps <= 0.35 patch-size cap measured against the ORIGINAL submission.
"""

import ast
import time

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401  (patch-size metric; enforced via first_passing)

ENTRY = "search"

TESTS = [
    {"args": [42, [-5, 1, 3, 5, 7, 10]], "expected": 6},
    {"args": [42, [1, 5, 10]], "expected": 3},
    {"args": [5, [1, 5, 10]], "expected": 1},
    {"args": [7, [1, 5, 10]], "expected": 2},
    {"args": [3, [1, 5, 10]], "expected": 1},
    {"args": [-5, [1, 5, 10]], "expected": 0},
    {"args": [10, [-5, -1, 3, 5, 7, 10]], "expected": 5},
    {"args": [-100, [-5, -1, 3, 5, 7, 10]], "expected": 0},
    {"args": [0, [-5, -1, 3, 5, 7, 10]], "expected": 2},
    {"args": [100, []], "expected": 0},
    {"args": [-100, []], "expected": 0},
]

MAX_RPS = 0.35
_TIME_BUDGET = 8.5  # seconds; stay safely under the ~10 s limit


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _find_func(tree, name=ENTRY):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _len_call(sname):
    return ast.Call(
        func=ast.Name(id="len", ctx=ast.Load()),
        args=[ast.Name(id=sname, ctx=ast.Load())],
        keywords=[],
    )


def _is_len_call(node, sname):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == sname
    )


def _slice_expr(sub):
    s = sub.slice
    if s.__class__.__name__ == "Index":  # pre-3.9 compatibility
        s = getattr(s, "value", s)
    return s


def _is_last_index(e, sname):
    # -1  (parsed as USub(1)), a folded Constant(-1), or len(seq) - 1
    if (isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub)
            and isinstance(e.operand, ast.Constant)
            and e.operand.value == 1):
        return True
    if isinstance(e, ast.Constant) and e.value == -1:
        return True
    if (isinstance(e, ast.BinOp) and isinstance(e.op, ast.Sub)
            and _is_len_call(e.left, sname)
            and isinstance(e.right, ast.Constant) and e.right.value == 1):
        return True
    return False


def _is_last_elem(node, sname):
    # seq[-1] or seq[len(seq) - 1]
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == sname
        and _is_last_index(_slice_expr(node), sname)
    )


def _guard(sname):
    # if not seq: return 0
    return ast.If(
        test=ast.UnaryOp(op=ast.Not(),
                         operand=ast.Name(id=sname, ctx=ast.Load())),
        body=[ast.Return(value=ast.Constant(value=0))],
        orelse=[],
    )


def _boundary_ifs(fn, xname, sname):
    """If/elif nodes testing `x >= seq[-1]` (or `seq[-1] <= x`)."""
    out = []
    for node in ast.walk(fn):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)):
            continue
        t = node.test
        if len(t.ops) != 1 or len(t.comparators) != 1:
            continue
        op, left, right = t.ops[0], t.left, t.comparators[0]
        a = (isinstance(op, ast.GtE) and isinstance(left, ast.Name)
             and left.id == xname and _is_last_elem(right, sname))
        b = (isinstance(op, ast.LtE) and _is_last_elem(left, sname)
             and isinstance(right, ast.Name) and right.id == xname)
        if a or b:
            out.append(node)
    return out


def _lenm1_returns(fn, sname):
    """Return nodes of the form `return len(seq) - 1`."""
    out = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Return)
                and isinstance(node.value, ast.BinOp)
                and isinstance(node.value.op, ast.Sub)
                and _is_len_call(node.value.left, sname)
                and isinstance(node.value.right, ast.Constant)
                and node.value.right.value == 1):
            out.append(node)
    return out


def _name_returns(fn):
    """Return nodes of the form `return <name>`."""
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name)]


def _nameplus1_returns(fn):
    """Return nodes of the form `return <name> + 1`."""
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.BinOp):
            v = n.value
            if (isinstance(v.op, ast.Add) and isinstance(v.left, ast.Name)
                    and isinstance(v.right, ast.Constant)
                    and v.right.value == 1):
                out.append(n)
    return out


def _break_loops(fn):
    """For/While loops containing a break and having no else clause."""
    out = []
    for node in ast.walk(fn):
        if isinstance(node, (ast.For, ast.While)) and not node.orelse:
            if any(isinstance(n, ast.Break) for n in ast.walk(node)):
                out.append(node)
    return out


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules
# ---------------------------------------------------------------------------

def _rule_candidates(source):
    """Targeted candidate patches for this assignment, most specific first."""
    out, seen = [], set()

    def emit(tree):
        try:
            ast.fix_missing_locations(tree)
            s = ast.unparse(tree)
        except Exception:
            return
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    try:
        probe = ast.parse(source)
    except Exception:
        return out
    fn0 = _find_func(probe)
    if fn0 is None or len(fn0.args.args) < 2:
        return out
    xname = fn0.args.args[0].arg
    sname = fn0.args.args[1].arg

    def fresh():
        t = ast.parse(source)
        return t, _find_func(t)

    # R4: wrong last-element boundary, e.g.
    #     elif x >= seq[-1]: return len(seq) - 1
    # -> elif x >  seq[-1]: return len(seq)
    n_b = len(_boundary_ifs(fn0, xname, sname))
    for k in range(n_b):
        for mode in ("both", "op", "ret"):
            try:
                t, f = fresh()
                node = _boundary_ifs(f, xname, sname)[k]
                if mode in ("both", "op"):
                    old = node.test.ops[0]
                    node.test.ops[0] = ast.Gt() if isinstance(old, ast.GtE) else ast.Lt()
                if mode in ("both", "ret"):
                    for stmt in node.body:
                        for r in ast.walk(stmt):
                            if isinstance(r, ast.Return):
                                r.value = _len_call(sname)
                emit(t)
            except Exception:
                pass

    # R5: `return len(seq) - 1`  ->  `return len(seq)`  (anywhere)
    n_l = len(_lenm1_returns(fn0, sname))
    for k in range(n_l):
        try:
            t, f = fresh()
            _lenm1_returns(f, sname)[k].value = _len_call(sname)
            emit(t)
        except Exception:
            pass

    # R2: wrong trailing return (e.g. `return i + 1`, `return i`,
    #     bare `return`)  ->  `return len(seq)`
    try:
        t, f = fresh()
        last = f.body[-1]
        if isinstance(last, ast.Return) and (
                last.value is None or not _is_len_call(last.value, sname)):
            last.value = _len_call(sname)
            emit(t)
    except Exception:
        pass

    # R1: function can fall off the end -> append `return len(seq)`
    try:
        t, f = fresh()
        if not isinstance(f.body[-1], ast.Return):
            f.body.append(ast.Return(value=_len_call(sname)))
            emit(t)
    except Exception:
        pass

    # R10: off-by-one on returned loop indices: `return j` <-> `return j + 1`
    n_r = len(_name_returns(fn0))
    for k in range(n_r):
        try:
            t, f = fresh()
            r = _name_returns(f)[k]
            r.value = ast.BinOp(left=r.value, op=ast.Add(),
                                right=ast.Constant(value=1))
            emit(t)
        except Exception:
            pass
    n_p = len(_nameplus1_returns(fn0))
    for k in range(n_p):
        try:
            t, f = fresh()
            r = _nameplus1_returns(f)[k]
            r.value = r.value.left
            emit(t)
        except Exception:
            pass

    # R9: loop with break but no else -> add `else: return len(seq)`
    n_bl = len(_break_loops(fn0))
    for k in range(n_bl):
        try:
            t, f = fresh()
            _break_loops(f)[k].orelse = [ast.Return(value=_len_call(sname))]
            emit(t)
        except Exception:
            pass

    # R3: missing empty-sequence handling -> insert `if not seq: return 0`
    try:
        t, f = fresh()
        f.body.insert(0, _guard(sname))
        emit(t)
    except Exception:
        pass

    # R3 + R1/R2 combo: guard AND fix/append the trailing return
    try:
        t, f = fresh()
        f.body.insert(0, _guard(sname))
        last = f.body[-1]
        if isinstance(last, ast.Return):
            if last.value is None or not _is_len_call(last.value, sname):
                last.value = _len_call(sname)
        else:
            f.body.append(ast.Return(value=_len_call(sname)))
        emit(t)
    except Exception:
        pass

    return out


def _with_guard(src):
    """Insert `if not seq: return 0` at the top of `search` in src."""
    try:
        t = ast.parse(src)
        f = _find_func(t)
        if f is None or len(f.args.args) < 2:
            return None
        f.body.insert(0, _guard(f.args.args[1].arg))
        ast.fix_missing_locations(t)
        return ast.unparse(t)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Search driver
# ---------------------------------------------------------------------------

def _safe_iter(gen):
    """Yield from gen, swallowing any exception it may raise."""
    try:
        it = iter(gen)
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


def _stage(cands, source, max_checks):
    try:
        return first_passing(_safe_iter(cands), ENTRY, TESTS, source,
                             max_rps=MAX_RPS, max_checks=max_checks)
    except Exception:
        return None


def _repair(source):
    t0 = time.time()
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None  # syntax errors are out of scope

    # Already correct? Validate the untouched submission (rps == 0).
    ok = _stage(iter([source]), source, max_checks=4)
    if ok is not None:
        return ok

    # Dispatch on observed behaviour: if the module cannot even be executed,
    # only a small generic search is plausibly useful.
    try:
        res = failing_tests(source, ENTRY, TESTS)
        if not getattr(res, "compiled", True):
            return _stage(candidates_generic(source, max_edits=1, budget=800),
                          source, max_checks=300)
    except Exception:
        pass

    rules = _rule_candidates(source)

    # Stage A: targeted rules first, then every single generic edit.
    cand = _stage(chain(iter(rules),
                        candidates_generic(source, max_edits=1, budget=2000)),
                  source, max_checks=800)
    if cand is not None:
        return cand

    # Stage B: rule outputs combined with an empty-seq guard and with one
    # extra generic edit on top (covers two-fault submissions).
    if time.time() - t0 < _TIME_BUDGET - 3.0:
        gens = []
        extra = []
        for r in rules[:12]:
            g = _with_guard(r)
            if g and g not in rules:
                extra.append(g)
        if extra:
            gens.append(iter(extra))
        for r in rules[:12]:
            gens.append(candidates_generic(r, max_edits=1, budget=300))
        if gens:
            cand = _stage(chain(*gens), source, max_checks=700)
            if cand is not None:
                return cand

    # Stage C: broad generic two-edit search.
    if time.time() - t0 < _TIME_BUDGET - 2.0:
        cand = _stage(candidates_generic(source, max_edits=2, budget=4000),
                      source, max_checks=800)
        if cand is not None:
            return cand

    return None


def repair(source: str):
    """Repair a buggy `search` submission; return fixed source or None."""
    try:
        return _repair(source)
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- real_008.py: REPAIRED
- real_099.py: NOT REPAIRED — no_patch
- real_219.py: NOT REPAIRED — no_patch
- real_362.py: REPAIRED
- real_384.py: NOT REPAIRED — no_patch

For reference, the submissions the module failed on:

### Failed submission real_099.py
```python
def search(x, seq):
    for i in range (len(seq)):
        if x < seq[i]:
            return i
        elif x ==seq[i]:
            return i
        else:
            continue
    return i + 1

```

### Failed submission real_219.py
```python
def search(x, seq):
    for i, elem in enumerate(seq):
        if x <= elem:
            return i
        elif i == len(seq) - 1 and x > elem:
            return i + 1

```

### Failed submission real_384.py
```python
def search(x, seq):
    for i in range(len(seq)):
        if seq[i] < x:
            continue
        elif seq[len(seq)-1] < x:
            return len(seq)-1
        else:
            return i
    """ Takes in a value x and a sorted sequence seq, and returns the
    position that x should go to such that the sequence remains sorted """

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
