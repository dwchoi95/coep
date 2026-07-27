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


def _replace_node(source, old, new):
    return _splice(source, old, new)


def _list_empty_check_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                right = node.comparators[0]
                if isinstance(right, ast.Tuple) and len(right.elts) == 0:
                    left_s, left_e = _span(source, node.left)
                    right_s, right_e = _span(source, right)
                    out.append(_splice(source, node, source[left_s:left_e] + " == []"))
    return out


def _lt_to_gt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left_s, left_e = _span(source, node.left)
            right_s, right_e = _span(source, node.comparators[0])
            out.append(_splice(source, node, source[left_s:left_e] + " > " + source[right_s:right_e]))
    return out


def _gt_to_lt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left_s, left_e = _span(source, node.left)
            right_s, right_e = _span(source, node.comparators[0])
            out.append(_splice(source, node, source[left_s:left_e] + " < " + source[right_s:right_e]))
    return out


def _empty_base_case_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                if len(left.args) == 1 and isinstance(right, ast.Constant) and right.value == 1:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re]))
    return out


def _pop_index_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id == "lst" and isinstance(node.slice, ast.Name) and node.slice.id == "index":
                out.append(_splice(source, node, "index"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "lst" and node.attr == "pop":
                out.append(_splice(source, node, "lst.pop"))
    return out


def _pop_call_parentheses_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "pop" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    out.append(_splice(source, node, source[_span(source, node.func)[0]:_span(source, node.func)[1]] + "(" + arg.id + ")"))
    return out


def _reverse_return_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            val = node.value
            if isinstance(val, ast.Subscript) and isinstance(val.slice, ast.Slice):
                sl = val.slice
                if sl.lower is None and sl.upper is None and isinstance(sl.step, ast.UnaryOp) and isinstance(sl.step.op, ast.USub):
                    out.append(_splice(source, node, "return " + source[_span(source, val)[0]:_span(source, val)[1]]))
            if isinstance(val, ast.Name):
                continue
    return out


def _append_prepend_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id in {"result", "new_lst", "new", "sort", "rslt"}:
                if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                    if isinstance(node.value.left, ast.Name) and node.value.left.id == tgt.id:
                        right = node.value.right
                        if isinstance(right, ast.List) and len(right.elts) == 1:
                            elt = right.elts[0]
                            if isinstance(elt, ast.Subscript):
                                s, e = _span(source, node.value)
                                out.append(_splice(source, node.value, "[" + source[_span(source, elt)[0]:_span(source, elt)[1]] + "] + " + tgt.id))
    return out


def _remove_wrong_empty_tuple_check(source):
    return _list_empty_check_fix(source)


class Fixer:
    def rules(self):
        return [
            Rule(name="empty_list_not_empty_tuple", apply=_list_empty_check_fix, symptoms=("wrong",)),
            Rule(name="comparison_lt_to_gt", apply=_lt_to_gt, symptoms=("wrong",)),
            Rule(name="comparison_gt_to_lt", apply=_gt_to_lt, symptoms=("wrong",)),
            Rule(name="len_one_should_allow_zero", apply=_empty_base_case_fix, symptoms=("wrong",)),
            Rule(name="fix_pop_index_parentheses", apply=_pop_call_parentheses_fix, symptoms=("err:TypeError", "err:SyntaxError")),
            Rule(name="fix_pop_index_argument", apply=_pop_index_fix, symptoms=("err:TypeError", "wrong")),
            Rule(name="reverse_slicing_return", apply=_reverse_return_fix, symptoms=("wrong",)),
            Rule(name="prepend_instead_of_append", apply=_append_prepend_fix, symptoms=("wrong",)),
        ]