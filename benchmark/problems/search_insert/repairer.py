"""Local, LLM-free automatic repair for the `search_insert` assignment.

Strategy:
  1. If the submission already passes, return it (validated via first_passing).
  2. Try problem-specific rewrites targeting common misconceptions for this
     assignment (bisect_right-style comparison flips, wrong final return such
     as `return -1`/missing return, classic "return mid on equality" binary
     search, `(lo+hi)//1` mid computation, `lst[mid+1]` index shifts,
     `len(lst)-1` upper-bound initialisation), dispatching on the observed
     failure pattern (IndexErrors prioritise index/bound fixes).
  3. Fall back to the generic single-edit search, then the pairwise search.
All candidates are validated with `first_passing`, which enforces the full
visible test suite and the rps <= 0.35 patch-size cap.
"""

import ast

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain  # noqa: F401
from coep.evaluate import rps  # noqa: F401

ENTRY = "search_insert"

TESTS = [
    {"args": [[1, 3, 5, 7], 5], "expected": 2},
    {"args": [[1, 3, 5, 7], 4], "expected": 2},
    {"args": [[1, 3, 5, 7], 0], "expected": 0},
    {"args": [[1, 3, 5, 7], 8], "expected": 4},
    {"args": [[], 4], "expected": 0},
    {"args": [[2, 2, 2, 2], 2], "expected": 0},
    {"args": [[1, 2, 2, 3], 2], "expected": 1},
    {"args": [[10], 10], "expected": 0},
    {"args": [[10], 5], "expected": 0},
    {"args": [[10], 15], "expected": 1},
    {"args": [[1, 1, 2, 3, 3, 3, 4], 3], "expected": 3},
    {"args": [[-5, -2, 0, 3], -2], "expected": 1},
    {"args": [[1, 3, 5, 7], 1], "expected": 0},
    {"args": [[1, 3, 5, 7], 7], "expected": 3},
]

_CMP_OPS = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)


# ---------------------------------------------------------------- utilities

def _parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _unparse(tree):
    try:
        return ast.unparse(ast.fix_missing_locations(tree))
    except Exception:
        return None


def _safe_iter(factory):
    """Iterate factory()'s results, swallowing any exception."""
    try:
        it = iter(factory())
    except Exception:
        return
    while True:
        try:
            item = next(it)
        except StopIteration:
            return
        except Exception:
            return
        if isinstance(item, str):
            yield item


def _f_get(failure, key):
    if isinstance(failure, dict):
        return failure.get(key)
    return getattr(failure, key, None)


# ------------------------------------------- comparison-operator rewrites
# The dominant misconception: computing the *rightmost* insertion point
# (`<=` instead of `<`, `>` instead of `>=`, or `==` in a linear search).

def _cmp_sites(tree):
    sites = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], _CMP_OPS)):
            sites.append(node)
    return sites


def _compare_variants(source):
    tree = _parse(source)
    if tree is None:
        return
    sites = _cmp_sites(tree)
    for i in range(len(sites)):
        current = type(sites[i].ops[0])
        for repl in _CMP_OPS:
            if repl is current:
                continue
            t2 = _parse(source)
            if t2 is None:
                return
            s2 = _cmp_sites(t2)
            if i >= len(s2):
                continue
            s2[i].ops[0] = repl()
            out = _unparse(t2)
            if out:
                yield out


# ------------------------------------------------------- AST normalisations
# div1: `(lo+hi)//1` -> `(lo+hi)//2` (broken mid computation)
# idx : `lst[mid+1]` / `lst[mid-1]` -> `lst[mid]` (shifted probe index)
# len1: `len(lst)-1` -> `len(lst)` (wrong upper bound for the lo<hi loop)

class _Norm(ast.NodeTransformer):
    def __init__(self, kinds):
        self.kinds = kinds
        self.changed = False

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if ("div1" in self.kinds and isinstance(node.op, ast.FloorDiv)
                and isinstance(node.right, ast.Constant)
                and node.right.value == 1):
            node.right = ast.Constant(2)
            self.changed = True
        if ("len1" in self.kinds and isinstance(node.op, ast.Sub)
                and isinstance(node.right, ast.Constant)
                and node.right.value == 1
                and isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Name)
                and node.left.func.id == "len"):
            self.changed = True
            return node.left
        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if "idx" in self.kinds:
            sl = node.slice
            if (isinstance(sl, ast.BinOp)
                    and isinstance(sl.op, (ast.Add, ast.Sub))
                    and isinstance(sl.right, ast.Constant)
                    and sl.right.value == 1
                    and isinstance(sl.left, ast.Name)):
                node.slice = sl.left
                self.changed = True
        return node


def _normalize(source, kinds):
    tree = _parse(source)
    if tree is None:
        return None
    tr = _Norm(kinds)
    tree = tr.visit(tree)
    if not tr.changed:
        return None
    return _unparse(tree)


# ----------------------------------------------- final-return misconception
# Linear searches that return -1 / None / a constant (or fall off the end)
# when x is larger than everything, instead of returning len(lst).

