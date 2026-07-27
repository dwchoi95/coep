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


def _replace_node(source, target, new_node):
    s, e = _span(source, target)
    return source[:s] + ast.get_source_segment(source, new_node) + source[e:]


def _digit_compare_to_str(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                left = node.left
                right = node.comparators[0]
                for side in (left, right):
                    if isinstance(side, ast.Constant) and isinstance(side.value, int) and side.value in (4, 7):
                        s, e = _span(source, side)
                        out.append(source[:s] + repr(str(side.value)) + source[e:])
    return out


def _swap_n_not_n(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                txt = ast.get_source_segment(source, node)
                if txt and " n==" in " " + txt or " n ==" in txt:
                    continue
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left == "n" and right in {"4", "7"}:
                out.append(_splice(source, node, f"a == {right}"))
    return out


def _fix_while_digit_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.BoolOp):
            txt = ast.get_source_segment(source, node.test)
            if not txt:
                continue
            if "n==4" in txt and "n==7" in txt:
                out.append(source.replace("if n==4 or n==7:", "if a==4 or a==7:"))
    return out


def _fix_string_digits(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.Eq):
                ltxt = ast.get_source_segment(source, node.left)
                rtxt = ast.get_source_segment(source, node.comparators[0])
                if (ltxt == "i" and rtxt in {"4", "7"}) or (rtxt == "i" and ltxt in {"4", "7"}):
                    if ltxt == "i":
                        s, e = _span(source, node.comparators[0])
                        out.append(source[:s] + repr(rtxt) + source[e:])
                    else:
                        s, e = _span(source, node.left)
                        out.append(source[:s] + repr(ltxt) + source[e:])
    return out


def _fix_all_lucky_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            txt = ast.get_source_segment(source, node.test)
            if txt and "not in [\"4\",\"7\"]" in txt.replace(" ", ""):
                out.append(source.replace("if i not in [\"4\",\"7\"]:", "if i in [\"4\",\"7\"]:"))
            if txt and ("S != 4 or S != 7" in txt or "S!=4 or S!=7" in txt):
                out.append(source.replace("if S != 4 or S != 7:", "if S not in [4,7]:"))
    return out


def _fix_case_output(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in {"Yes", "No"}:
            s, e = _span(source, node)
            if node.value == "Yes":
                out.append(source[:s] + repr("YES") + source[e:])
            else:
                out.append(source[:s] + repr("NO") + source[e:])
    return out


def _fix_count_modulo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "c % 4 == 0 or c % 7 == 0" in txt:
                    out.append(source.replace("if c % 4 == 0 or c % 7 == 0:", "if c == 4 or c == 7:"))
                if txt and "c==4 or c==7" in txt.replace(" ", ""):
                    pass
        if isinstance(node, ast.If):
            txt = ast.get_source_segment(source, node.test)
            if txt and "c % 4 == 0 or c % 7 == 0" in txt:
                out.append(source.replace("if c % 4 == 0 or c % 7 == 0:", "if c != 0 and c == 4 or c == 7:"))
    return out


def _fix_counting_wrong_digit(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            txt = ast.get_source_segment(source, node)
            if txt and "cik2=cik" in source and 'n.count("4")' in source:
                out.append(source.replace('cik2=n.count("4")', 'cik2=n.count("7")'))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="digit_compare_int_to_str", apply=_digit_compare_to_str, symptoms=("wrong",)),
            Rule(name="wrong_variable_in_digit_check", apply=_fix_while_digit_check, symptoms=("wrong",)),
            Rule(name="compare_digit_as_int_in_string_loop", apply=_fix_string_digits, symptoms=("wrong",)),
            Rule(name="fix_not_inclusion_and_de_morgan", apply=_fix_all_lucky_condition, symptoms=("wrong",)),
            Rule(name="fix_output_case", apply=_fix_case_output, symptoms=("wrong",)),
            Rule(name="fix_count_modulo_logic", apply=_fix_count_modulo, symptoms=("wrong",)),
        ]