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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


def _rounding_correction(source):
    """Fix ceil-style rounding from +2 to +1 when converting cm to inches."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add):
                add = node.left
                if isinstance(add.right, ast.Constant) and add.right.value == 2:
                    new_add = _replace_node(source, add.right, "1")
                    out.append(_replace_node(new_add, add, new_add[_span(new_add, add)[0]:_span(new_add, add)[1]]))
    return out


def _rounding_correction_v2(source):
    """Fix +2//3 rounding in a parenthesized conversion expression."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add):
                add = node.left
                if isinstance(add.right, ast.Constant) and add.right.value == 2:
                    out.append(_splice(source, add.right, "1"))
    return out


def _round_builtin_to_guarded(source):
    """Guard rounded inches so exactly 12 inches becomes an extra foot."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "round":
                # Find enclosing function/block? Use local statement-level insertion only when simple target name exists.
                if isinstance(node.targets[0], ast.Name):
                    target = node.targets[0].id
                    assign_text = source[_span(source, node)[0]:_span(source, node)[1]]
                    extra = f"\n    if {target} == 12:\n        ft +=1 \n        {target} = 0"
                    out.append(assign_text + extra)
    return out


def _fix_ft36_to_ft12(source):
    """Convert feet computation from centimeters directly by 36 instead of inches by 12."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 36:
            out.append(_splice(source, node, "12"))
    return out


def _fix_off_by_one_in_addition(source):
    """Correct +2 to +1 in simple arithmetic conversion expressions."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 2:
            parent_text = source[_span(source, node)[0]:_span(source, node)[1]]
            if parent_text == "2":
                out.append(_splice(source, node, "1"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="rounding_plus_two_to_plus_one",
                apply=_rounding_correction_v2,
                symptoms=("wrong",),
            ),
            Rule(
                name="round_builtin_needs_overflow_guard",
                apply=_round_builtin_to_guarded,
                symptoms=("wrong",),
            ),
            Rule(
                name="cm_to_inches_using_36_should_use_12_for_feet",
                apply=_fix_ft36_to_ft12,
                symptoms=("wrong",),
            ),
            Rule(
                name="off_by_one_addition_constant",
                apply=_fix_off_by_one_in_addition,
                symptoms=("wrong",),
            ),
        ]