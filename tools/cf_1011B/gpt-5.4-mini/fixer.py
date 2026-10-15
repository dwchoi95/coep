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


def _replace_node(source, old_node, new_node):
    return _splice(source, old_node, new_node)


def _binary_op_fix(source, op_type, new_op_src):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, op_type):
            ls, le = _span(source, node.left)
            rs, re = _span(source, node.right)
            out.append(_splice(source, node, source[ls:le] + f" {new_op_src} " + source[rs:re]))
    return out


def _compare_op_fix(source, old_op_type, new_op_src):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], old_op_type):
            ls, le = _span(source, node.left)
            rs, re = _span(source, node.comparators[0])
            out.append(_splice(source, node, source[ls:le] + f" {new_op_src} " + source[rs:re]))
    return out


def _range_bound_fix(source, delta):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) in (1, 2, 3):
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    new = str(arg.value + delta)
                    out.append(_splice(source, arg, new))
            else:
                last = node.args[-1]
                if isinstance(last, ast.Constant) and isinstance(last.value, int):
                    new = str(last.value + delta)
                    out.append(_splice(source, last, new))
    return out


def _fix_return_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            if node.value.id == "False":
                out.append(_splice(source, node.value, "0"))
            elif node.value.id == "True":
                out.append(_splice(source, node.value, "1"))
    return out


def _fix_constant_bound_100_to_100000(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and node.value == 100:
            out.append(_splice(source, node, "100000"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="increase_binary_search_upper_bound",
                apply=_fix_constant_bound_100_to_100000,
                symptoms=("wrong",),
            ),
            Rule(
                name="lt_to_lte",
                apply=lambda s: _compare_op_fix(s, ast.Lt, "<="),
                symptoms=("wrong",),
            ),
            Rule(
                name="gt_to_gte",
                apply=lambda s: _compare_op_fix(s, ast.Gt, ">="),
                symptoms=("wrong",),
            ),
            Rule(
                name="add_range_upper_off_by_one",
                apply=lambda s: _range_bound_fix(s, 1),
                symptoms=("wrong",),
            ),
            Rule(
                name="subtract_range_upper_off_by_one",
                apply=lambda s: _range_bound_fix(s, -1),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_boolean_return_literal",
                apply=_fix_return_name,
                symptoms=("wrong",),
            ),
        ]