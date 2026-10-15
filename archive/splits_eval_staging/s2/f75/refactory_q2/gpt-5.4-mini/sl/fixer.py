from src.core.repair import Rule
import ast


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


def _replace_name_in_node_source(source, node, old, new):
    s, e = _span(source, node)
    text = source[s:e]
    if old not in text:
        return None
    return source[:s] + text.replace(old, new, 1) + source[e:]


def _fix_day_month_identity(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        if fn.name == "unique_day" and fn.args.args:
            arg = fn.args.args[0].arg
            if arg != "day":
                patched = _replace_name_in_node_source(source, fn, arg, "day")
                if patched is not None:
                    out.append(patched)
        if fn.name == "unique_month" and fn.args.args:
            arg = fn.args.args[0].arg
            if arg != "month":
                patched = _replace_name_in_node_source(source, fn, arg, "month")
                if patched is not None:
                    out.append(patched)
    return list(dict.fromkeys(out))


def _fix_contains_unique_day(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        text = ast.get_source_segment(source, fn)
        if text is None:
            continue
        candidates = []
        if "unique_date" in text:
            candidates.append(text.replace("unique_date", "unique_day"))
        if "return false" in text:
            candidates.append(text.replace("return false", "return False"))
        if "return True" in text and "days == 1" in text:
            pass
        for c in candidates:
            out.append(source[:_span(source, fn)[0]] + c + source[_span(source, fn)[1]:])
    return list(dict.fromkeys(out))


def _fix_count_vs_unique(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Gt):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left and right:
                    out.append(_splice(source, node, f"{left} == {right}"))
            if isinstance(op, ast.GtE):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left and right:
                    out.append(_splice(source, node, f"{left} == {right}"))
    return list(dict.fromkeys(out))


def _fix_false_lower(source):
    if "return false" not in source:
        return []
    return [source.replace("return false", "return False")]


def _fix_contains_return_only(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        seg = ast.get_source_segment(source, fn)
        if seg and seg.strip() == "def contains_unique_day(month, possible_birthdays):\n    return":
            replacement = """def contains_unique_day(month, possible_birthdays):
    for birthday in possible_birthdays:
        if birthday[0] == month:
            if unique_day(birthday[1], possible_birthdays):
                return True
    return False"""
            out.append(_splice(source, fn, replacement))
    return out


def _fix_day_month_index_mixups(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.left, ast.Subscript):
                seg = ast.get_source_segment(source, node)
                if seg:
                    if "[1] == days" in seg:
                        out.append(source.replace("[1] == days", "[1] == day"))
                    if "[0] == days" in seg:
                        out.append(source.replace("[0] == days", "[0] == month"))
                    if "date == possible_birthdays[i]" in seg:
                        out.append(source.replace("date == possible_birthdays[i]", "date == possible_birthdays[i][1]"))
    return list(dict.fromkeys(out))


def _fix_unique_day_truthiness(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("unique_day", "unique_month")]:
        seg = ast.get_source_segment(source, fn)
        if not seg:
            continue
        if "return count>=2" in seg:
            out.append(source.replace("return count>=2", "return count==1"))
        if "return count > 1" in seg and "return True" not in seg:
            out.append(source.replace("return count > 1", "return count == 1"))
        if "if count > 1:\n        return False\n    else:\n        return True" in seg:
            out.append(source.replace("if count > 1:\n        return False\n    else:\n        return True",
                                      "if count == 1:\n        return True\n    else:\n        return False"))
    return list(dict.fromkeys(out))


class Fixer:
    def rules(self):
        return [
            Rule(name="rename_day_parameter", apply=_fix_day_month_identity, symptoms=("wrong",)),
            Rule(name="contains_unique_day_return_fix", apply=_fix_contains_unique_day, symptoms=("wrong",)),
            Rule(name="comparison_count_threshold", apply=_fix_count_vs_unique, symptoms=("wrong",)),
            Rule(name="lowercase_false", apply=_fix_false_lower, symptoms=("err:NameError", "wrong")),
            Rule(name="contains_unique_day_return_impl", apply=_fix_contains_return_only, symptoms=("wrong",)),
            Rule(name="subscript_index_mixup", apply=_fix_day_month_index_mixups, symptoms=("wrong",)),
            Rule(name="unique_day_month_truthiness", apply=_fix_unique_day_truthiness, symptoms=("wrong",)),
        ]