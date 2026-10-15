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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


def _rounding_and_split_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 36:
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.right)
                new_text = f"{source[ls:le]} // 3"
                out.append(_splice(source, node, new_text))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            if isinstance(node.right, ast.Constant) and node.right.value == 36:
                ls, le = _span(source, node.left)
                new_text = f"{source[ls:le]} % 3"
                out.append(_splice(source, node, new_text))
    return out


def _ceilish_plus_one_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 3:
                parent = None
                ls, le = _span(source, node.left)
                new_text = f"({source[ls:le]} + 1) // 3"
                out.append(_splice(source, node, new_text))
    return out


def _float_round_to_inch_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "round":
            if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Div):
                div = node.args[0]
                if isinstance(div.right, ast.Constant) and div.right.value == 3:
                    ls, le = _span(source, div.left)
                    new_text = f"round({source[ls:le]}/3)"
                    out.append(_splice(source, node, new_text))
    return out


def _fix_36_to_3_chain_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 12:
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.right)
                new_text = f"{source[ls:le]} // 12"
                out.append(_splice(source, node, new_text))
    return out


def _comparison_2_to_1_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 2:
                lefts, le = _span(source, node.left)
                rs, re = _span(source, node.comparators[0])
                new_text = f"{source[lefts:le]} == 1"
                out.append(_splice(source, node, new_text))
    return out


def _fix_mod_zero_one_two_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                if isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value == 2:
                    ls, le = _span(source, test.left)
                    new_test = f"{source[ls:le]} == 2"
                    out.append(_splice(source, test, new_test))
    return out


def _fix_increment_when_rem_two_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                cmp = node.test
                if isinstance(cmp.comparators[0], ast.Constant) and cmp.comparators[0].value == 2:
                    body = node.body[0] if node.body else None
                    if isinstance(body, ast.AugAssign) and isinstance(body.op, ast.Add):
                        target_s, target_e = _span(source, body.target)
                        new_stmt = f"{source[target_s:target_e]} += 1"
                        out.append(_splice(source, body, new_stmt))
    return out


def _fix_print_two_values_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Add):
                pass
    return out


def _fix_return_single_value_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 1 and isinstance(node.args[0], ast.JoinedStr):
                continue
    return out


def _fix_round_to_split_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "round":
            if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp):
                div = node.args[0]
                if isinstance(div.op, ast.Div) and isinstance(div.right, ast.Constant) and div.right.value == 3:
                    ls, le = _span(source, div.left)
                    new_text = f"round({source[ls:le]}/3)"
                    out.append(_splice(source, node, new_text))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="use_inches_then_split_into_feet", apply=_rounding_and_split_rule, symptoms=("wrong",)),
            Rule(name="ceil_cm_to_inches_by_add_one", apply=_ceilish_plus_one_rule, symptoms=("wrong",)),
            Rule(name="round_cm_to_inches_then_split", apply=_float_round_to_inch_rule, symptoms=("wrong",)),
            Rule(name="replace_36_based_split_with_3_and_12_split", apply=_fix_36_to_3_chain_rule, symptoms=("wrong",)),
            Rule(name="fix_rounding_threshold_to_two", apply=_comparison_2_to_1_rule, symptoms=("wrong",)),
            Rule(name="fix_rem_equals_two_branch", apply=_fix_mod_zero_one_two_rule, symptoms=("wrong",)),
            Rule(name="increment_on_remainder_two", apply=_fix_increment_when_rem_two_rule, symptoms=("wrong",)),
            Rule(name="round_then_split_generic", apply=_fix_round_to_split_rule, symptoms=("wrong",)),
        ]