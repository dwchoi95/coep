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


def _ast_equal(a, b):
    return ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)


def _return_slice_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
            sub = node.value
            if isinstance(sub.slice, ast.Slice) and sub.slice.lower is None and sub.slice.upper:
                upper = sub.slice.upper
                if isinstance(upper, ast.BinOp) and isinstance(upper.op, ast.Add) and isinstance(upper.right, ast.Constant) and upper.right.value == 1:
                    left = upper.left
                    replacement = source[_span(source, left)[0]:_span(source, left)[1]]
                    out.append(_splice(source, upper, replacement))
    return out


def _range_minus_one_to_range(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                out.append(_splice(source, node, source[_span(source, arg.left)[0]:_span(source, arg.left)[1]]))
    return out


def _sort_to_reverse_sorted(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "sort" and len(call.args) == 0 and len(call.keywords) == 0:
                replacement = source[_span(source, call.func.value)[0]:_span(source, call.func.value)[1]] + ".sort(reverse=True)"
                out.append(_splice(source, call, replacement))
    return out


def _list_sort_to_max_remove_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        body = func.body
        if len(body) < 3:
            continue
        assign = body[0]
        expr = body[1]
        ret = body[-1]
        if not (isinstance(assign, ast.Assign) and isinstance(assign.value, ast.List) and len(assign.targets) == 1):
            continue
        if not (isinstance(expr, ast.Expr) and isinstance(expr.value, ast.Call)):
            continue
        call = expr.value
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "sort"):
            continue
        if not (isinstance(ret, ast.Return) and isinstance(ret.value, ast.Name) and len(body) == 3):
            continue
        target_name = assign.targets[0]
        if not isinstance(target_name, ast.Name):
            continue
        lst_name = target_name.id
        if not (isinstance(call.func.value, ast.Name) and call.func.value.id == lst_name):
            continue
        if len(call.args) or len(call.keywords):
            continue
        new_text = (
            f"{source[_span(source, assign)[0]:_span(source, assign)[1]]}\n"
            f"    for _ in range(k):\n"
            f"        {ret.value.id}.append(max({lst_name}))\n"
            f"        {lst_name}.remove(max({lst_name}))"
        )
        out.append(_splice(source, body[0], new_text))
    return out


def _range_k_minus_one_to_range_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                out.append(_splice(source, node, source[_span(source, arg.left)[0]:_span(source, arg.left)[1]]))
    return out


def _pop_based_to_remove_based(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1 and not node.keywords:
            target = source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]]
            idx = source[_span(node.args[0].left if isinstance(node.args[0], ast.UnaryOp) and isinstance(node.args[0].op, ast.USub) and isinstance(node.args[0].operand, ast.Call) else node.args[0])[0]:_span(node.args[0] if not (isinstance(node.args[0], ast.UnaryOp) and isinstance(node.args[0].op, ast.USub)) else node.args[0].operand)[1]]
            if isinstance(node.args[0], ast.UnaryOp) and isinstance(node.args[0].op, ast.USub):
                arg_text = "-" + source[_span(node.args[0].operand)[0]:_span(node.args[0].operand)[1]]
            else:
                arg_text = source[_span(node.args[0])[0]:_span(node.args[0])[1]]
            out.append(_splice(source, node, f"{target}.remove({target}[{arg_text}])"))
    return out


def _slice_return_k_to_k_minus_one_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
            sub = node.value
            if isinstance(sub.slice, ast.Slice) and sub.slice.upper:
                upper = sub.slice.upper
                if isinstance(upper, ast.BinOp) and isinstance(upper.op, ast.Add) and isinstance(upper.right, ast.Constant) and upper.right.value == 1:
                    out.append(_splice(source, upper, source[_span(upper.left)[0]:_span(upper.left)[1]]))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="slice_return_off_by_one", apply=_slice_return_k_to_k_minus_one_fix, symptoms=("wrong",)),
            Rule(name="range_k_minus_one_to_k", apply=_range_k_minus_one_to_range_k, symptoms=("wrong",)),
            Rule(name="sort_to_reverse_sorted", apply=_sort_to_reverse_sorted, symptoms=("wrong",)),
            Rule(name="pop_to_remove_in_topk_loop", apply=_pop_based_to_remove_based, symptoms=("wrong",)),
            Rule(name="replace_sort_then_prefix_with_max_remove", apply=_list_sort_to_max_remove_loop, symptoms=("wrong", "timeout")),
        ]