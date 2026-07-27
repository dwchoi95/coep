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


def _replace_constant(source, node, new_value_text):
    if isinstance(node, ast.Constant):
        return _splice(source, node, new_value_text)
    return None


def _fix_plus_two_div_three(source):
    """Change the common over-rounding +2 to the correct +1."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value == 2:
                new_src = _splice(source, node.right, "1")
                out.append(new_src)
    return out


def _fix_round_half_up_to_floor_plus_one(source):
    """Fix round(rem/3) style integer rounding by adding one before //3."""
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
                    left = div.left
                    ls, le = _span(source, left)
                    rs, re = _span(source, div.right)
                    new_text = f"({source[ls:le]} + 1) // {source[rs:re]}"
                    out.append(_splice(source, node, new_text))
    return out


def _fix_missing_carry_at_12(source):
    """Insert carry handling when inches round to exactly 12."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            for i in range(len(body) - 1):
                a, b = body[i], body[i + 1]
                if isinstance(a, ast.Assign) and isinstance(b, ast.Assign):
                    if len(a.targets) == 1 and len(b.targets) == 1:
                        ta, tb = a.targets[0], b.targets[0]
                        if isinstance(ta, ast.Name) and isinstance(tb, ast.Name):
                            if ta.id in {"ic", "inch", "inches", "b"} and tb.id in {"ft", "feet", "a"}:
                                if isinstance(a.value, ast.Call) and isinstance(a.value.func, ast.Name) and a.value.func.id == "round":
                                    if len(a.value.args) == 1 and isinstance(a.value.args[0], ast.BinOp) and isinstance(a.value.args[0].op, ast.Div):
                                        div = a.value.args[0]
                                        if isinstance(div.right, ast.Constant) and div.right.value == 3:
                                            indent = " " * a.col_offset
                                            insert = (
                                                f"\n{indent}if {ta.id} == 12:\n"
                                                f"{indent}    {tb.id} += 1\n"
                                                f"{indent}    {ta.id} = 0"
                                            )
                                            out.append(_splice(source, b, source[_span(source, b)[0]:_span(source, b)[1]] + insert))
                                            return out
    return out


def _fix_floor_division_then_round_up_remainder(source):
    """Repair nearby computations that use 36-based feet and rounded remainder inches."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.FloorDiv):
            if isinstance(node.value.right, ast.Constant) and node.value.right.value == 36:
                # look for a later round(rem/3) in same function
                parent_func = None
                for p in ast.walk(tree):
                    if isinstance(p, ast.FunctionDef) and node in p.body:
                        parent_func = p
                        break
                if parent_func is None:
                    continue
                for n2 in ast.walk(parent_func):
                    if isinstance(n2, ast.Call) and isinstance(n2.func, ast.Name) and n2.func.id == "round":
                        if len(n2.args) == 1 and isinstance(n2.args[0], ast.BinOp) and isinstance(n2.args[0].op, ast.Div):
                            div = n2.args[0]
                            if isinstance(div.right, ast.Constant) and div.right.value == 3:
                                left = div.left
                                ls, le = _span(source, left)
                                rs, re = _span(source, div.right)
                                new_text = f"({source[ls:le]} + 1) // {source[rs:re]}"
                                out.append(_splice(source, n2, new_text))
                                return out
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="plus_two_to_plus_one_before_div3",
                apply=_fix_plus_two_div_three,
                symptoms=("wrong",),
            ),
            Rule(
                name="round_div3_to_floor_plus_one",
                apply=_fix_round_half_up_to_floor_plus_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_carry_when_inch_equals_12",
                apply=_fix_missing_carry_at_12,
                symptoms=("wrong",),
            ),
            Rule(
                name="feet_36_and_round_remainder_to_correct_rounding",
                apply=_fix_floor_division_then_round_up_remainder,
                symptoms=("wrong",),
            ),
        ]