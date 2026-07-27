import ast
from src.core.repair import Rule


def _span(source, node):
    """(start, end) char offsets of node in source."""
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


def _replace_name_in_compare(source, old_name, new_name):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and left.id == old_name:
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + source[le:rs] + new_name + source[re:re]
                out.append(_splice(source, node, new_cmp))
            if isinstance(right, ast.Name) and right.id == old_name:
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + source[le:rs] + new_name + source[re:re]
                out.append(_splice(source, node, new_cmp))
    return out


def _fix_unique_day_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.left, ast.Subscript) and isinstance(node.comparators[0], ast.Name):
                sub = node.left
                comp = node.comparators[0]
                if isinstance(sub.slice, ast.Constant) and sub.slice.value == 1 and comp.id == "day":
                    ls, le = _span(source, sub)
                    rs, re = _span(source, comp)
                    new_cmp = source[ls:le] + source[le:rs] + "date" + source[re:re]
                    out.append(_splice(source, node, new_cmp))
            if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Subscript):
                comp = node.comparators[0]
                left = node.left
                if isinstance(comp.slice, ast.Constant) and comp.slice.value == 1 and left.id == "day":
                    ls, le = _span(source, left)
                    rs, re = _span(source, comp)
                    new_cmp = source[ls:le] + "date" + source[le:rs] + source[re:re]
                    out.append(_splice(source, node, new_cmp))
    return out


def _fix_contains_unique_day_iteration(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            if isinstance(node.iter, ast.Name) and node.iter.id == "possible_birthdays":
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.If):
                    if_node = body[0]
                    if isinstance(if_node.test, ast.Compare) and len(if_node.test.ops) == 1:
                        cmp = if_node.test
                        if isinstance(cmp.left, ast.Subscript) and isinstance(cmp.comparators[0], ast.Name):
                            sub = cmp.left
                            comp = cmp.comparators[0]
                            if isinstance(sub.slice, ast.Constant) and sub.slice.value == 0 and comp.id == "month":
                                ls, le = _span(source, comp)
                                out.append(_splice(source, node, source[_span(source, node)[0]:_span(source, node)[1]].replace("birthday[0]", "birthday[0]")))
    return out


def _fix_return_none_unique_month(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            for stmt in node.body:
                if isinstance(stmt, ast.If):
                    if len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Return):
                        if stmt.orelse == []:
                            text = ast.get_source_segment(source, stmt)
                            if text and "return True" in text and "return False" not in text:
                                new_text = text + "\n    else:\n        return False"
                                out.append(_splice(source, stmt, new_text))
    return out


def _fix_wrong_unique_day_arg(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
            if len(node.args) == 2:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Subscript):
                    sub = arg0
                    if isinstance(sub.slice, ast.Constant) and sub.slice.value == 1:
                        ls, le = _span(source, arg0)
                        out.append(_splice(source, arg0, "day"))
    return out


def _fix_day_variable_misname(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.left, ast.Subscript) and isinstance(node.comparators[0], ast.Name):
                sub = node.left
                comp = node.comparators[0]
                if isinstance(sub.slice, ast.Constant) and sub.slice.value == 1 and comp.id == "day":
                    ls, le = _span(source, comp)
                    out.append(_splice(source, comp, "date"))
            if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Subscript):
                left = node.left
                comp = node.comparators[0]
                if isinstance(comp.slice, ast.Constant) and comp.slice.value == 1 and left.id == "day":
                    ls, le = _span(source, left)
                    out.append(_splice(source, left, "date"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="unique_day_variable_name_day_to_date",
                apply=_fix_day_variable_misname,
                symptoms=("wrong",),
            ),
            Rule(
                name="unique_month_missing_false_return",
                apply=_fix_return_none_unique_month,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_pass_day_variable",
                apply=_fix_wrong_unique_day_arg,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_month_filter_iteration",
                apply=_fix_contains_unique_day_iteration,
                symptoms=("wrong",),
            ),
        ]