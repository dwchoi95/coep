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


def _literal_number_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, complex)):
            s, e = _span(source, node)
            text = source[s:e]
            if text == "4":
                out.append(_splice(source, node, "7"))
            elif text == "7":
                out.append(_splice(source, node, "4"))
    return out


def _literal_string_digit_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s, e = _span(source, node)
            text = source[s:e]
            if text == "'4'":
                out.append(_splice(source, node, "'7'"))
            elif text == "'7'":
                out.append(_splice(source, node, "'4'"))
            elif text == '"4"':
                out.append(_splice(source, node, '"7"'))
            elif text == '"7"':
                out.append(_splice(source, node, '"4"'))
    return out


def _compare_literal_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            right = node.comparators[0]
            if isinstance(right, ast.Constant):
                s, e = _span(source, right)
                text = source[s:e]
                if text == "4":
                    out.append(_splice(source, right, "7"))
                elif text == "7":
                    out.append(_splice(source, right, "4"))
                elif text == "'4'":
                    out.append(_splice(source, right, "'7'"))
                elif text == "'7'":
                    out.append(_splice(source, right, "'4'"))
                elif text == '"4"':
                    out.append(_splice(source, right, '"7"'))
                elif text == '"7"':
                    out.append(_splice(source, right, '"4"'))
    return out


def _fix_count_method_digit(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "count" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    s, e = _span(source, arg)
                    text = source[s:e]
                    if text in ("'4'", '"4"'):
                        out.append(_splice(source, arg, text[0] + "7" + text[0]))
                    elif text in ("'7'", '"7"'):
                        out.append(_splice(source, arg, text[0] + "4" + text[0]))
    return out


def _membership_condition_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.NotIn):
                left = node.left
                comp = node.comparators[0]
                if isinstance(comp, ast.List) and len(comp.elts) == 2:
                    s1, e1 = _span(source, left)
                    s2, e2 = _span(source, comp)
                    new_text = source[s1:e1] + " in " + source[s2:e2]
                    out.append(_splice(source, node, new_text))
    return out


def _bool_or_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
            if len(node.comparators) == 1 and isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Constant):
                right = node.comparators[0]
                if right.value in (4, 7):
                    s, e = _span(source, node)
                    text = source[s:e]
                    if "!=" in text:
                        out.append(_splice(source, node, text.replace("!=", "==", 1)))
    return out


def _yes_no_case_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s, e = _span(source, node)
            text = source[s:e]
            if text == "'Yes'":
                out.append(_splice(source, node, "'YES'"))
            elif text == "'No'":
                out.append(_splice(source, node, "'NO'"))
            elif text == '"Yes"':
                out.append(_splice(source, node, '"YES"'))
            elif text == '"No"':
                out.append(_splice(source, node, '"NO"'))
    return out


def _count_condition_not_in_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant):
                if node.comparators[0].value in (4, 7):
                    s, e = _span(source, node)
                    text = source[s:e]
                    if "==" in text:
                        out.append(_splice(source, node, text.replace("==", "not in", 1).replace(str(node.comparators[0].value), "[4,7]")))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="swap_miscounted_digit_constants", apply=_literal_number_fix, symptoms=("wrong",)),
            Rule(name="swap_digit_string_literals", apply=_literal_string_digit_fix, symptoms=("wrong",)),
            Rule(name="fix_comparison_digit_literal", apply=_compare_literal_fix, symptoms=("wrong",)),
            Rule(name="fix_count_argument_digit", apply=_fix_count_method_digit, symptoms=("wrong",)),
            Rule(name="fix_not_in_to_in_for_lucky_digits", apply=_membership_condition_fix, symptoms=("wrong",)),
            Rule(name="fix_boolean_logic_inequality", apply=_bool_or_fix, symptoms=("wrong",)),
            Rule(name="normalize_yes_no_output", apply=_yes_no_case_fix, symptoms=("wrong",)),
        ]