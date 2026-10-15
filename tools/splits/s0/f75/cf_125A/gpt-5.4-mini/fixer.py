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


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _fix_roundi(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.Eq) and _is_name(node.left, "roundI"):
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                out.append(_replace_node(source, node, f"{left} <= {right}"))
    return out


def _fix_int_div_print(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            new_args = []
            changed = False
            for arg in node.args:
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.FloorDiv) and isinstance(arg.left, ast.Name) and isinstance(arg.right, ast.Constant):
                    new_args.append(f"int({source[_span(source, arg)[0]:_span(source, arg)[1]]})")
                    changed = True
                else:
                    new_args.append(source[_span(source, arg)[0]:_span(source, arg)[1]])
            if changed:
                out.append(_replace_node(source, node, f"print({', '.join(new_args)})"))
    return out


def _fix_math_modf_round(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id == "cm":
                val = source[_span(source, node.value)[0]:_span(source, node.value)[1]]
                if "round(frctn * 12)" in val:
                    out.append(_replace_node(source, node.value, "int(round(frctn * 12))"))
    return out


def _fix_cm_rounding_to_floor_plus_remainder(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
            txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if "b%3==0" in txt and "b%3==1" in txt:
                out.append(_replace_node(source, node.test, "b%3 == 2"))
            if "b2==1" in txt and "b2==0" in txt:
                out.append(_replace_node(source, node.test, "b2 == 2"))
    return out


def _fix_feet_rounding_small(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.FloorDiv):
            txt = source[_span(source, node.value)[0]:_span(source, node.value)[1]]
            if "/36" in txt or "//36" in txt:
                out.append(_replace_node(source, node.value, "n // 36"))
    return out


def _fix_roundi_body(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "roundI":
            for stmt in node.body:
                if isinstance(stmt, ast.If):
                    test_txt = source[_span(source, stmt.test)[0]:_span(source, stmt.test)[1]]
                    if "roundI==1" in test_txt:
                        out.append(_replace_node(source, stmt.test, "inch <= 1"))
    return out


def _fix_finalinch_carry(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if test_txt.strip() == "finalinch == 12":
                out.append(_replace_node(source, node.test, "finalinch >= 12"))
    return out


def _fix_n_plus_two_to_plus_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
            right = source[_span(source, node.right)[0]:_span(source, node.right)[1]]
            if right == "2" and ("int(input())" in left or "input()" in left):
                out.append(_replace_node(source, node, f"{left}+1"))
    return out


def _fix_nplus2_over3_to_nplus1_over3(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if "+2" in txt and "/3" in txt:
                out.append(_replace_node(source, node, txt.replace("+2", "+1")))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="roundI_equals_one_to_le_one", apply=_fix_roundi, symptoms=("wrong",)),
            Rule(name="print_floordiv_as_int", apply=_fix_int_div_print, symptoms=("wrong",)),
            Rule(name="round_modf_piece_as_int", apply=_fix_math_modf_round, symptoms=("wrong",)),
            Rule(name="remainder_two_should_round_up", apply=_fix_cm_rounding_to_floor_plus_remainder, symptoms=("wrong",)),
            Rule(name="feet_division_by_36", apply=_fix_feet_rounding_small, symptoms=("wrong",)),
            Rule(name="roundi_body_uses_param", apply=_fix_roundi_body, symptoms=("wrong",)),
            Rule(name="carry_inches_at_12", apply=_fix_finalinch_carry, symptoms=("wrong",)),
            Rule(name="plus_two_instead_of_plus_one", apply=_fix_n_plus_two_to_plus_one, symptoms=("wrong",)),
            Rule(name="plus_two_div_three_to_plus_one_div_three", apply=_fix_nplus2_over3_to_nplus1_over3, symptoms=("wrong",)),
        ]