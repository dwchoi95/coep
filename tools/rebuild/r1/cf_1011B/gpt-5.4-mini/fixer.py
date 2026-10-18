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


def _replace_number_literal(source, node, new_value):
    return _splice(source, node, str(new_value))


def _max_bound_100_to_100000(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if node.value.value == 100:
                out.append(_replace_number_literal(source, node.value, 100000))
    return out


def _extend_small_upper_bound_to_100(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if node.value.value == 1:
                out.append(_replace_number_literal(source, node.value, 100))
    return out


def _lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re]))
    return out


def _gt_to_ge(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " >= " + source[rs:re]))
    return out


def _fix_off_by_one_range(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2:
                second = node.args[1]
                if isinstance(second, ast.BinOp) and isinstance(second.op, ast.Sub) and isinstance(second.right, ast.Constant) and second.right.value == 1:
                    ls, le = _span(source, second.left)
                    out.append(_splice(source, second, source[ls:le]))
    return out


def _fix_return_false_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is False:
            out.append(_splice(source, node.value, "0"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="binary_search_upper_bound_100_to_100000",
                apply=_max_bound_100_to_100000,
                symptoms=("wrong",),
            ),
            Rule(
                name="single_day_upper_bound_1_to_100",
                apply=_extend_small_upper_bound_to_100,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_to_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_to_gte",
                apply=_gt_to_ge,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_end_minus_one_off_by_one",
                apply=_fix_off_by_one_range,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_false_to_zero",
                apply=_fix_return_false_zero,
                symptoms=("wrong", "err:TypeError"),
            ),
        ]