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


def _int_input_to_int_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            parent = node
            while hasattr(parent, "parent"):
                parent = parent.parent
            out.append(source[: _span(source, node)[0]] + "int(" + source[_span(source, node)[0] : _span(source, node)[1]] + ")" + source[_span(source, node)[1] :])
    return out


def _attach_parents(tree):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent


def _fix_input_to_int(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _attach_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            out.append(_splice(source, node, "int(input())"))
    return out


def _range_start_1_to_0(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) >= 1:
            if isinstance(node.args[0], ast.Constant) and node.args[0].value == 1:
                out.append(_splice(source, node.args[0], "0"))
    return out


def _lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re]))
    return out


def _eq_to_ne(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " != " + source[rs:re]))
    return out


def _fix_while_len_str_not_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
            txt = ast.get_source_segment(source, node)
            if txt and "len(str(" in txt and "!= 1" in txt:
                out.append(_splice(source, node, txt.replace("!= 1", "> 1")))
    return out


def _fix_return_input_to_int(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "input":
            out.append(_splice(source, node.value, "int(input())"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            for arg in node.args:
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                    out.append(_splice(source, arg, "int(input())"))
    return out


def _fix_input_in_function_to_int(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            out.append(_splice(source, node, "int(input())"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="input_needs_int", apply=_fix_input_to_int, symptoms=("wrong", "err:TypeError")),
            Rule(name="range_one_to_zero", apply=_range_start_1_to_0, symptoms=("wrong",)),
            Rule(name="strict_lt_to_le", apply=_lt_to_le, symptoms=("wrong",)),
            Rule(name="equality_to_inequality", apply=_eq_to_ne, symptoms=("wrong",)),
            Rule(name="while_len_str_not_one", apply=_fix_while_len_str_not_one, symptoms=("wrong",)),
            Rule(name="return_or_print_input_needs_int", apply=_fix_return_input_to_int, symptoms=("wrong", "err:TypeError")),
            Rule(name="call_input_needs_int_generic", apply=_fix_input_in_function_to_int, symptoms=("wrong", "err:TypeError")),
        ]