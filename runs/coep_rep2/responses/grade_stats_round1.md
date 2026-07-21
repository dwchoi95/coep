```python
import ast
import itertools

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

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


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _const(v):
    return ast.Constant(value=v, kind=None)


def _name(n):
    return ast.Name(id=n, ctx=ast.Load())


def _is_round(node):
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "round")


def _round2(expr):
    return ast.Call(func=_name("round"), args=[expr, _const(2)], keywords=[])


def _is_num(node):
    return (isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool))


def _sum_over_len(varname):
    return ast.BinOp(
        left=ast.Call(func=_name("sum"), args=[_name(varname)], keywords=[]),
        op=ast.Div(),
        right=ast.Call(func=_name("len"), args=[_name(varname)], keywords=[]),
    )


def _preorder(node):
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _preorder(child)


class _ReplaceNth(ast.NodeTransformer):
    """Apply `builder` to the target-th node (preorder) matching `pred`."""

    def __init__(self, pred, builder, target):
        self.pred = pred
        self.builder = builder
        self.target = target
        self.count = -1

    def visit(self, node):
        if self.count < self.target and self.pred(node):
            self.count += 1
            if self.count == self.target:
                try:
                    new = self.builder(node)
                except Exception:
                    new = None
                if new is not None:
                    try:
                        ast.copy_location(new, node)
                    except Exception:
                        pass
                    return new
        return self.generic_visit(node)


def _apply_rule(source, pred, builder):
    try:
        base = ast.parse(source)
    except Exception:
        return
    total = sum(1 for n in _preorder(base) if pred(n))
    for i in range(total):
        try:
            tree = ast.parse(source)
            tree = _ReplaceNth(pred, builder, i).visit(tree)
            ast.fix_missing_locations(tree)
            yield ast.unparse(tree)
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules for grade_stats
# ---------------------------------------------------------------------------

def _find_param(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            if node.args.args:
                return node.args.args[0].arg
    return "scores"


def _third_ret_var(tree):
    """Name of the variable used as the mean slot of the returned triple."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Return)
                and isinstance(node.value, (ast.List, ast.Tuple))
                and len(node.value.elts) == 3):
            e = node.value.elts[2]
            if _is_round(e) and e.args and isinstance(e.args[0], ast.Name):
                return e.args[0].id
            if isinstance(e, ast.Name):
                return e.id
    return None


def _build_rules(source):
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    param = _find_param(tree)
    mean_var = _third_ret_var(tree)

    def is_ret3(n):
        return (isinstance(n, ast.Return)
                and isinstance(n.value, (ast.List, ast.Tuple))
                and len(n.value.elts) == 3)

    rules = []

    # returned tuple instead of list
    def b_tuple(n):
        if not isinstance(n.value, ast.Tuple):
            return None
        n.value = ast.List(elts=list(n.value.elts), ctx=ast.Load())
        return n
    rules.append((is_ret3, b_tuple))

    # forgot to round the mean: wrap third element in round(x, 2)
    def b_wrap3(n):
        e = list(n.value.elts)
        if _is_round(e[2]):
            return None
        e[2] = _round2(e[2])
        n.value = ast.List(elts=e, ctx=ast.Load())
        return n
    rules.append((is_ret3, b_wrap3))

    # min and max swapped in the returned triple
    def b_swap01(n):
        e = list(n.value.elts)
        n.value = ast.List(elts=[e[1], e[0], e[2]], ctx=ast.Load())
        return n
    rules.append((is_ret3, b_swap01))

    # min/max wrongly rounded (breaks e.g. 2.675): unwrap round on slot 0/1
    def b_unwrap0(n):
        e = list(n.value.elts)
        if not (_is_round(e[0]) and e[0].args):
            return None
        e[0] = e[0].args[0]
        n.value = ast.List(elts=e, ctx=ast.Load())
        return n
    rules.append((is_ret3, b_unwrap0))

    def b_unwrap1(n):
        e = list(n.value.elts)
        if not (_is_round(e[1]) and e[1].args):
            return None
        e[1] = e[1].args[0]
        n.value = ast.List(elts=e, ctx=ast.Load())
        return n
    rules.append((is_ret3, b_unwrap1))

    # wrong statistic in the mean slot: replace with round(sum(p)/len(p), 2)
    def b_mean3(n):
        e = list(n.value.elts)
        e[2] = _round2(_sum_over_len(param))
        n.value = ast.List(elts=e, ctx=ast.Load())
        return n
    rules.append((is_ret3, b_mean3))

    # bad round() usage anywhere: missing precision, wrong precision,
    # or swapped arguments like round(1, mean)
    def b_round_norm(n):
        args = n.args
        if len(args) == 1:
            if _is_num(args[0]):
                return None
            n.args = [args[0], _const(2)]
            return n
        if len(args) == 2:
            if _is_num(args[0]) and not _is_num(args[1]):
                n.args = [args[1], _const(2)]
                return n
            if not (isinstance(args[1], ast.Constant) and args[1].value == 2):
                n.args = [args[0], _const(2)]
                return n
        return None
    rules.append((_is_round, b_round_norm))

    # min/max confused (single occurrence swap)
    def is_minmax(n):
        return (isinstance(n, ast.Name) and n.id in ("min", "max")
                and isinstance(n.ctx, ast.Load))

    def b_minmax(n):
        n.id = "max" if n.id == "min" else "min"
        return n
    rules.append((is_minmax, b_minmax))

    # truncation with int(...) instead of round(..., 2)
    def is_int_call(n):
        return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "int" and len(n.args) == 1)

    def b_int(n):
        n.func = _name("round")
        n.args = [n.args[0], _const(2)]
        return n
    rules.append((is_int_call, b_int))

    # a division assigned to a variable but never rounded (also fixes //)
    def is_div_assign(n):
        return (isinstance(n, ast.Assign) and isinstance(n.value, ast.BinOp)
                and isinstance(n.value.op, (ast.Div, ast.FloorDiv)))

    def b_div_assign(n):
        n.value = _round2(ast.BinOp(left=n.value.left, op=ast.Div(),
                                    right=n.value.right))
        return n
    rules.append((is_div_assign, b_div_assign))

    # wrong initialization of a running min/max (e.g. lo = 0) -> param[0]
    def is_const_assign(n):
        return (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and _is_num(n.value))

    def b_const_assign(n):
        n.value = ast.Subscript(value=_name(param), slice=_const(0),
                                ctx=ast.Load())
        return n
    rules.append((is_const_assign, b_const_assign))

    # median instead of mean: X[len(X) // 2] -> sum(X) / len(X)
    def is_median(n):
        if not (isinstance(n, ast.Subscript)
                and isinstance(n.value, ast.Name)):
            return False
        sl = n.slice
        return (isinstance(sl, ast.BinOp)
                and isinstance(sl.op, (ast.FloorDiv, ast.Div))
                and isinstance(sl.left, ast.Call)
                and isinstance(sl.left.func, ast.Name)
                and sl.left.func.id == "len")

    def b_median(n):
        return _sum_over_len(n.value.id)
    rules.append((is_median, b_median))

    # the variable feeding the mean slot computes something wrong:
    # rewrite its right-hand side to the true mean
    if mean_var:
        def is_mean_assign(n):
            return (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id == mean_var)

        def b_mean_assign(n):
            n.value = _sum_over_len(param)
            return n

        def b_mean_assign_round(n):
            n.value = _round2(_sum_over_len(param))
            return n
        rules.append((is_mean_assign, b_mean_assign))
        rules.append((is_mean_assign, b_mean_assign_round))

    return rules


def _problem_specific(source, rules):
    for pred, builder in rules:
        yield from _apply_rule(source, pred, builder)


def _second_order(source, rules, limit_first=60, limit_total=350):
    firsts = list(itertools.islice(_problem_specific(source, rules),
                                   limit_first))
    n = 0
    for cand in firsts:
        try:
            crules = _build_rules(cand)
        except Exception:
            continue
        for c2 in _problem_specific(cand, crules):
            yield c2
            n += 1
            if n >= limit_total:
                return


def _dedup(gen):
    seen = set()
    for c in gen:
        if not isinstance(c, str):
            continue
        key = c.strip()
        if key in seen:
            continue
        seen.add(key)
        yield c


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def repair(source: str) -> str | None:
    try:
        if not isinstance(source, str):
            return None
        try:
            ast.parse(source)
        except Exception:
            return None

        rules = _build_rules(source)

        def gen():
            # the submission itself (it might already pass)
            yield source
            # problem-specific single rewrites
            yield from _problem_specific(source, rules)
            # generic single semantic edits
            yield from candidates_generic(source, max_edits=1)
            # pairs of problem-specific rewrites
            yield from _second_order(source, rules)
            # generic edit pairs as a last resort
            yield from candidates_generic(source, max_edits=2, budget=2000)

        return first_passing(_dedup(gen()), ENTRY, TESTS, source,
                             max_rps=0.35, max_checks=800)
    except Exception:
        return None
```
