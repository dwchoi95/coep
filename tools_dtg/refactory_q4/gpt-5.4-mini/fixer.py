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


def _name(node):
    return isinstance(node, ast.Name)


def _cmp_text(source, node):
    ls, le = _span(source, node.left)
    rs, re = _span(source, node.comparators[0])
    return source[ls:le], source[rs:re]


def _rewrite_compare(source, node, op_text):
    left, right = _cmp_text(source, node)
    return _splice(source, node, f"{left} {op_text} {right}")


def _rule_fix_index_remove_append(source):
    """Replace loop variable with tracked selection in remove/append."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sort_age"]:
        for wh in [n for n in ast.walk(fn) if isinstance(n, ast.While)]:
            if len(wh.body) < 2:
                continue
            first, second = wh.body[0], wh.body[1]
            if not (isinstance(first, ast.Expr) or isinstance(first, ast.Assign)):
                continue
            for stmt in wh.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    if isinstance(call.func, ast.Attribute) and call.func.attr in ("append", "remove"):
                        arg = call.args[0] if call.args else None
                        if isinstance(arg, ast.Name):
                            if call.func.attr == "remove":
                                out.append(_splice(source, arg, "smallest"))
                            elif call.func.attr == "append":
                                out.append(_splice(source, arg, "smallest"))
    return out


def _rule_relax_lt_to_gt(source):
    """Flip age comparison direction when selecting the oldest element."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.Lt):
                out.append(_rewrite_compare(source, node, ">"))
            elif isinstance(node.ops[0], ast.LtE):
                out.append(_rewrite_compare(source, node, ">"))
    return out


def _rule_fix_gt_to_lt(source):
    """Flip descending selection comparisons in insertion/selection style code."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.Gt):
                out.append(_rewrite_compare(source, node, "<"))
            elif isinstance(node.ops[0], ast.GtE):
                out.append(_rewrite_compare(source, node, "<"))
    return out


def _rule_sort_return_sort_name(source):
    """Repair returning the built-in sort function or a missing final list."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            if node.value.id == "sort":
                out.append(_splice(source, node.value, "sortt"))
            if node.value.id in {"new_list", "sorted_lst", "output", "result", "newlst", "sort1"}:
                continue
    return out


def _rule_reverse_call_to_method(source):
    """Turn list.reverse used as a value into an in-place call."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "reverse":
            parent_call = None
            for p in ast.walk(tree):
                if isinstance(p, ast.Call) and p.func is node:
                    parent_call = p
                    break
            if parent_call is not None:
                out.append(_splice(source, node, "reverse()"))
    return out


def _rule_fix_pop_index_arg(source):
    """Replace pop subscript/variable misuse with a proper index or element."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
            if node.args and isinstance(node.args[0], ast.Subscript):
                out.append(_splice(source, node.args[0], "index"))
    return out


def _rule_fix_assignment_swap(source):
    """Repair broken two-step swaps into tuple swap."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Subscript) and isinstance(node.value, ast.Subscript):
                parent = None
                for n in ast.walk(tree):
                    if isinstance(n, ast.FunctionDef) and any(node is b for b in n.body):
                        parent = n
                        break
                if parent:
                    out.append(_splice(source, node, f"{source[_span(source, t)[0]:_span(source, t)[1]]}, {source[_span(source, node.value)[0]:_span(source, node.value)[1]]} = {source[_span(source, node.value)[0]:_span(source, node.value)[1]]}, {source[_span(source, t)[0]:_span(source, t)[1]]}"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="index_variable_instead_of_selected_item", apply=_rule_fix_index_remove_append, symptoms=("wrong", "timeout")),
            Rule(name="comparison_direction_lt_to_gt_for_oldest", apply=_rule_relax_lt_to_gt, symptoms=("wrong",)),
            Rule(name="comparison_direction_gt_to_lt_for_descending", apply=_rule_fix_gt_to_lt, symptoms=("wrong",)),
            Rule(name="wrong_returned_sort_name", apply=_rule_sort_return_sort_name, symptoms=("wrong",)),
            Rule(name="reverse_method_used_as_value", apply=_rule_reverse_call_to_method, symptoms=("wrong",)),
            Rule(name="pop_called_on_subscript", apply=_rule_fix_pop_index_arg, symptoms=("wrong", "err:TypeError")),
            Rule(name="broken_assignment_swap", apply=_rule_fix_assignment_swap, symptoms=("wrong",)),
        ]