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


def _replace_compare_op(source, op_type, new_op):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], op_type):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            new_cmp = source[ls:le] + f" {new_op} " + source[rs:re]
            out.append(_splice(source, node, new_cmp))
    return out


def _fix_contains_unique_day(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
        if len(returns) == 1:
            ret = returns[0]
            if ret.value is None:
                continue
            s, e = _span(source, ret)
            new_text = "    for birthday in possible_birthdays:\n        if birthday[0] == month:\n            if unique_day(birthday[1], possible_birthdays):\n                return True\n    return False"
            out.append(source[:s] + new_text + source[e:])
    return out


def _fix_unique_day_month_return_bool(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in ("unique_day", "unique_month"):
            for node in ast.walk(fn):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.NameConstant):
                    if node.value.value is True or node.value.value is False:
                        continue
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Compare):
                    cmp = node.value
                    if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.NotEq):
                        s, e = _span(source, node)
                        out.append(source[:s] + "    return " + source[_span(source, cmp)[0]:_span(source, cmp)[1]].replace("!=", "==") + source[e:])
    return out


def _fix_count_greater_to_equals(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
    return out


def _fix_incorrect_index_2_to_0(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == 2:
            s, e = _span(source, node.slice)
            out.append(source[:s] + "0" + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="strict_gt_should_be_eq_for_uniqueness", apply=_fix_count_greater_to_equals, symptoms=("wrong",)),
            Rule(name="unique_day_month_should_use_equality_not_membership", apply=lambda s: _replace_compare_op(s, ast.In, "=="), symptoms=("wrong",)),
            Rule(name="fix_contains_unique_day_missing_logic", apply=_fix_contains_unique_day, symptoms=("wrong",)),
            Rule(name="generic_index_2_to_0", apply=_fix_incorrect_index_2_to_0, symptoms=("err:IndexError", "wrong")),
        ]