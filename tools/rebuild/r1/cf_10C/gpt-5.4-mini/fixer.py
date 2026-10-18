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


def _replace_node(source, old_node, new_node_src):
    return _splice(source, old_node, new_node_src)


def _int_input_to_n(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "input":
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    out.append(_replace_node(source, call, "int(input())"))
    return out


def _range_start_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 1 and not node.keywords:
                arg = node.args[0]
                out.append(_replace_node(source, node, f"range(1, {_segment(source, arg)} + 1)"))
    return out


def _segment(source, node):
    s, e = _span(source, node)
    return source[s:e]


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
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re]))
    return out


def _neq_to_eq(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
    return out


def _len_str_loop_to_digit_sum(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
            cmp = node.test
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.NotEq):
                if isinstance(cmp.left, ast.Call) and isinstance(cmp.left.func, ast.Name) and cmp.left.func.id == "len":
                    args = cmp.left.args
                    if len(args) == 1 and isinstance(args[0], ast.Call) and isinstance(args[0].func, ast.Name) and args[0].func.id == "str":
                        s, e = _span(source, cmp)
                        new_test = source[s:e].replace("len(str(", "len(str(")
                        out.append(_splice(source, node.test, f"False"))
    return out


def _input_str_to_int(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str":
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                    out.append(_replace_node(source, node, "int(input())"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="input_needs_int", apply=_int_input_to_n, symptoms=("err:TypeError", "wrong")),
            Rule(name="range_single_arg_to_inclusive_range", apply=_range_start_one, symptoms=("wrong",)),
            Rule(name="strict_lt_should_be_lte", apply=_lt_to_le, symptoms=("wrong",)),
            Rule(name="not_equal_should_be_equal", apply=_neq_to_eq, symptoms=("wrong",)),
            Rule(name="input_used_as_string_should_be_int", apply=_input_str_to_int, symptoms=("err:TypeError", "wrong")),
        ]