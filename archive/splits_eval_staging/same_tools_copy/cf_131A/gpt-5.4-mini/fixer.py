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


def _replace_node(source, target, new_text):
    return _splice(source, target, new_text)


def _is_input_call(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input"


def _input_assigned_name(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if _is_input_call(node.value):
                return node.targets[0].id, node.value
    return None, None


def _rule_replace_title_like(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"title", "capitalize"} and len(node.args) == 0 and len(node.keywords) == 0:
                if isinstance(node.func.value, ast.Name):
                    base = node.func.value.id
                    new = f"{base}.swapcase()"
                    out.append(_replace_node(source, node, new))
    return out


def _rule_fix_guard_to_suffix_isupper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
            txt = ast.get_source_segment(source, node.test)
            if txt and any(".isupper()" in part for part in txt.split("or")) and any("[1:]" in part or "[1::]" in part for part in txt.split("or")):
                left_s, left_e = _span(source, node.test)
                new_test = txt.replace(".isupper()", ".upper() == " + txt.split("or")[-1].split(".isupper()")[0].strip(), 1) if False else None
    return []


def _rule_wrong_singleton_upper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            t = ast.get_source_segment(source, node.test)
            if t and "len(" in t and "== 1" in t and ".isupper()" in t:
                new_test = t.replace(".isupper()", ".islower()")
                out.append(_replace_node(source, node.test, new_test))
    return out


def _rule_isupper_or_suffix_isupper_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            t = ast.get_source_segment(source, node.test)
            if not t:
                continue
            if "isupper()" in t and "[1:]" in t and "swapcase()" in ast.get_source_segment(source, node) or False:
                pass
            if "word.isupper()" in t and "word[1:].isupper()" in t:
                new_t = t.replace("word[1:].isupper()", "word[1:].upper() == word[1:]")
                out.append(_replace_node(source, node.test, new_t))
            elif ".isupper()" in t and "[1:].isupper()" in t:
                new_t = t.replace("[1:].isupper()", "[1:].upper() == " + t.split("[1:].isupper()")[0].split()[-1].replace("(", "").replace(")", ""))
                out.append(_replace_node(source, node.test, new_t))
    return out


def _rule_swap_title_capitalize_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"title", "capitalize"}:
                txt = ast.get_source_segment(source, node)
                if txt and txt.endswith(".title()") or txt and txt.endswith(".capitalize()"):
                    out.append(_replace_node(source, node, txt.rsplit(".", 1)[0] + ".swapcase()"))
    return out


def _rule_input_then_capitalize_all(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    name, call = _input_assigned_name(tree)
    if name is None:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
            txt = ast.get_source_segment(source, node.value)
            if txt == f"{name}.capitalize()":
                out.append(_replace_node(source, node.value, f"{name}.swapcase()"))
    return out


def _rule_zero_branch_missing_else(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.orelse == []:
            body_text = ast.get_source_segment(source, node)
            if body_text and "print(" in body_text and "swapcase()" in body_text:
                continue
            if body_text and "print(" in body_text:
                # add an else by local splice only when the body is a single print and the guard is malformed
                test_text = ast.get_source_segment(source, node.test)
                if test_text and ("[1:].isupper()" in test_text or "[1:].lower()" in test_text or ".lower()" in test_text or ".title()" in test_text):
                    indent = " " * node.col_offset
                    stmt = ast.get_source_segment(source, node.body[0])
                    new = body_text + f"\n{indent}else:\n{indent}    print({ast.get_source_segment(source, node.body[0].value.args[0]) if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Call) and node.body[0].value.args else ast.get_source_segment(source, node.body[0]).split('print(',1)[1].rsplit(')',1)[0]})"
                    out.append(_replace_node(source, node, new))
                    break
    return out


def _rule_basic_misapplied_capitalize(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "capitalize":
                txt = ast.get_source_segment(source, node)
                if txt and ".capitalize()" in txt:
                    out.append(_replace_node(source, node, txt.replace(".capitalize()", ".swapcase()")))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="replace_title_capitalize_with_swapcase", apply=_rule_replace_title_like, symptoms=("wrong",)),
            Rule(name="singleton_upper_check_should_be_lower", apply=_rule_wrong_singleton_upper, symptoms=("wrong",)),
            Rule(name="suffix_isupper_guard_to_suffix_upper_equality", apply=_rule_isupper_or_suffix_isupper_to_swapcase, symptoms=("wrong",)),
            Rule(name="capitalize_call_should_be_swapcase", apply=_rule_swap_title_capitalize_to_swapcase, symptoms=("wrong",)),
            Rule(name="input_assigned_then_capitalize_should_swapcase", apply=_rule_input_then_capitalize_all, symptoms=("wrong",)),
            Rule(name="missing_else_for_print_branch", apply=_rule_zero_branch_missing_else, symptoms=("wrong",)),
            Rule(name="basic_misapplied_capitalize", apply=_rule_basic_misapplied_capitalize, symptoms=("wrong",)),
        ]