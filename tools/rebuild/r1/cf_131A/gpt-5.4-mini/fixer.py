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


def _walk_parents(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _replace_node(source, old_node, new_text):
    return _splice(source, old_node, new_text)


def _is_input_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "input"
    )


def _rule_fix_isupper_or_rest_isupper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
            vals = node.test.values
            if len(vals) == 2:
                a, b = vals
                if (
                    isinstance(a, ast.Call)
                    and isinstance(a.func, ast.Attribute)
                    and a.func.attr == "isupper"
                    and isinstance(b, ast.Call)
                    and isinstance(b.func, ast.Attribute)
                    and b.func.attr == "isupper"
                    and isinstance(b.func.value, ast.Subscript)
                ):
                    old = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                    new = old.replace(" or ", " and ", 1)
                    out.append(_replace_node(source, node.test, new))
    return out


def _rule_fix_always_truthy_upper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_src = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if ".upper()" in test_src and " or " in test_src and ".isupper" not in test_src:
                new = test_src.replace(".upper()", ".isupper()")
                out.append(_replace_node(source, node.test, new))
    return out


def _rule_fix_len1_isupper_to_islower(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And) and len(test.values) == 2:
                left, right = test.values
                if isinstance(left, ast.Compare) and isinstance(right, ast.Call):
                    ls = source[_span(source, left)[0]:_span(source, left)[1]]
                    rs = source[_span(source, right)[0]:_span(source, right)[1]]
                    if ".isupper()" in ls and ".islower()" not in ls:
                        new = ls.replace(".isupper()", ".islower()")
                        out.append(_replace_node(source, left, new))
                    if ".isupper()" in rs and ".islower()" not in rs:
                        new = rs.replace(".isupper()", ".islower()")
                        out.append(_replace_node(source, right, new))
    return out


def _rule_fix_capitalize_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"capitalize", "title"}:
            base = node.func.value
            if isinstance(base, ast.Name):
                old = source[_span(source, node)[0]:_span(source, node)[1]]
                new = old.replace(node.func.attr, "swapcase")
                out.append(_replace_node(source, node, new))
    return out


def _rule_fix_uppercase_method(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "uppercase":
            out.append(_replace_node(source, node, source[_span(source, node.value)[0]:_span(source, node.value)[1]] + ".swapcase"))
    return out


def _rule_add_len1_to_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_src = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if ("word[1:].isupper()" in test_src or "s[1:].isupper()" in test_src or "n[1:].isupper()" in test_src) and "len(" not in test_src:
                new = test_src.replace(" or ", " or len(" + test_src.split("[", 1)[0].strip() + ") == 1 or ", 1) if " or " in test_src else test_src
                if "len(" not in new:
                    continue
                out.append(_replace_node(source, node.test, new))
    return out


def _rule_fix_lower_to_swapcase_for_capslock(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_src = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if ".islower()" in test_src and ".isupper()" in test_src:
                continue
            if ".isupper()" in test_src and ".islower()" in test_src:
                continue
    return out


def _rule_fix_swapcase_on_only_rest_upper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_src = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if "word[1:].isupper()" in test_src or "s[1:].isupper()" in test_src or "n[1:].isupper()" in test_src:
                if "swapcase()" in source[_span(source, node)[0]:_span(source, node)[1]]:
                    continue
                body_start = _span(source, node.body[0])[0]
                body_end = _span(source, node.body[0])[1]
                stmt = source[body_start:body_end]
                if ".capitalize()" in stmt or ".title()" in stmt or ".lower()" in stmt:
                    new_stmt = stmt.replace(".capitalize()", ".swapcase()").replace(".title()", ".swapcase()").replace(".lower()", ".swapcase()")
                    out.append(source[:body_start] + new_stmt + source[body_end:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="and_instead_of_or_for_capslock_guard",
                apply=_rule_fix_isupper_or_rest_isupper,
                symptoms=("wrong",),
            ),
            Rule(
                name="truthy_upper_call",
                apply=_rule_fix_always_truthy_upper,
                symptoms=("wrong",),
            ),
            Rule(
                name="single_char_lower_guard",
                apply=_rule_fix_len1_isupper_to_islower,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_or_title_to_swapcase",
                apply=_rule_fix_capitalize_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_swapcase_method_name",
                apply=_rule_fix_uppercase_method,
                symptoms=("err:AttributeError", "wrong"),
            ),
            Rule(
                name="add_single_char_to_caps_condition",
                apply=_rule_add_len1_to_condition,
                symptoms=("wrong",),
            ),
            Rule(
                name="replace_rest_upper_capitalize_with_swapcase",
                apply=_rule_fix_swapcase_on_only_rest_upper,
                symptoms=("wrong",),
            ),
        ]