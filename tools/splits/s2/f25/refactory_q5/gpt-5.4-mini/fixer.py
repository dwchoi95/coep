import ast
from src.core.repair import Rule


def _span(source, node):
    """(start, end) char offsets of node in source."""
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
    s, e = _span(source, target)
    rs, re = _span(source, replacement)
    return source[:s] + source[rs:re] + source[e:]


def _replace_constant(source, const_node, value_text):
    return _splice(source, const_node, value_text)


def _fix_missing_return_after_recursive_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "top_k":
            for stmt in node.body:
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.BinOp):
                    if isinstance(stmt.value.op, ast.Add):
                        right = stmt.value.right
                        if isinstance(right, ast.Call) and isinstance(right.func, ast.Name) and right.func.id == "top_k":
                            out.append(_splice(source, stmt.value.right, "new_list"))
    return out


def _fix_return_literal_slice(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
            sub = node.value
            if isinstance(sub.slice, ast.Slice) and isinstance(sub.slice.lower, ast.Constant) and isinstance(sub.slice.upper, ast.Constant):
                if isinstance(sub.slice.upper.value, int) and sub.slice.upper.value in (3, 1, -1, 0):
                    out.append(_splice(source, sub.slice.upper, "k"))
    return out


def _fix_return_wrong_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "lst":
            out.append(_splice(source, node.value, "new_lst"))
    return out


def _fix_remove_append_misuse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "append" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "max":
                    pass
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "lst":
                    pass
    return out


def _fix_off_by_one_range(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant):
                if arg.right.value == 1:
                    out.append(_splice(source, arg.right, "0"))
    return out


def _fix_max_to_min_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "max":
            out.append(_splice(source, node.func, "min"))
    return out


def _fix_wrong_compare_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Name) and left.id != right.id:
                if left.id == "x" and right.id == "lst":
                    out.append(_splice(source, right, left.id))
    return out


def _fix_append_remove_max_pattern(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "top_k":
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    if isinstance(stmt.value, ast.List) and not stmt.value.elts and stmt.targets[0].id in {"new_lst", "sort", "result", "res", "l", "n", "values"}:
                        pass
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
            pass
    return out


def _fix_return_sort_slice_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
            sub = node.value
            if isinstance(sub.slice, ast.Slice):
                if isinstance(sub.slice.upper, ast.Constant) and sub.slice.upper.value == 3:
                    out.append(_splice(source, sub.slice.upper, "k"))
                elif isinstance(sub.slice.upper, ast.BinOp) and isinstance(sub.slice.upper.op, ast.Add):
                    if isinstance(sub.slice.upper.right, ast.Constant) and sub.slice.upper.right.value == 1:
                        out.append(_splice(source, sub.slice.upper.right, "0"))
    return out


def _fix_missing_remove_after_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            txt = ast.get_source_segment(source, node)
            if txt and "max(" in txt and ".remove(" not in txt:
                out.append(source[:_span(source, node)[0]] + txt.replace("sort.append(i)", "lst.remove(largest)\n        sort.append(largest)").replace("sort.append(maxi)", "lst.remove(maxi)\n        sort.append(maxi)") + source[_span(source, node)[1]:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="recursive_call_uses_wrong_variable", apply=_fix_missing_return_after_recursive_call, symptoms=("wrong",)),
            Rule(name="slice_upper_bound_off_by_one", apply=_fix_return_literal_slice, symptoms=("wrong",)),
            Rule(name="return_original_list_instead_of_result", apply=_fix_return_wrong_name, symptoms=("wrong",)),
            Rule(name="range_bound_off_by_one", apply=_fix_off_by_one_range, symptoms=("wrong",)),
            Rule(name="max_called_as_min_in_selection_loop", apply=_fix_max_to_min_loop, symptoms=("wrong",)),
            Rule(name="comparison_uses_wrong_operand", apply=_fix_wrong_compare_var, symptoms=("wrong",)),
            Rule(name="return_slice_fixed_to_k", apply=_fix_return_sort_slice_k, symptoms=("wrong",)),
        ]