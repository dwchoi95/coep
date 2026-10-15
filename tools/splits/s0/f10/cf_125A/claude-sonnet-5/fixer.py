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


def _is_const(node, value):
    return isinstance(node, ast.Constant) and node.value == value


def _rounding_offset_off_by_one(source):
    """Fix the classic (x + 2) // 3 rounding bug to (x + 1) // 3.

    The assignment rounds centimeters to the nearest inch, where an inch
    is 3 cm. The correct "round half up" transform for this scale is
    (x + 1) // 3; many buggy submissions instead use (x + 2) // 3 (a
    ceiling-style division), which rounds too aggressively.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv)):
            continue
        if not _is_const(node.right, 3):
            continue
        add = node.left
        if not (isinstance(add, ast.BinOp) and isinstance(add.op, ast.Add)):
            continue

        target_const = None
        if _is_const(add.right, 2):
            target_const = add.right
        elif _is_const(add.left, 2):
            target_const = add.left

        if target_const is None:
            continue

        new_src = _splice(source, target_const, "1")
        out.append(new_src)

    return out


def _ceil_div_call_off_by_one(source):
    """Fix the same rounding misconception expressed via -(-x // 3).

    Some submissions compute ceiling division of centimeters by 3 using
    -(-x // 3), which is mathematically a ceiling (same bug as +2 // 3).
    We rewrite the whole expression to the correct (x + 1) // 3 rounding
    form, keeping the inner operand untouched.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)):
            continue
        inner = node.operand
        if not (isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.FloorDiv)):
            continue
        if not _is_const(inner.right, 3):
            continue
        neg_left = inner.left
        if not (isinstance(neg_left, ast.UnaryOp) and isinstance(neg_left.op, ast.USub)):
            continue
        operand = neg_left.operand
        os_, oe_ = _span(source, operand)
        operand_text = source[os_:oe_]
        new_expr = f"({operand_text} + 1) // 3"
        out.append(_splice(source, node, new_expr))

    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="rounding_offset_off_by_one",
                apply=_rounding_offset_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="ceil_div_call_off_by_one",
                apply=_ceil_div_call_off_by_one,
                symptoms=("wrong",),
            ),
        ]