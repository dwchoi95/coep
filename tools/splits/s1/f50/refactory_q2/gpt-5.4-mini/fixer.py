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


def _find_func(tree, name):
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _replace_name_in_func(source, func, old, new):
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == old:
            out.append(_splice(source, node, new))
    return out


def _replace_const_in_func(source, func, old, new):
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Constant) and node.value == old:
            out.append(_splice(source, node, new))
    return out


def _fix_unique_day_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _find_func(tree, "unique_day")
    if not func or not func.args.args:
        return []
    arg = func.args.args[0]
    if arg.arg != "day":
        out.append(_splice(source, arg, "day"))
    return out


def _fix_unique_month_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _find_func(tree, "unique_month")
    if not func or not func.args.args:
        return []
    arg = func.args.args[0]
    if arg.arg != "month":
        out.append(_splice(source, arg, "month"))
    return out


def _fix_contains_unique_day_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _find_func(tree, "contains_unique_day")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
            if len(node.args) == 1:
                continue
            new = ast.unparse(node.args[0]) + ", possible_birthdays"
            out.append(_splice(source, node, f"unique_day({new})"))
    return out


def _fix_unique_day_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _find_func(tree, "unique_day")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left = ast.unparse(node.left)
            right = ast.unparse(node.comparators[0])
            if right == "day":
                out.append(_splice(source, node, f"{left} == day"))
            elif left == "day":
                out.append(_splice(source, node, f"day == {right}"))
    return out


def _fix_unique_month_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _find_func(tree, "unique_month")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left = ast.unparse(node.left)
            right = ast.unparse(node.comparators[0])
            if right == "month":
                out.append(_splice(source, node, f"{left} == month"))
            elif left == "month":
                out.append(_splice(source, node, f"month == {right}"))
    return out


def _fix_len_count_eq(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            left = ast.unparse(node.left)
            right = ast.unparse(node.comparators[0])
            if right == "1":
                out.append(_splice(source, node, f"{left} == 1"))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left = ast.unparse(node.left)
            right = ast.unparse(node.comparators[0])
            if right == "1":
                out.append(_splice(source, node, f"{left} == 1"))
    return out


def _fix_contains_return_false(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = _find_func(tree, "contains_unique_day")
    if not func:
        return []
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value in (True, False):
            if node.value.value is True:
                out.append(_splice(source, node, "return False"))
    return out


def _fix_wrong_day_membership(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            left = ast.unparse(node.left)
            right = ast.unparse(node.comparators[0])
            if left == "day" and right.endswith("[1]"):
                out.append(_splice(source, node, f"{right} == day"))
            if left == "month" and right.endswith("[0]"):
                out.append(_splice(source, node, f"{right} == month"))
    return out


def _fix_unique_day_call_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "unique_date":
            out.append(_splice(source, node, "unique_day"))
    return out


def _fix_false_lowercase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "false":
            out.append(_splice(source, node, "False"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="unique_day_param_should_be_day", apply=_fix_unique_day_param, symptoms=("wrong",)),
            Rule(name="unique_month_param_should_be_month", apply=_fix_unique_month_param, symptoms=("wrong",)),
            Rule(name="contains_unique_day_should_pass_day_argument", apply=_fix_contains_unique_day_call, symptoms=("wrong",)),
            Rule(name="unique_day_compare_against_parameter", apply=_fix_unique_day_compare, symptoms=("wrong",)),
            Rule(name="unique_month_compare_against_parameter", apply=_fix_unique_month_compare, symptoms=("wrong",)),
            Rule(name="count_must_equal_one_not_at_most_one", apply=_fix_len_count_eq, symptoms=("wrong",)),
            Rule(name="contains_unique_day_should_not_return_early_true", apply=_fix_contains_return_false, symptoms=("wrong",)),
            Rule(name="membership_check_should_be_equality", apply=_fix_wrong_day_membership, symptoms=("wrong",)),
            Rule(name="unique_date_typo_to_unique_day", apply=_fix_unique_day_call_name, symptoms=("err:NameError", "wrong")),
            Rule(name="lowercase_false_to_false", apply=_fix_false_lowercase, symptoms=("err:NameError",)),
        ]