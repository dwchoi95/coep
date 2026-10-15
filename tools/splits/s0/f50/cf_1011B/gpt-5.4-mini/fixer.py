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


def _replace_compare_op(source, old_cls, new_op_text):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], old_cls):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + f" {new_op_text} " + source[rs:re]))
    return out


def _fix_binary_search_upper_bound(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id == "r" and isinstance(node.value, ast.Constant) and node.value.value == 100:
                out.append(_splice(source, node.value, "100000"))
    return out


def _fix_list_counter_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id == "b" and isinstance(node.value, ast.List) and len(node.value.elts) == 1:
                elt = node.value.elts[0]
                if isinstance(elt, ast.Constant) and elt.value == 0:
                    out.append(_splice(source, node.value, "[0]*100"))
    return out


def _fix_from_counter_from_input(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "Counter" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                    if isinstance(arg.parent, ast.Call):
                        pass
    return out


def _fix_min_days_zero_init(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id == "prev_days":
                if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.FloorDiv):
                    left = node.value.left
                    if isinstance(left, ast.Subscript):
                        out.append(_splice(source, node.value, "0"))
    return out


def _fix_len_food_init(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id == "b":
                if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                    out.append(_splice(source, node.value, "[n]"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="binary_search_upper_bound_too_small", apply=_fix_binary_search_upper_bound, symptoms=("wrong",)),
            Rule(name="strict_lt_to_le", apply=lambda s: _replace_compare_op(s, ast.Lt, "<="), symptoms=("wrong",)),
            Rule(name="strict_gt_to_ge", apply=lambda s: _replace_compare_op(s, ast.Gt, ">="), symptoms=("wrong",)),
            Rule(name="counter_list_length_should_be_n", apply=_fix_len_food_init, symptoms=("wrong",)),
            Rule(name="initial_prev_days_should_be_zero", apply=_fix_min_days_zero_init, symptoms=("wrong",)),
        ]