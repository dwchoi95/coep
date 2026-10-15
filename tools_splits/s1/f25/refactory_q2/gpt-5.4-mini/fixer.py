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


def _collect_func(tree, name):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _fix_wrong_param_reference(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    funcs = _collect_func(tree, "unique_day")
    for fn in funcs:
        if len(fn.args.args) >= 1:
            param = fn.args.args[0].arg
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and node.id == "day":
                    out.append(_splice(source, node, param))
                    break
    funcs = _collect_func(tree, "unique_month")
    for fn in funcs:
        if len(fn.args.args) >= 1:
            param = fn.args.args[0].arg
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and node.id == "date":
                    out.append(_splice(source, node, param))
                    break
    return out


def _fix_leq_to_eq(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            new_cmp = source[ls:le] + " == " + source[rs:re]
            out.append(_splice(source, node, new_cmp))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            new_cmp = source[ls:le] + " == " + source[rs:re]
            out.append(_splice(source, node, new_cmp))
    return out


def _fix_in_to_eq_on_day_month(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            left = node.left
            right = node.comparators[0]
            if isinstance(right, ast.Subscript) and isinstance(right.slice, ast.Constant) and right.slice.value in (0, 1):
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                op = " == "
                new_cmp = source[ls:le] + op + source[rs:re]
                out.append(_splice(source, node, new_cmp))
    return out


def _fix_return_true_default(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _collect_func(tree, "unique_day") + _collect_func(tree, "unique_month"):
        if fn.body and isinstance(fn.body[-1], ast.Return) and isinstance(fn.body[-1].value, ast.Constant) and fn.body[-1].value.value is True:
            out.append(_splice(source, fn.body[-1], "return False"))
    return out


def _fix_contains_wrong_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _collect_func(tree, "contains_unique_day"):
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is True:
                out.append(_splice(source, node, "return False"))
    return out


def _fix_count_threshold(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            if isinstance(node.left, ast.Name) and node.left.id in {"count", "counter", "total", "result", "num", "check", "appearance", "days", "months"}:
                left = node.left
                right = node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
    return out


def _fix_contains_use_month_filter(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _collect_func(tree, "contains_unique_day"):
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Name):
                    out.append(_splice(source, node, f"{source[_span(source, node.left)[0]:_span(source, node.left)[1]]} == {source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]}"))
                    break
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="wrong_parameter_reference", apply=_fix_wrong_param_reference, symptoms=("wrong",)),
            Rule(name="count_threshold_to_exactly_one", apply=_fix_count_threshold, symptoms=("wrong",)),
            Rule(name="contains_unique_day_month_equality", apply=_fix_contains_use_month_filter, symptoms=("wrong",)),
            Rule(name="membership_to_equality_in_comparisons", apply=_fix_in_to_eq_on_day_month, symptoms=("wrong",)),
            Rule(name="strict_default_return_false", apply=_fix_return_true_default, symptoms=("wrong",)),
            Rule(name="contains_unique_day_default_false", apply=_fix_contains_wrong_return, symptoms=("wrong",)),
            Rule(name="gt_to_eq_in_uniqueness_check", apply=_fix_leq_to_eq, symptoms=("wrong",)),
        ]