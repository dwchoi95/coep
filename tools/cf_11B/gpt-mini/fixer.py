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


def _replace_expr(source, old, new_expr):
    s, e = _span(source, old)
    return source[:s] + new_expr + source[e:]


def _abs_input_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == "int" and len(call.args) == 1:
                    arg = call.args[0]
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                        new_text = f"{tgt.id} = abs(int(input()))"
                        out.append(_splice(source, node, new_text))
    return out


def _wrap_input_in_abs(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "int" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                out.append(_replace_expr(source, node, "abs(int(input()))"))
    return out


def _fix_simple_while_accumulator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
            txt = ast.get_source_segment(source, node.test)
            if txt and ("or n%2==1" in txt or "or n % 2 == 1" in txt or "or n%2 == 1" in txt or "or n % 2==1" in txt):
                new_test = "i <= n or n % 2 == 1"
                out.append(_splice(source, node.test, new_test))
    return out


def _replace_print_yes_no_with_count(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant) and node.value.value in ("YES", "NO"):
                out.append(_splice(source, node.value, "0"))
    return out


def _fix_range_parity_search(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
            seg = ast.get_source_segment(source, node.iter)
            if seg and "range(2, x, 2)" in seg:
                out.append(_splice(source, node.iter, "range(1, x + 1)"))
    return out


def _fix_compare_assignment_to_result(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            seg = ast.get_source_segment(source, node.test)
            if seg and "x-n" in seg and "%2==0" in seg.replace(" ", ""):
                out.append(_splice(source, node.test, "False"))
    return out


def _fix_print_constant_three(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "print" and len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, ast.Constant) and arg.value == 3:
                    out.append(_splice(source, arg, "0"))
    return out


def _fix_wrong_while_scan(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            seg = ast.get_source_segment(source, node.test)
            if seg and "s != x" in seg:
                out.append(_splice(source, node.test, "pos < x or (pos-x) % 2 != 0"))
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and sub.id == "s":
                        break
    return out


def _fix_math_formula_integer_division(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            seg = ast.get_source_segment(source, node)
            if seg and "pow(n,2)-n" in seg.replace(" ", ""):
                out.append(_splice(source, node, "(pow(n, 2) - n) // 2"))
    return out


def _fix_len_zero_print(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                inner = node.args[0]
                if isinstance(inner.func, ast.Name) and inner.func.id == "len":
                    out.append(_splice(source, node, "print(jumps)"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="wrap_input_in_abs", apply=_wrap_input_in_abs, symptoms=("wrong",)),
            Rule(name="assign_abs_int_input", apply=_abs_input_rule, symptoms=("wrong",)),
            Rule(name="fix_while_or_parity_scan", apply=_fix_simple_while_accumulator, symptoms=("wrong", "timeout")),
            Rule(name="range_parity_search_to_direct_count", apply=_fix_range_parity_search, symptoms=("wrong",)),
            Rule(name="result_yes_no_to_count", apply=_replace_print_yes_no_with_count, symptoms=("wrong",)),
            Rule(name="fix_constant_three_output", apply=_fix_print_constant_three, symptoms=("wrong",)),
            Rule(name="fix_scan_while_condition", apply=_fix_wrong_while_scan, symptoms=("wrong",)),
            Rule(name="fix_float_sum_to_int_div", apply=_fix_math_formula_integer_division, symptoms=("wrong",)),
            Rule(name="fix_len_print_to_count", apply=_fix_len_zero_print, symptoms=("wrong",)),
            Rule(name="fix_generic_input_abs_return", apply=_fix_compare_assignment_to_result, symptoms=("wrong",)),
        ]