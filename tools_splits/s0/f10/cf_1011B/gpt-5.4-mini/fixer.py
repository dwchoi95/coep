import ast
from src.core.repair import Rule


def _span(source, node):
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _replace_node(source, target, new_text):
    return _splice(source, target, new_text)


def _collect_candidates(source, tree, pred, build):
    out = []
    for node in ast.walk(tree):
        if pred(node):
            try:
                out.append(_replace_node(source, node, build(source, node)))
            except Exception:
                pass
    return out


def _cmp_flip_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    ops = {
        ast.Lt: ">=",
        ast.LtE: ">",
        ast.Gt: "<=",
        ast.GtE: "<",
        ast.Eq: "!=",
        ast.NotEq: "==",
    }

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            for k, sym in ops.items():
                if isinstance(op, k):
                    left = node.left
                    right = node.comparators[0]
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new_cmp = source[ls:le] + f" {sym} " + source[rs:re]
                    out.append(_splice(source, node, new_cmp))
                    break
    return out


def _range_bound_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) >= 1:
            last = node.args[-1]
            if isinstance(last, ast.BinOp) and isinstance(last.op, ast.Add):
                for side in (last.left, last.right):
                    if isinstance(side, ast.Constant) and isinstance(side.value, int) and side.value == 1:
                        other = last.right if side is last.left else last.left
                        out.append(_splice(source, last, source[_span(source, other)[0]:_span(source, other)[1]]))
                        return out
            if isinstance(last, ast.BinOp) and isinstance(last.op, ast.Sub):
                for side in (last.left, last.right):
                    if isinstance(side, ast.Constant) and isinstance(side.value, int) and side.value == 1:
                        other = last.right if side is last.left else last.left
                        out.append(_splice(source, last, source[_span(source, other)[0]:_span(source, other)[1]]))
                        return out
    return out


def _return_zero_to_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value == 0:
            out.append(_splice(source, node.value, "1"))
    return out


def _wrong_max_to_min_in_len_division(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "max" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.FloorDiv):
                if isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name) and arg.left.func.id == "len":
                    out.append(_splice(source, node.func, "min"))
    return out


def _ceil_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add):
                for side in (node.left.left, node.left.right):
                    if isinstance(side, ast.Constant) and isinstance(side.value, int) and side.value == 1:
                        out.append(_splice(source, node.left, source[_span(source, node.left.left)[0]:_span(source, node.left.left)[1]]))
                        return out
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="comparison_flip", apply=_cmp_flip_rule, symptoms=("wrong",)),
            Rule(name="range_bound_off_by_one", apply=_range_bound_fix, symptoms=("wrong",)),
            Rule(name="return_zero_to_one", apply=_return_zero_to_one, symptoms=("wrong",)),
            Rule(name="max_to_min_len_division", apply=_wrong_max_to_min_in_len_division, symptoms=("wrong",)),
            Rule(name="ceil_half_as_floor", apply=_ceil_fix, symptoms=("wrong",)),
        ]