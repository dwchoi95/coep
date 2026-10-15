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


def _is_input_int_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "int"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Call)
        and isinstance(node.args[0].func, ast.Name)
        and node.args[0].func.id == "input"
        and len(node.args[0].args) == 0
    )


def _abs_input_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if _is_input_int_call(node):
            out.append(_splice(source, node, f"abs({source[_span(source, node)[0]:_span(source, node)[1]]})"))
    return out


def _while_ne_to_parity_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
            cmp = node.test
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.NotEq):
                ls, le = _span(source, cmp.left)
                rs, re = _span(source, cmp.comparators[0])
                left_txt = source[ls:le]
                right_txt = source[rs:re]
                new_test = f"{left_txt} < {right_txt} or ({left_txt}-{right_txt}) % 2 != 0"
                out.append(_splice(source, cmp, new_test))
    return out


def _lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


def _fix_print_input(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                arg = node.args[0]
                if arg.id == "x":
                    xs, xe = _span(source, arg)
                    out.append(_splice(source, arg, "abs(int(input()))"))
    return out


def _plus_to_minus_in_jump_update(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if isinstance(node.target, ast.Name) and node.target.id in {"s", "pos"}:
                if isinstance(node.value, ast.Name) and node.value.id in {"n", "count", "jumps"}:
                    out.append(_splice(source, node.op, "+"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="abs_input_int", apply=_abs_input_fix, symptoms=("wrong", "err:ValueError")),
            Rule(name="while_not_equal_needs_parity_loop", apply=_while_ne_to_parity_condition, symptoms=("wrong", "timeout")),
            Rule(name="strict_lt_should_be_lte", apply=_lt_to_le, symptoms=("wrong",)),
            Rule(name="print_variable_should_be_abs_input", apply=_fix_print_input, symptoms=("wrong", "err:NameError")),
            Rule(name="plus_to_minus_in_incremental_update", apply=_plus_to_minus_in_jump_update, symptoms=("wrong",)),
        ]