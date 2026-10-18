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


def _num3_to_round_inches(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 3:
                out.append(_replace_node(source, node, f"round({source[_span(source, node.left)[0]:_span(source, node.left)[1]]}/3)"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "round":
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                    if isinstance(arg.right, ast.Constant) and arg.right.value == 3:
                        out.append(_replace_node(source, node, f"round({source[_span(source, arg.left)[0]:_span(source, arg.left)[1]]}/3)"))
    return out


def _round_rem_to_div3_plus1(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value == 2:
                if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name) and node.left.func.id == "int":
                    arg = node.left.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                        if isinstance(arg.right, ast.Constant) and arg.right.value == 3:
                            out.append(_replace_node(source, node, f"(int({source[_span(source, arg.left)[0]:_span(source, arg.left)[1]]}/3)+1)//1"))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 3:
                out.append(_replace_node(source, node, f"({source[_span(source, node.left)[0]:_span(source, node.left)[1]]}+1)//3"))
    return out


def _fix_cm_prompt_input(source):
    if 'input("Enter length in centimeter : ")' not in source:
        return []
    return [source.replace('input("Enter length in centimeter : ")', 'input()')]


def _fix_mod26_to_36(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            if isinstance(node.right, ast.Constant) and node.right.value == 26:
                out.append(_replace_node(source, node.right, "36"))
    return out


def _fix_round_to_floor_and_carry(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "round":
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div) and isinstance(arg.right, ast.Constant) and arg.right.value == 3:
                    out.append(_replace_node(source, node, f"({source[_span(source, arg.left)[0]:_span(source, arg.left)[1]]} + 1) // 3"))
    return out


def _fix_float_rounding_to_integer_inches(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "int":
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                    if isinstance(arg.right, ast.Constant) and arg.right.value == 3:
                        out.append(_replace_node(source, node, f"round({_source_expr(source, arg.left)}/3)"))
    return out


def _source_expr(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _fix_print_concat_to_two_ints(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                    pass
    return out


def _fix_add_one_before_div36(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value == 2:
                if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Call):
                    pass
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 36:
                parent_text = _source_expr(source, node)
                out.append(_replace_node(source, node, f"({parent_text}+1)//36"))
    return out


def _fix_inch_to_feet_chain(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.FloorDiv):
                if isinstance(node.value.right, ast.Constant) and node.value.right.value == 12:
                    out.append(source)
    return out


def _fix_common_rounding(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 36:
                expr = _source_expr(source, node.left)
                out.append(_replace_node(source, node, f"({expr}+1)//36"))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Constant) and node.right.value == 36:
                expr = _source_expr(source, node.left)
                out.append(_replace_node(source, node, f"{expr}//36"))
    return out


def _fix_invalid_ceil_on_inches(source):
    if "math.ceil" not in source:
        return []
    return [source.replace("int(math.ceil(f/3))", "(f + 1)//3").replace("math.ceil(f/3)", "(f + 1)//3")]


class Fixer:
    def rules(self):
        return [
            Rule(name="round_cm_to_inches", apply=_num3_to_round_inches, symptoms=("wrong",)),
            Rule(name="carry_from_remainder_on_three", apply=_round_rem_to_div3_plus1, symptoms=("wrong",)),
            Rule(name="prompted_input_to_plain_input", apply=_fix_cm_prompt_input, symptoms=("wrong", "err:ValueError")),
            Rule(name="mod26_typo_to_mod36", apply=_fix_mod26_to_36, symptoms=("wrong",)),
            Rule(name="round_half_up_inches", apply=_fix_round_to_floor_and_carry, symptoms=("wrong",)),
            Rule(name="fix_float_rounding_inches", apply=_fix_float_rounding_to_integer_inches, symptoms=("wrong",)),
            Rule(name="add_one_before_dividing_by_36", apply=_fix_add_one_before_div36, symptoms=("wrong",)),
            Rule(name="ceil_used_for_inches", apply=_fix_invalid_ceil_on_inches, symptoms=("wrong",)),
            Rule(name="generic_36_division_rounding", apply=_fix_common_rounding, symptoms=("wrong",)),
            Rule(name="fix_printed_inches_expression", apply=_fix_print_concat_to_two_ints, symptoms=("wrong",)),
        ]