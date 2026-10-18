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


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _max_remove_append_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "top_k"]:
        for w in ast.walk(fn):
            if not isinstance(w, ast.While) or len(w.body) < 2:
                continue
            b0, b1 = w.body[0], w.body[1]
            if not (isinstance(b0, ast.Expr) and isinstance(b0.value, ast.Call) and isinstance(b1, ast.Expr) and isinstance(b1.value, ast.Call)):
                continue
            c0, c1 = b0.value, b1.value
            if not (isinstance(c0.func, ast.Attribute) and isinstance(c1.func, ast.Attribute)):
                continue
            if c0.func.attr != "remove" or c1.func.attr != "append":
                continue
            if not (len(c0.args) == len(c1.args) == 1):
                continue
            arg0, arg1 = c0.args[0], c1.args[0]
            if not (_is_name(c0.func.value, "lst") and _is_name(c1.func.value, "new_list") or _is_name(c1.func.value, "new_lst") or _is_name(c1.func.value, "result") or _is_name(c1.func.value, "sort") or _is_name(c1.func.value, "arranged") or _is_name(c1.func.value, "values") or _is_name(c1.func.value, "new")):
                pass
            if isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) and arg0.func.id == "max" and len(arg0.args) == 1 and _is_name(arg0.args[0], "lst"):
                if ast.dump(arg1, include_attributes=False) == ast.dump(arg0, include_attributes=False):
                    new_body = [ast.Expr(value=c1), ast.Expr(value=c0)]
                    s, e = _span(source, w.body[0])
                    s2, e2 = _span(source, w.body[1])
                    if s < e and s2 < e2:
                        out.append(source[:s] + source[s2:e2] + "\n" + source[s:e] + source[e2:])
    return list(dict.fromkeys(out))


def _append_removed_value_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "remove":
                out.append(_splice(source, node, ast.get_source_segment(source, arg.func.value)))
    return list(dict.fromkeys(out))


def _return_slice_k_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == 5:
            out.append(_splice(source, node.slice, "k"))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add) and isinstance(node.right, ast.Constant) and node.right.value == 1:
            out.append(_splice(source, node.right, "0"))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub) and isinstance(node.right, ast.Constant) and node.right.value == 1:
            out.append(_splice(source, node.right, "0"))
    return list(dict.fromkeys(out))


def _fix_return_lst_slice(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
            sub = node.value
            if isinstance(sub.value, ast.Name) and sub.value.id == "lst" and isinstance(sub.slice, ast.Slice):
                out.append(_splice(source, sub.value, next((n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in {"sort", "result", "new_lst", "sort_list", "sorted_lst", "arranged", "values", "newlist", "new"}), "lst")))
    return list(dict.fromkeys(out))


def _off_by_one_range_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                out.append(_splice(source, arg.right, "0"))
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                out.append(_splice(source, arg.right, "0"))
    return list(dict.fromkeys(out))


def _k_zero_return_empty_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.left, ast.Name) and node.left.id == "k" and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 0:
                out.append(_splice(source, node, "k == 0"))
    return list(dict.fromkeys(out))


def _replace_pop_with_remove_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "max":
                txt = ast.get_source_segment(source, node.func.value)
                out.append(_splice(source, node, f"{txt}.remove(max({txt}))"))
    return list(dict.fromkeys(out))


class Fixer:
    def rules(self):
        return [
            Rule(name="append_removed_value_instead_of_max", apply=_append_removed_value_fix, symptoms=("wrong",)),
            Rule(name="append_before_remove_with_max", apply=_max_remove_append_fix, symptoms=("wrong",)),
            Rule(name="return_lst_slice_when_result_exists", apply=_fix_return_lst_slice, symptoms=("wrong",)),
            Rule(name="off_by_one_slice_k", apply=_return_slice_k_fix, symptoms=("wrong",)),
            Rule(name="off_by_one_range_bound", apply=_off_by_one_range_fix, symptoms=("wrong", "timeout")),
            Rule(name="k_zero_should_return_empty", apply=_k_zero_return_empty_fix, symptoms=("wrong",)),
            Rule(name="pop_max_index_vs_remove_max", apply=_replace_pop_with_remove_max, symptoms=("wrong",)),
        ]