"""Local, LLM-free automatic repair for the `top_k` assignment.

Strategy:
  1. If the submission already passes, return it (validated via first_passing).
  2. Problem-specific AST rewrites targeting common misconceptions for this
     assignment (nsmallest vs nlargest, missing reverse=True in sorted(),
     wrong slice direction/sign, spurious or missing [::-1] reversal,
     missing emptiness guard on the selection loop, min/max confusion).
  3. Generic single-edit search (operator swaps, off-by-one, etc.).
  4. Compositions: specific+specific and specific+generic (for bugs needing
     two coordinated fixes, e.g. sorted(lst)[-k:]).
  5. Generic two-edit search as a last resort.
All candidates are validated with first_passing (test suite + rps <= 0.35).
"""

import ast
import copy
import itertools
import time

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "top_k"

TESTS = [
    {"args": [[5, 5, 1], 2], "expected": [5, 5]},
    {"args": [[3, 1, 2], 2], "expected": [3, 2]},
    {"args": [[1, 2, 3, 4, 5], 3], "expected": [5, 4, 3]},
    {"args": [[], 0], "expected": []},
    {"args": [[], 3], "expected": []},
    {"args": [[7], 1], "expected": [7]},
    {"args": [[4, 2], 0], "expected": []},
    {"args": [[1, 2], 5], "expected": [2, 1]},
    {"args": [[-1, -5, -3], 2], "expected": [-1, -3]},
    {"args": [[10, 10, 10], 2], "expected": [10, 10]},
    {"args": [[0, -1, 1], 3], "expected": [1, 0, -1]},
    {"args": [[2, 8, 6, 4, 9, 1], 4], "expected": [9, 8, 6, 4]},
    {"args": [[5, 3, 5, 3, 5], 3], "expected": [5, 5, 5]},
    {"args": [[100], 0], "expected": []},
]

# Direction-confused helper names commonly mixed up for this assignment.
_NAME_SWAPS = {
    "nsmallest": "nlargest",
    "nlargest": "nsmallest",
    "min": "max",
    "max": "min",
}


def _site_rewrites(node):
    """Return a list of in-place mutation callables applicable to `node`.

    Each callable receives the *corresponding node in a deep copy* of the
    tree and mutates it. Decisions are made from the original node's shape,
    but the callables only ever touch the node they are given.
    """
    fixes = []

    if isinstance(node, ast.Name) and node.id in _NAME_SWAPS:
        new = _NAME_SWAPS[node.id]
        fixes.append(lambda n, new=new: setattr(n, "id", new))

    if isinstance(node, ast.Attribute) and node.attr in _NAME_SWAPS:
        new = _NAME_SWAPS[node.attr]
        fixes.append(lambda n, new=new: setattr(n, "attr", new))

    if isinstance(node, ast.Call):
        fname = None
        if isinstance(node.func, ast.Name):
            fname = node.func.id
        elif isinstance(node.func, ast.Attribute):
            fname = node.func.attr
        if fname in ("sorted", "sort") and not any(
            kw.arg == "reverse" for kw in node.keywords
        ):
            def _add_reverse(n):
                n.keywords.append(
                    ast.keyword(arg="reverse", value=ast.Constant(True))
                )
            fixes.append(_add_reverse)

    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
        sl = node.slice
        if sl.lower is not None and sl.upper is None:
            # X[k:] or X[-k:]  ->  X[:k]
            def _swap_lower_to_upper(n):
                s = n.slice
                low = s.lower
                if isinstance(low, ast.UnaryOp) and isinstance(low.op, ast.USub):
                    low = low.operand
                s.upper = low
                s.lower = None
            fixes.append(_swap_lower_to_upper)
        if (
            sl.upper is not None
            and sl.lower is None
            and isinstance(sl.upper, ast.UnaryOp)
            and isinstance(sl.upper.op, ast.USub)
        ):
            # X[:-k] -> X[:k]
            def _unnegate_upper(n):
                n.slice.upper = n.slice.upper.operand
            fixes.append(_unnegate_upper)
        if sl.step is not None:
            # drop a spurious reversal / step
            def _drop_step(n):
                n.slice.step = None
            fixes.append(_drop_step)

    if isinstance(node, ast.Return) and node.value is not None:
        # result built in ascending order: return X -> return X[::-1]
        def _wrap_reverse(n):
            n.value = ast.Subscript(
                value=n.value,
                slice=ast.Slice(
                    lower=None,
                    upper=None,
                    step=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1)),
                ),
                ctx=ast.Load(),
            )
        fixes.append(_wrap_reverse)

    if isinstance(node, ast.While):
        # Missing emptiness guard: while COND: ... temp.remove/pop(...)
        removed_vars = set()
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr in ("remove", "pop")
                and isinstance(sub.func.value, ast.Name)
            ):
                removed_vars.add(sub.func.value.id)
        in_test = {
            n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)
        }
        for v in sorted(removed_vars - in_test):
            def _guard(n, v=v):
                n.test = ast.BoolOp(
                    op=ast.And(),
                    values=[ast.Name(id=v, ctx=ast.Load()), n.test],
                )
            fixes.append(_guard)

    return fixes


def _specific(source):
    """Yield candidate programs from problem-specific single rewrites."""
    try:
        tree = ast.parse(source)
    except Exception:
        return
    nodes = list(ast.walk(tree))
    for i, node in enumerate(nodes):
        for fix in _site_rewrites(node):
            try:
                tree2 = copy.deepcopy(tree)
                node2 = list(ast.walk(tree2))[i]
                fix(node2)
                yield ast.unparse(ast.fix_missing_locations(tree2))
            except Exception:
                continue


def _compose(source):
    """Two-edit compositions: specific+specific, then specific+generic."""
    try:
        bases = list(itertools.islice(_specific(source), 60))
    except Exception:
        return
    for b in bases:
        try:
            yield from itertools.islice(_specific(b), 40)
        except Exception:
            continue
    for b in bases:
        try:
            yield from itertools.islice(candidates_generic(b, max_edits=1), 150)
        except Exception:
            continue


def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None


def _repair(source):
    if not isinstance(source, str):
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    deadline = time.monotonic() + 8.0
    seen = set()

    def fresh(gen):
        for cand in gen:
            if time.monotonic() > deadline:
                return
            if not isinstance(cand, str) or cand in seen:
                continue
            seen.add(cand)
            yield cand

    def stages():
        # 0: the submission itself (maybe already correct)
        yield iter([source])
        # 1: problem-specific single rewrites
        yield _specific(source)
        # 2: generic single edits
        yield candidates_generic(source, max_edits=1)
        # 3: two-edit compositions seeded by specific rewrites
        yield _compose(source)
        # 4: generic pairs (bounded)
        yield candidates_generic(source, max_edits=2, budget=2000)

    for gen in stages():
        if time.monotonic() > deadline:
            break
        try:
            result = first_passing(
                fresh(gen), ENTRY, TESTS, source,
                max_rps=0.35, max_checks=800,
            )
        except Exception:
            result = None
        if result is not None:
            return result
    return None
