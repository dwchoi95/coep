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


def _find_input_assign_name(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name):
                val = node.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "input":
                    return t.id
    return None


def _make_stmt(source, node, new_text):
    return _splice(source, node, new_text)


def _rule_title_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "title":
            out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".swapcase()"))
    return out


def _rule_capitalize_to_swapcase_on_capslock_branch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "capitalize":
            out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".swapcase()"))
    return out


def _rule_upper_to_lower_on_all_upper_branch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "upper":
            out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".lower()"))
    return out


def _rule_isupper_call_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "isupper" and not isinstance(getattr(node, "ctx", None), ast.Store):
            out.append(_splice(source, node, source[_span(source, node.value)[0]:_span(source, node.value)[1]] + ".isupper()"))
    return out


def _rule_len_eq1_to_len_ge1(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name) and node.left.func.id == "len":
                if len(node.left.args) == 1 and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 1:
                    left_text = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    right_text = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                    out.append(_splice(source, node, left_text + " >= " + right_text))
    return out


def _rule_fix_or_always_true(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for v in node.values:
                if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "upper":
                    out.append(_splice(source, v, source[_span(source, v.func.value)[0]:_span(source, v.func.value)[1]] + ".isupper()"))
    return out


def _rule_replace_lower_check_with_upper_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "islower":
            out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".isupper()"))
    return out


def _rule_replace_title_result_with_swapcase_branch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                if isinstance(test.left, ast.Subscript) and isinstance(test.comparators[0], ast.Call):
                    pass
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
                for v in test.values:
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "upper":
                        out.append(_splice(source, v, source[_span(source, v.func.value)[0]:_span(source, v.func.value)[1]] + ".isupper()"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="title_to_swapcase", apply=_rule_title_to_swapcase, symptoms=("wrong",)),
            Rule(name="capitalize_to_swapcase", apply=_rule_capitalize_to_swapcase_on_capslock_branch, symptoms=("wrong",)),
            Rule(name="upper_to_lower_on_all_upper", apply=_rule_upper_to_lower_on_all_upper_branch, symptoms=("wrong",)),
            Rule(name="missing_isupper_call", apply=_rule_isupper_call_fix, symptoms=("wrong", "err:AttributeError")),
            Rule(name="len_eq1_to_len_ge1", apply=_rule_len_eq1_to_len_ge1, symptoms=("wrong",)),
            Rule(name="or_always_true_upper_to_isupper", apply=_rule_fix_or_always_true, symptoms=("wrong",)),
            Rule(name="islower_mischeck_to_isupper", apply=_rule_replace_lower_check_with_upper_check, symptoms=("wrong",)),
            Rule(name="title_branch_misrepair", apply=_rule_replace_title_result_with_swapcase_branch, symptoms=("wrong",)),
        ]