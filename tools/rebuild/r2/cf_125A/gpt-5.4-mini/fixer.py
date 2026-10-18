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


def _round_half_up_cm_to_inches(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 3:
                left = node.left
                ns, ne = _span(source, left)
                out.append(_splice(source, node, f"({source[ns:ne]} + 1)//3"))
    return out


def _fix_round_to_inches_then_feet(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "round":
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                    if isinstance(arg.right, ast.Constant) and arg.right.value == 3:
                        as_, ae = _span(source, arg.left)
                        new = f"round({source[as_:ae]}/3)"
                        out.append(_splice(source, node, new))
    return out


def _fix_mod36_to_n_mod3(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 36:
            out.append(_splice(source, node, "3"))
    return out


def _fix_wrong_div36_to_div3_then_quotrem(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and node.right.value == 36:
                l, r = node.left, node.right
                ls, le = _span(source, l)
                rs, re = _span(source, r)
                out.append(_splice(source, node, f"{source[ls:le]}//3"))
    return out


def _fix_cm_input_plus_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value == 2:
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.right)
                out.append(_splice(source, node, f"({source[ls:le]}+1)"))
    return out


def _fix_add_one_after_input(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value == 1:
                continue
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if isinstance(node.value, ast.Constant) and node.value.value == 1:
                continue
    return out


def _fix_float_rounding(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "int":
            if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Div):
                div = node.args[0]
                if isinstance(div.right, ast.Constant) and div.right.value == 36:
                    ls, le = _span(source, div.left)
                    rs, re = _span(source, div.right)
                    out.append(_splice(source, node, f"round({source[ls:le]}/3)"))
    return out


def _fix_print_tuple_spacing(source):
    try:
        ast.parse(source)
    except SyntaxError:
        return []
    if "print(" in source and "'  '" in source:
        return [source.replace("'  '", "' '")]
    return []


def _fix_int_cast_on_print(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            new_args = []
            changed = False
            for a in node.args:
                if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id == "int" and len(a.args) == 1:
                    s, e = _span(source, a.args[0])
                    new_args.append(source[s:e])
                    changed = True
                else:
                    s, e = _span(source, a)
                    new_args.append(source[s:e])
            if changed:
                out.append(_splice(source, node, "print(" + ", ".join(new_args) + ")"))
    return out


def _fix_bad_ceil_rem(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Constant):
                if node.comparators[0].value == 2:
                    s, e = _span(source, node)
                    out.append(_splice(source, node, source[s:e].replace("== 2", ">= 2")))
    return out


def _fix_foot_inch_order(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 2:
                a0s, a0e = _span(source, node.args[0])
                a1s, a1e = _span(source, node.args[1])
                if source[a0s:a0e].strip() == "a" and source[a1s:a1e].strip() == "b":
                    out.append(_splice(source, node, f"print({source[a1s:a1e]}, {source[a0s:a0e]})"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="round_cm_to_inches", apply=_round_half_up_cm_to_inches, symptoms=("wrong",)),
            Rule(name="round_call_to_inches", apply=_fix_round_to_inches_then_feet, symptoms=("wrong",)),
            Rule(name="fix_mod36_literal", apply=_fix_mod36_to_n_mod3, symptoms=("wrong",)),
            Rule(name="fix_floor_div_36", apply=_fix_wrong_div36_to_div3_then_quotrem, symptoms=("wrong",)),
            Rule(name="fix_plus_two_rounding", apply=_fix_cm_input_plus_one, symptoms=("wrong",)),
            Rule(name="fix_float_rounding", apply=_fix_float_rounding, symptoms=("wrong",)),
            Rule(name="fix_print_spacing", apply=_fix_print_tuple_spacing, symptoms=("wrong",)),
            Rule(name="cast_print_ints", apply=_fix_int_cast_on_print, symptoms=("wrong",)),
            Rule(name="ceil_when_remainder_two", apply=_fix_bad_ceil_rem, symptoms=("wrong",)),
            Rule(name="swap_output_order", apply=_fix_foot_inch_order, symptoms=("wrong",)),
        ]