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


def _fix_unique_name_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_day":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == "day":
                    out.append(_splice(source, sub, "date"))
                    break
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == "days":
                    out.append(_splice(source, sub, "month"))
                    break
                if isinstance(sub, ast.Name) and sub.id == "day":
                    out.append(_splice(source, sub, "month"))
                    break
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == "unique_date":
                    out.append(_splice(source, sub, "unique_day"))
                    break
    return out


def _fix_unique_day_wrong_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_day":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == "day":
                    out.append(_splice(source, sub, "date"))
                    break
    return out


def _fix_unique_day_comparison(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                if (left.id, right.id) in {("day", "days"), ("days", "day"), ("day", "days_in_month"), ("days_in_month", "day")}: 
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new_cmp = source[ls:le] + " == " + source[rs:re]
                    out.append(_splice(source, node, new_cmp))
    return out


def _fix_contains_unique_day_false_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is True:
                out.append(_splice(source, node, "return False"))
                break
    return out


def _fix_contains_unique_day_return_unique_day(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"unique_date", "unique_month"}:
            out.append(_splice(source, node, "return False"))
    return out


def _fix_month_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            sl = node.slice
            if isinstance(sl, ast.Constant) and sl.value == 1:
                out.append(_splice(source, sl, "0"))
    return out


def _fix_count_vs_unique(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.LtE):
                left = node.left
                right = node.comparators[0]
                if isinstance(right, ast.Constant) and right.value == 1:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
            if isinstance(node.ops[0], ast.Gt):
                right = node.comparators[0]
                if isinstance(right, ast.Constant) and right.value == 1:
                    left = node.left
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
    return out


def _fix_contains_unique_day_return_stmt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and node.value is None:
                replacement = None
                body = func.body
                if len(body) == 1:
                    replacement = (
                        "    for birthday in possible_birthdays:\n"
                        "        if birthday[0] == month:\n"
                        "            if unique_day(birthday[1], possible_birthdays):\n"
                        "                return True\n"
                        "    return False"
                    )
                    out.append(_splice(source, func.body[0], replacement))
                break
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="replace_day_name_variable_with_parameter",
                apply=_fix_unique_name_mismatch,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_unique_day_parameter_name",
                apply=_fix_unique_day_wrong_name,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_day_comparison_identifier_mismatch",
                apply=_fix_unique_day_comparison,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_should_not_return_true_on_missing_case",
                apply=_fix_contains_unique_day_false_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="replace_unique_date_call_with_unique_day_logic",
                apply=_fix_contains_unique_day_return_unique_day,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_month_index_zero_based",
                apply=_fix_month_index,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="strict_one_should_be_exactly_one",
                apply=_fix_count_vs_unique,
                symptoms=("wrong",),
            ),
            Rule(
                name="implement_missing_contains_unique_day",
                apply=_fix_contains_unique_day_return_stmt,
                symptoms=("wrong",),
            ),
        ]