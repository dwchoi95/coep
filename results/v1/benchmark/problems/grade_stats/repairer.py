"""Local, LLM-free automatic repair for the `grade_stats` assignment.

Strategy:
  1. If the submission already passes, return it (validated via first_passing).
  2. Apply problem-specific AST rewrite rules targeting the misconceptions
     common for this assignment (missing/wrong rounding, median instead of
     mean, floor division, int() truncation, swapped min/max, bad numeric
     initializations, tuple returns, forgotten division), plus second-level
     combinations of those rules.
  3. Fall back to the generic mutation search (single edits on the source and
     on the most promising rewritten variants, then paired edits).
All candidates are validated exclusively through `first_passing`, which
enforces the full visible test suite and the rps <= 0.35 patch-size cap.
`repair` never raises and returns None on unfixable/invalid input.
"""

from __future__ import annotations

import ast
import re

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401  (patch-size metric; enforced by first_passing)

ENTRY = "grade_stats"

TESTS = [
    {"args": [[70, 80, 90]], "expected": [70, 90, 80.0]},
    {"args": [[100]], "expected": [100, 100, 100.0]},
    {"args": [[50.5, 60.5]], "expected": [50.5, 60.5, 55.5]},
    {"args": [[-10, 0, 10]], "expected": [-10, 10, 0.0]},
    {"args": [[1, 2]], "expected": [1, 2, 1.5]},
    {"args": [[1, 2, 3]], "expected": [1, 3, 2.0]},
    {"args": [[0, 0, 0]], "expected": [0, 0, 0.0]},
    {"args": [[59.9, 60.1, 60.0]], "expected": [59.9, 60.1, 60.0]},
    {"args": [[85, 92, 78, 95, 88]], "expected": [78, 95, 87.6]},
    {"args": [[1, 2, 4]], "expected": [1, 4, 2.33]},
    {"args": [[-5, -15, -10]], "expected": [-15, -5, -10.0]},
    {"args": [[2.675, 2.675]], "expected": [2.675, 2.675, 2.67]},
    {"args": [[0.1, 0.2, 0.3]], "expected": [0.1, 0.3, 0.2]},
    {"args": [[10, 20, 30, 40]], "expected": [10, 40, 25.0]},
]


# --------------------------------------------------------------------------
# small AST helpers
# --------------------------------------------------------------------------

def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


def _unparse(tree):
    try:
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
    except Exception:
        return None


def _call(fname, argname):
    return ast.Call(
        func=ast.Name(id=fname, ctx=ast.Load()),
        args=[ast.Name(id=argname, ctx=ast.Load())],
        keywords=[],
    )


def _round2(node):
    return ast.Call(
        func=ast.Name(id="round", ctx=ast.Load()),
        args=[node, ast.Constant(value=2)],
        keywords=[],
    )


def _is_round2(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "round"
        and len(node.args) == 2
        and not node.keywords
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == 2
    )