def _find_entry(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == ENTRY:
            return n
    return None


def _final_return_variants(source):
    tree = _parse(source)
    if tree is None:
        return
    func = _find_entry(tree)
    if func is None or not getattr(func.args, "args", None) or not func.body:
        return
    pname = func.args.args[0].arg
    ret_len = ast.Return(value=ast.Call(
        func=ast.Name(id="len", ctx=ast.Load()),
        args=[ast.Name(id=pname, ctx=ast.Load())],
        keywords=[]))
    last = func.body[-1]
    if isinstance(last, ast.Return) and (
            last.value is None or isinstance(last.value, ast.Constant)):
        func.body[-1] = ret_len
        out = _unparse(tree)
        if out:
            yield out
    elif isinstance(last, (ast.For, ast.While)):
        func.body.append(ret_len)
        out = _unparse(tree)
        if out:
            yield out


# ------------------------------------------ "return mid on equality" fix
# Classic binary *search* (returns any matching index) instead of leftmost
# insertion point.  Replace `return mid` inside the while loop with an
# upper-bound update (`hi = mid - 1` or `hi = mid`) so the scan keeps
# moving left; the trailing `return lo` then yields the leftmost position.

def _stmt_sites(tree):
    sites = []

    def visit(node):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list):
                for i, st in enumerate(block):
                    sites.append((block, i, st))
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return sites


def _return_mid_variants(source):
    base = _parse(source)
    if base is None:
        return
    if not any(isinstance(n, ast.While) for n in ast.walk(base)):
        return
    sites = _stmt_sites(base)
    assigned = set()
    for _, _, st in sites:
        if isinstance(st, ast.Assign):
            for t in st.targets:
                if isinstance(t, ast.Name):
                    assigned.add(t.id)
                elif isinstance(t, ast.Tuple):
                    for e in t.elts:
                        if isinstance(e, ast.Name):
                            assigned.add(e.id)
        elif isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name):
            assigned.add(st.target.id)
    targets = [(k, st.value.id) for k, (_, _, st) in enumerate(sites)
               if isinstance(st, ast.Return) and isinstance(st.value, ast.Name)]
    emitted = 0
    for k, mname in targets:
        for var in sorted(assigned - {mname}):
            for minus_one in (True, False):
                if emitted >= 40:
                    return
                t2 = _parse(source)
                if t2 is None:
                    return
                s2 = _stmt_sites(t2)
                if k >= len(s2):
                    continue
                block, i, _ = s2[k]
                if minus_one:
                    value = ast.BinOp(left=ast.Name(id=mname, ctx=ast.Load()),
                                      op=ast.Sub(), right=ast.Constant(1))
                else:
                    value = ast.Name(id=mname, ctx=ast.Load())
                block[i] = ast.Assign(
                    targets=[ast.Name(id=var, ctx=ast.Store())], value=value)
                out = _unparse(t2)
                if out:
                    emitted += 1
                    yield out


# ------------------------------------------------------ targeted dispatcher

def _targeted(source, res):
    index_error = False
    try:
        failures = getattr(res, "failures", None) if res is not None else None
        for f in failures or []:
            err = _f_get(f, "error")
            if err and "IndexError" in str(err):
                index_error = True
                break
    except Exception:
        pass

    def cmp_family():
        yield from _compare_variants(source)

    def ret_family():
        yield from _final_return_variants(source)
        yield from _return_mid_variants(source)

    def norm_family():
        variants = []
        for kinds in (("div1",), ("idx",), ("len1",), ("div1", "idx", "len1")):
            v = _normalize(source, kinds)
            if v and v != source and v not in variants:
                variants.append(v)
        # First the bare normalisations (often the whole fix)...
        for v in variants:
            yield v
        # ...then each normalisation combined with one more small edit,
        # covering two-fault submissions like //1 together with mid-1.
        for v in variants:
            yield from _compare_variants(v)
            yield from _safe_iter(
                lambda v=v: candidates_generic(v, max_edits=1, budget=800))

    if index_error:
        order = (norm_family, cmp_family, ret_family)
    else:
        order = (cmp_family, ret_family, norm_family)
    for family in order:
        yield from _safe_iter(family)


# ---------------------------------------------------------------- top level

def _all_candidates(source, res):
    yield from _safe_iter(lambda: _targeted(source, res))
    yield from _safe_iter(
        lambda: candidates_generic(source, max_edits=1, budget=2000))
    yield from _safe_iter(
        lambda: candidates_generic(source, max_edits=2, budget=5000))


def repair(source):
    try:
        if not isinstance(source, str):
            return None
        if _parse(source) is None:
            return None

        res = None
        try:
            res = failing_tests(source, ENTRY, TESTS)
            if (getattr(res, "compiled", False)
                    and getattr(res, "passed", -1) == getattr(res, "total", -2)):
                ok = first_passing(iter([source]), ENTRY, TESTS, source,
                                   max_rps=0.35)
                if ok is not None:
                    return ok
        except Exception:
            res = None

        seen = {source}

        def stream():
            for cand in _all_candidates(source, res):
                if cand not in seen:
                    seen.add(cand)
                    yield cand

        return first_passing(stream(), ENTRY, TESTS, source,
                             max_rps=0.35, max_checks=800)
    except Exception:
        return None
