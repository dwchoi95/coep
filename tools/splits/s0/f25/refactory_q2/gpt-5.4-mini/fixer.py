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


def _replace_node(source, old, new):
    return _splice(source, old, new)


def _is_name(node, names):
    return isinstance(node, ast.Name) and node.id in names


def _fix_unique_count_comparison(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Gt):
                left, right = node.left, node.comparators[0]
                new = f"{ast.get_source_segment(source, left)} == {ast.get_source_segment(source, right)}"
                out.append(_replace_node(source, node, new))
            elif isinstance(op, ast.GtE):
                left, right = node.left, node.comparators[0]
                new = f"{ast.get_source_segment(source, left)} == {ast.get_source_segment(source, right)}"
                out.append(_replace_node(source, node, new))
            elif isinstance(op, ast.LtE):
                left, right = node.left, node.comparators[0]
                new = f"{ast.get_source_segment(source, left)} == {ast.get_source_segment(source, right)}"
                out.append(_replace_node(source, node, new))
    return out


def _fix_str_day_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "str":
                if len(left.args) == 1 and isinstance(right, ast.Subscript):
                    seg = ast.get_source_segment(source, left.args[0])
                    new = f"{seg} == {ast.get_source_segment(source, right)}"
                    out.append(_replace_node(source, node, new))
    return out


def _fix_rhs_name_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Name):
                l = node.left.id
                r = node.comparators[0].id
                if l in {"days", "day"} and r in {"date", "days"}:
                    new = f"{ast.get_source_segment(source, node.left)} == {ast.get_source_segment(source, node.comparators[0])}"
                    out.append(_replace_node(source, node, new))
    return out


def _fix_broken_uniqueness_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {"unique_day", "unique_month"}:
            for stmt in node.body:
                if isinstance(stmt, ast.Return):
                    txt = ast.get_source_segment(source, stmt)
                    if txt == "return True":
                        out.append(source[:_span(source, stmt)[0]] + "return count == 1" + source[_span(source, stmt)[1]:])
                    elif txt == "return False":
                        continue
    return out


def _fix_contains_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            if any(isinstance(s, ast.Return) and isinstance(s.value, ast.NameConstant) and s.value.value is None for s in node.body):
                continue
            if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                out.append(_replace_node(source, node.body[0], "    for i in possible_birthdays:\n        if i[0] == month:\n            if unique_day(i[1], possible_birthdays):\n                return True\n    return False"))
    return out


def _fix_single_return_inside_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            for stmt in node.body:
                if isinstance(stmt, ast.For):
                    if any(isinstance(s, ast.Return) and s.value is not None for s in ast.walk(stmt)):
                        src = ast.get_source_segment(source, stmt)
                        if "return unique_day" in src and "if unique_day" in src:
                            continue
    return out


def _fix_contains_unique_day_patterns(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            src = ast.get_source_segment(source, node)
            if src is None:
                continue
            if "return True" in src and "return False" in src and "if unique_day" in src:
                continue
    return out


def _fix_day_month_arg_mixups(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Subscript):
                seg = ast.get_source_segment(source, node)
                if "month == possible_birthdays" in seg and "[0]" in seg:
                    continue
                if "day == possible_birthdays" in seg and "[1]" in seg:
                    continue
    return out


def _fix_wrong_index_in_unique_month(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            src = ast.get_source_segment(source, node)
            if src and "birthday[1]" in src and "month == birthday[1]" in src:
                out.append(src.replace("birthday[1]", "birthday[0]").replace("month == birthday[1]", "month == birthday[0]"))
    return out


def _fix_unique_day_contains_in(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_day":
            src = ast.get_source_segment(source, node)
            if src and "if day in i" in src:
                out.append(src.replace("if day in i", "if day == i[1]"))
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            src = ast.get_source_segment(source, node)
            if src and "if month in i" in src:
                out.append(src.replace("if month in i", "if month == i[0]"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="count_should_compare_equality", apply=_fix_unique_count_comparison, symptoms=("wrong",)),
            Rule(name="stringify_day_argument_mismatch", apply=_fix_str_day_compare, symptoms=("wrong",)),
            Rule(name="compare_var_names_not_constants", apply=_fix_rhs_name_mismatch, symptoms=("wrong",)),
            Rule(name="unique_day_month_return_true_should_be_count_check", apply=_fix_broken_uniqueness_return, symptoms=("wrong",)),
            Rule(name="contains_unique_day_should_scan_matching_months", apply=_fix_contains_return, symptoms=("wrong",)),
            Rule(name="contains_unique_day_return_inside_loop", apply=_fix_single_return_inside_loop, symptoms=("wrong",)),
            Rule(name="wrong_index_month_check", apply=_fix_wrong_index_in_unique_month, symptoms=("wrong",)),
            Rule(name="membership_vs_equality", apply=_fix_unique_day_contains_in, symptoms=("wrong",)),
        ]