def _param_name(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == ENTRY and n.args.args:
            return n.args.args[0].arg
    return "scores"


def _mean_expr(name):
    return ast.BinOp(left=_call("sum", name), op=ast.Div(), right=_call("len", name))


# --------------------------------------------------------------------------
# problem-specific rewrite rules; each returns a list of variant sources
# --------------------------------------------------------------------------

def t_fix_round(src):
    """Normalize every round(...) call to round(<value>, 2).

    Fixes round(x) with no ndigits, round(x, 1)/round(x, 3), and swapped
    arguments like round(2, x): the value kept is the first argument that is
    not a bare numeric constant.
    """
    tree = _parse(src)
    if tree is None:
        return []
    changed = [False]

    class R(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "round"
                and node.args
                and not node.keywords
                and not _is_round2(node)
            ):
                val = None
                for a in node.args:
                    if not (
                        isinstance(a, ast.Constant)
                        and isinstance(a.value, (int, float))
                        and not isinstance(a.value, bool)
                    ):
                        val = a
                        break
                if val is None:
                    val = node.args[0]
                changed[0] = True
                return _round2(val)
            return node

    tree = R().visit(tree)
    if not changed[0]:
        return []
    out = _unparse(tree)
    return [out] if out else []


def t_wrap_third(src):
    """Wrap the third element of a 3-element return in round(..., 2)."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = [False]

    class R(ast.NodeTransformer):
        def visit_Return(self, node):
            self.generic_visit(node)
            v = node.value
            if isinstance(v, (ast.List, ast.Tuple)) and len(v.elts) == 3:
                if not _is_round2(v.elts[2]):
                    v.elts[2] = _round2(v.elts[2])
                    changed[0] = True
            return node

    tree = R().visit(tree)
    if not changed[0]:
        return []
    out = _unparse(tree)
    return [out] if out else []


def t_tuple_to_list(src):
    """Turn `return a, b, c` / tuple returns into list returns."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = [False]

    class R(ast.NodeTransformer):
        def visit_Return(self, node):
            self.generic_visit(node)
            if isinstance(node.value, ast.Tuple) and len(node.value.elts) == 3:
                node.value = ast.List(elts=node.value.elts, ctx=ast.Load())
                changed[0] = True
            return node

    tree = R().visit(tree)
    if not changed[0]:
        return []
    out = _unparse(tree)
    return [out] if out else []


def t_floordiv(src):
    """Replace every floor division with true division."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = [False]

    class R(ast.NodeTransformer):
        def visit_BinOp(self, node):
            self.generic_visit(node)
            if isinstance(node.op, ast.FloorDiv):
                node.op = ast.Div()
                changed[0] = True
            return node

    tree = R().visit(tree)
    if not changed[0]:
        return []
    out = _unparse(tree)
    return [out] if out else []


def t_int_call(src):
    """Fix int() truncation: int(x) -> round(x, 2), and int(x) -> x."""
    outs = []
    for mode in ("round", "strip"):
        tree = _parse(src)
        if tree is None:
            return []
        changed = [False]

        class R(ast.NodeTransformer):
            def visit_Call(self, node):
                self.generic_visit(node)
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "int"
                    and len(node.args) == 1
                    and not node.keywords
                ):
                    changed[0] = True
                    if mode == "round":
                        return _round2(node.args[0])
                    return node.args[0]
                return node

        tree = R().visit(tree)
        if changed[0]:
            out = _unparse(tree)
            if out:
                outs.append(out)
    return outs


def t_subscript_to_mean(src):
    """Replace one indexing expression (e.g. the median pick ordered[n//2])
    with sum(seq)/len(seq).  One variant per Load-context subscript; wrong
    replacements are filtered out by the test suite."""
    tree = _parse(src)
    if tree is None:
        return []
    total = sum(
        1
        for n in ast.walk(tree)
        if isinstance(n, ast.Subscript)
        and isinstance(n.value, ast.Name)
        and isinstance(n.ctx, ast.Load)
    )
    outs = []
    for k in range(min(total, 8)):
        t2 = _parse(src)
        if t2 is None:
            return outs
        state = {"i": 0, "done": False}

        class R(ast.NodeTransformer):
            def visit_Subscript(self, node):
                self.generic_visit(node)
                if isinstance(node.value, ast.Name) and isinstance(node.ctx, ast.Load):
                    idx = state["i"]
                    state["i"] += 1
                    if idx == k and not state["done"]:
                        state["done"] = True
                        return _mean_expr(node.value.id)
                return node

        t3 = R().visit(t2)
        if state["done"]:
            out = _unparse(t3)
            if out:
                outs.append(out)
    return outs


def t_divide_third(src):
    """Fix a forgotten division: third return element becomes elt/len(param)
    (inside round(..., 2))."""
    tree = _parse(src)
    if tree is None:
        return []
    param = _param_name(tree)
    changed = [False]

    class R(ast.NodeTransformer):
        def visit_Return(self, node):
            self.generic_visit(node)
            v = node.value
            if isinstance(v, (ast.List, ast.Tuple)) and len(v.elts) == 3:
                third = v.elts[2]
                if _is_round2(third):
                    third.args[0] = ast.BinOp(
                        left=third.args[0], op=ast.Div(), right=_call("len", param)
                    )
                else:
                    v.elts[2] = _round2(
                        ast.BinOp(left=third, op=ast.Div(), right=_call("len", param))
                    )
                changed[0] = True
            return node

    tree = R().visit(tree)
    if not changed[0]:
        return []
    out = _unparse(tree)
    return [out] if out else []


def t_init_fix(src):
    """Fix bad min/max initializations like lo = 0 or hi = 100 by replacing
    the numeric constant with <param>[0].  Variants: each constant-assign
    individually, plus all assigns whose target is used in a comparison."""
    tree = _parse(src)
    if tree is None:
        return []
    param = _param_name(tree)

    cmp_names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            for sub in [n.left] + list(n.comparators):
                if isinstance(sub, ast.Name):
                    cmp_names.add(sub.id)

    def is_const_assign(n):
        return (
            isinstance(n, ast.Assign)
            and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, (int, float))
            and not isinstance(n.value.value, bool)
        )

    total = sum(1 for n in ast.walk(tree) if is_const_assign(n))
    if not total:
        return []

    plans = [("idx", k) for k in range(min(total, 6))]
    if cmp_names:
        plans.append(("cmp", None))

    outs = []
    for mode, k in plans:
        t2 = _parse(src)
        if t2 is None:
            return outs
        state = {"i": 0, "hit": False}

        class R(ast.NodeTransformer):
            def visit_Assign(self, node):
                self.generic_visit(node)
                if is_const_assign(node):
                    idx = state["i"]
                    state["i"] += 1
                    replace = (
                        (mode == "idx" and idx == k)
                        or (mode == "cmp" and node.targets[0].id in cmp_names)
                    )
                    if replace:
                        node.value = ast.Subscript(
                            value=ast.Name(id=param, ctx=ast.Load()),
                            slice=ast.Constant(value=0),
                            ctx=ast.Load(),
                        )
                        state["hit"] = True
                return node

        t3 = R().visit(t2)
        if state["hit"]:
            out = _unparse(t3)
            if out:
                outs.append(out)
    return outs


def t_swap_minmax(src):
    """Swap the first two elements of a 3-element return (min/max mixed up)."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = [False]

    class R(ast.NodeTransformer):
        def visit_Return(self, node):
            self.generic_visit(node)
            v = node.value
            if isinstance(v, (ast.List, ast.Tuple)) and len(v.elts) == 3:
                v.elts[0], v.elts[1] = v.elts[1], v.elts[0]
                changed[0] = True
            return node

    tree = R().visit(tree)
    if not changed[0]:
        return []
    out = _unparse(tree)
    return [out] if out else []


def t_median_name(src):
    """statistics.median (or a helper named median) -> mean."""
    if not re.search(r"\bmedian\b", src):
        return []
    out = re.sub(r"\bmedian\b", "mean", src)
    return [out] if out != src else []


TRANSFORMS = [
    t_fix_round,
    t_wrap_third,
    t_tuple_to_list,
    t_floordiv,
    t_subscript_to_mean,
    t_divide_third,
    t_init_fix,
    t_int_call,
    t_swap_minmax,
    t_median_name,
]

# rounding-style fixes composed on top of first-level variants
LEVEL2_TRANSFORMS = [t_fix_round, t_wrap_third, t_floordiv, t_tuple_to_list]


# --------------------------------------------------------------------------
# failure-pattern dispatch
# --------------------------------------------------------------------------

def _hint(source):
    """Classify the failure pattern: 'swap' (min/max exchanged), 'mean'
    (min/max right, mean wrong), or None."""
    try:
        r = failing_tests(source, ENTRY, TESTS)
        if not getattr(r, "compiled", False):
            return None
        fails = getattr(r, "failures", None) or []
        swapish = meanish = considered = 0
        for f in fails:
            got = f.get("got")
            exp = f.get("expected")
            if (
                isinstance(got, (list, tuple))
                and isinstance(exp, (list, tuple))
                and len(got) == 3
                and len(exp) == 3
            ):
                considered += 1
                if got[0] == exp[1] and got[1] == exp[0] and exp[0] != exp[1]:
                    swapish += 1
                elif got[0] == exp[0] and got[1] == exp[1]:
                    meanish += 1
        if considered and swapish:
            return "swap"
        if considered and meanish == considered:
            return "mean"
    except Exception:
        pass
    return None


# --------------------------------------------------------------------------
# main entry point
# --------------------------------------------------------------------------

def repair(source):
    try:
        if not isinstance(source, str) or _parse(source) is None:
            return None

        transforms = list(TRANSFORMS)
        if _hint(source) == "swap":
            transforms.remove(t_swap_minmax)
            transforms.insert(0, t_swap_minmax)

        # ---- stage 1: identity + problem-specific rewrites (+ combos) ----
        seen = {source}
        level1 = []
        for t in transforms:
            try:
                for v in t(source):
                    if v and v not in seen:
                        seen.add(v)
                        level1.append(v)
            except Exception:
                pass

        level2 = []
        for v in level1[:20]:
            for t in LEVEL2_TRANSFORMS:
                try:
                    for w in t(v):
                        if w and w not in seen:
                            seen.add(w)
                            level2.append(w)
                except Exception:
                    pass

        variants = [source] + level1 + level2
        try:
            res = first_passing(iter(variants), ENTRY, TESTS, source)
            if res is not None:
                return res
        except Exception:
            pass

        # ---- stage 2: generic single edits (source + top rewrites) ----
        try:
            gens = [candidates_generic(source, max_edits=1)]
            for v in (level1 + level2)[:6]:
                try:
                    gens.append(candidates_generic(v, max_edits=1))
                except Exception:
                    pass
            res = first_passing(
                chain(*gens), ENTRY, TESTS, source, max_rps=0.35, max_checks=800
            )
            if res is not None:
                return res
        except Exception:
            pass

        # ---- stage 3: generic paired edits on the original source ----
        try:
            res = first_passing(
                candidates_generic(source, max_edits=2, budget=2000),
                ENTRY,
                TESTS,
                source,
                max_rps=0.35,
                max_checks=800,
            )
            if res is not None:
                return res
        except Exception:
            pass

        return None
    except Exception:
        return None
