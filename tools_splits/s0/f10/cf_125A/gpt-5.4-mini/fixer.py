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


def _replace_binop_op(source, op_type, new_op_text):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, op_type):
            ls, le = _span(source, node.left)
            rs, re = _span(source, node.right)
            new_expr = source[ls:le] + f" {new_op_text} " + source[rs:re]
            out.append(_splice(source, node, new_expr))
    return out


def _replace_compare_op(source, old_type, new_op_text):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], old_type):
            ls, le = _span(source, node.left)
            rs, re = _span(source, node.comparators[0])
            new_expr = source[ls:le] + f" {new_op_text} " + source[rs:re]
            out.append(_splice(source, node, new_expr))
    return out


def _fix_floor_div_to_add_one_then_div(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add):
                # only a small local rewrite: (x + k) // m  ->  (x + k + m - 1) // m
                left = node.left
                if isinstance(left.right, ast.Constant) and isinstance(left.right.value, int) and isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):
                    ls, le = _span(source, left.left)
                    rs1, re1 = _span(source, left.right)
                    rs2, re2 = _span(source, node.right)
                    new_left = source[ls:le] + " + " + source[rs1:re1] + " + " + source[rs2:re2] + " - 1"
                    new_expr = f"({new_left}) // " + source[rs2:re2]
                    out.append(_splice(source, node, new_expr))
    return out


def _fix_rounding_division_to_nearest(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add) and isinstance(node.left.right, ast.Constant):
                # Replace (n + c) // d with (n + c // 2) // d only when it looks like a rounding-to-nearest attempt.
                left = node.left
                if isinstance(left.right.value, int) and isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):
                    c = left.right.value
                    d = node.right.value
                    if d == 3 and c == 2:
                        ls, le = _span(source, left.left)
                        rs1, re1 = _span(source, left.right)
                        rs2, re2 = _span(source, node.right)
                        new_left = source[ls:le] + " + 1"
                        new_expr = f"({new_left}) // {source[rs2:re2]}"
                        out.append(_splice(source, node, new_expr))
    return out


def _fix_mod_after_div(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.FloorDiv):
                # turn (x // d) % d2 into (x % (d*d2)) // d
                div = node.left
                if isinstance(div.right, ast.Constant) and isinstance(node.right, ast.Constant):
                    if isinstance(div.right.value, int) and isinstance(node.right.value, int):
                        ls, le = _span(source, div.left)
                        rs1, re1 = _span(source, div.right)
                        rs2, re2 = _span(source, node.right)
                        new_expr = "(" + source[ls:le] + f" % ({source[rs1:re1]} * {source[rs2:re2]})) // {source[rs1:re1]}"
                        out.append(_splice(source, node, new_expr))
    return out


def _fix_len_to_feet_inches(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, int) and node.right.value == 12:
                # For the specific assignment, feet should be based on 36 cm per foot.
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.right)
                new_expr = source[ls:le] + " // 36"
                out.append(_splice(source, node, new_expr))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="convert_cm_to_inches_using_3cm_per_inch",
                apply=_fix_floor_div_to_add_one_then_div,
                symptoms=("wrong",),
            ),
            Rule(
                name="round_to_nearest_inch_before_feet_split",
                apply=_fix_rounding_division_to_nearest,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_feet_inches_split_after_feet_division",
                apply=_fix_mod_after_div,
                symptoms=("wrong",),
            ),
            Rule(
                name="feet_should_use_36_cm_per_foot",
                apply=_fix_len_to_feet_inches,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=lambda source: _replace_compare_op(source, ast.Lt, "<="),
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_should_be_gte",
                apply=lambda source: _replace_compare_op(source, ast.Gt, ">="),
                symptoms=("wrong",),
            ),
            Rule(
                name="floor_div_should_be_true_div_when_followed_by_int_cast",
                apply=lambda source: _replace_binop_op(source, ast.FloorDiv, "/"),
                symptoms=("wrong",),
            ),
        ]