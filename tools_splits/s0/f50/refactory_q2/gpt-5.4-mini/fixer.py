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


def _get_func(tree, name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _replace_name_in_namefunc(source, func, old, new):
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == old:
            out.append(_splice(source, node, new))
    return out


def _replace_name_in_attrs(source, func, old, new):
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == old:
            out.append(_splice(source, node, new))
    return out


def _compare_to_eq(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.LtE):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(source[:ls] + source[ls:le] + " == " + source[rs:re] + source[re:])
            elif isinstance(op, ast.GtE):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(source[:ls] + source[ls:le] + " == " + source[rs:re] + source[re:])
            elif isinstance(op, ast.Gt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(source[:ls] + source[ls:le] + " == " + source[rs:re] + source[re:])
    return out


def _fix_day_param_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fname, old, new in [("unique_day", "date", "day"), ("unique_day", "day", "date")]:
        func = _get_func(tree, fname)
        if func and func.args.args and func.args.args[0].arg == old:
            arg = func.args.args[0]
            out.append(_splice(source, arg, new))
    return out


def _fix_month_param_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _get_func(tree, "unique_month")
    if func and func.args.args:
        arg = func.args.args[0]
        if arg.arg == "day":
            out.append(_splice(source, arg, "month"))
    return out


def _fix_contains_unique_day_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _get_func(tree, "contains_unique_day")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is True:
            out.append(_splice(source, node.value, "False"))
        if isinstance(node, ast.Return) and node.value is None:
            out.append(_splice(source, node, "return False"))
    return out


def _fix_contains_unique_day_month_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _get_func(tree, "contains_unique_day")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            if node.slice.value == 1 and isinstance(node.value, ast.Name):
                out.append(_splice(source, node.slice, "0"))
    return out


def _fix_unique_day_day_misuse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _get_func(tree, "unique_day")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == "day":
            parent_ok = True
            out.append(_splice(source, node, "date"))
            break
    return out


def _fix_unique_month_month_misuse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _get_func(tree, "unique_month")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == 1:
            out.append(_splice(source, node.slice, "0"))
            break
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="day_parameter_name",
                apply=_fix_day_param_name,
                symptoms=("wrong",),
            ),
            Rule(
                name="month_parameter_name",
                apply=_fix_month_param_name,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_to_equality",
                apply=_compare_to_eq,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_return_false_on_success",
                apply=_fix_contains_unique_day_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_month_index",
                apply=_fix_contains_unique_day_month_index,
                symptoms=("wrong",),
            ),
            Rule(
                name="unique_day_name_fix",
                apply=_fix_unique_day_day_misuse,
                symptoms=("wrong",),
            ),
            Rule(
                name="unique_month_month_index_fix",
                apply=_fix_unique_month_month_misuse,
                symptoms=("wrong",),
            ),
        ]