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


def _replace_node(source, target, replacement):
    s1, e1 = _span(source, target)
    s2, e2 = _span(source, replacement)
    return source[:s1] + source[s2:e2] + source[e1:]


def _float_to_int_print(source):
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
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                    left = arg.left
                    if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "str":
                        inner = left.args[0] if left.args else None
                        if inner is not None and not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "int"):
                            repl = "str(int(" + source[_span(source, inner)[0]:_span(source, inner)[1]] + "))"
                            new_args.append(repl)
                            changed = True
                            continue
                new_args.append(source[_span(source, arg)[0]:_span(source, arg)[1]])
            if changed:
                out.append(_splice(source, node, "print(" + ", ".join(new_args) + ")"))
    return out


def _mod_division_in_print(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 2:
                a1, a2 = node.args
                txt1 = source[_span(source, a1)[0]:_span(source, a1)[1]]
                txt2 = source[_span(source, a2)[0]:_span(source, a2)[1]]
                if "//" in txt1 and "%" in txt2:
                    out.append(_splice(source, node, "print(int(" + txt1 + "), int(" + txt2 + "))"))
    return out


def _fix_floor_to_round_in_inches(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.FloorDiv):
            rhs = node.value
            if isinstance(rhs.left, ast.Name) and isinstance(rhs.right, ast.Constant) and rhs.right.value == 3:
                target_text = source[_span(source, rhs)[0]:_span(source, rhs)[1]]
                if "%" not in target_text:
                    out.append(_splice(source, rhs, "(" + source[_span(source, rhs.left)[0]:_span(source, rhs.left)[1]] + " + 1) // 3"))
    return out


def _fix_add_rounding_threshold(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            cmp = node.test
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.GtE):
                left = source[_span(source, cmp.left)[0]:_span(source, cmp.left)[1]]
                right = source[_span(source, cmp.comparators[0])[0]:_span(source, cmp.comparators[0])[1]]
                if right == "2" and "%" in left:
                    out.append(_splice(source, cmp, left + " >= 2"))
    return out


def _fix_div_mod_print_pair(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 2:
                a1, a2 = node.args
                t1 = source[_span(source, a1)[0]:_span(source, a1)[1]]
                t2 = source[_span(source, a2)[0]:_span(source, a2)[1]]
                if t1.endswith("//36") and t2.startswith("(n%36)//3"):
                    out.append(_splice(source, node, "print(" + t1.replace("//36", "//12") + ", " + t2 + ")"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="cast_printed_division_results_to_int", apply=_float_to_int_print, symptoms=("wrong", "err:TypeError")),
            Rule(name="wrap_printed_quotients_with_int", apply=_mod_division_in_print, symptoms=("wrong", "err:TypeError")),
            Rule(name="use_rounded_inches_not_floor_division", apply=_fix_floor_to_round_in_inches, symptoms=("wrong",)),
            Rule(name="round_up_when_remainder_at_least_two", apply=_fix_add_rounding_threshold, symptoms=("wrong",)),
            Rule(name="fix_feet_from_total_inches_in_output", apply=_fix_div_mod_print_pair, symptoms=("wrong",)),
        ]