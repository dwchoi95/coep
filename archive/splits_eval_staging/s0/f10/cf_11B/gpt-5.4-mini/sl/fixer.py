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


def _replace_node(source, target, new_node):
    return _splice(source, target, ast.get_source_segment(source, new_node))


def _abs_to_no_abs(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "abs" and len(node.args) == 1 and not node.keywords:
            arg = node.args[0]
            out.append(_splice(source, node, ast.get_source_segment(source, arg)))
    return out


def _ceil_formula_to_linear(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ceil" and len(node.args) == 1:
            text = ast.get_source_segment(source, node.args[0])
            if text and "8 *" in text and "** 0.5" in text:
                inner = node.args[0]
                out.append(_splice(source, node, ast.get_source_segment(source, inner)))
    return out


def _minus_one_in_triangle_to_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub) and isinstance(node.right, ast.Constant) and node.right.value == 1:
            left = node.left
            if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Div):
                out.append(_splice(source, node, ast.get_source_segment(source, left)))
    return out


def _wrong_parity_loop_to_target_formula(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            txt = ast.get_source_segment(source, node.test)
            if txt and "product % 2 == n % 2" in txt:
                repl = "((i * (i + 1) // 2) - n) % 2 == 0"
                out.append(_splice(source, node.test, repl))
    return out


def _incremental_simulation_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            txt = ast.get_source_segment(source, node.test)
            if txt and "posicion!=x" in txt.replace(" ", ""):
                new_test = "posicion < x or posicion > x"
                out.append(_splice(source, node.test, new_test))
    return out


def _n_to_abs_input(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "int":
                seg = ast.get_source_segment(source, val)
                if seg == "int(input())":
                    out.append(_splice(source, val, "abs(int(input()))"))
    return out


def _range_like_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            txt = ast.get_source_segment(source, node.test)
            if txt and "<=n" in txt.replace(" ", ""):
                out.append(_splice(source, node.test, "current + i < n"))
    return out


def _jumps_parity_check_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            txt = ast.get_source_segment(source, node.test)
            if txt and "product >= n and product % 2 == n % 2" in txt:
                out.append(_splice(source, node.test, "product >= abs(n) and (product - abs(n)) % 2 == 0"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="remove_abs_when_problem_keeps_sign", apply=_abs_to_no_abs, symptoms=("wrong",)),
            Rule(name="replace_ceil_quadratic_with_direct_total", apply=_ceil_formula_to_linear, symptoms=("wrong",)),
            Rule(name="drop_minus_one_from_triangle_formula", apply=_minus_one_in_triangle_to_zero, symptoms=("wrong",)),
            Rule(name="fix_parity_check_in_iterative_solution", apply=_wrong_parity_loop_to_target_formula, symptoms=("wrong",)),
            Rule(name="fix_simulation_termination_and_sign", apply=_incremental_simulation_fix, symptoms=("wrong", "timeout")),
            Rule(name="wrap_input_with_abs_for_symmetric_problem", apply=_n_to_abs_input, symptoms=("wrong",)),
            Rule(name="fix_while_bound_off_by_one", apply=_range_like_off_by_one, symptoms=("wrong", "timeout")),
            Rule(name="use_abs_in_parity_jump_condition", apply=_jumps_parity_check_fix, symptoms=("wrong",)),
        ]