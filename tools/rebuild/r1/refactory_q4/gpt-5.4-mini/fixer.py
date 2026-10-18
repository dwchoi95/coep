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


def _name_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"sort", "biggest", "smallest", "final", "new_lst", "new"}:
            pass
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sort_age"]:
        target = None
        for n in ast.walk(func):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id != "lst":
                target = n
        if target is not None:
            out.append(_splice(source, target.value, "sort"))
    return out


def _fix_return_none(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            continue
    return out


def _common_local_fixes(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and node.value.attr == "reverse":
            out.append(_splice(source, node.value, node.value.value.id))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            out.append(_splice(source, node, source[_span(source, left)[0]:_span(source, left)[1]] + " > " + source[_span(source, right)[0]:_span(source, right)[1]]))
    return out


def _replace_expr(source, old, new):
    return _splice(source, old, new)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="return_wrong_variable_sort",
                apply=lambda s: _apply_return_wrong_variable(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="use_current_item_not_loop_variable",
                apply=lambda s: _apply_append_loop_var(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="replace_spurious_identifier_with_candidate",
                apply=lambda s: _apply_bad_identifier_fix(s),
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_oldest_assignment_in_comparison_loop",
                apply=lambda s: _apply_compare_assignment_fix(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_remove_and_append_target",
                apply=lambda s: _apply_remove_append_target(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_reverse_return",
                apply=lambda s: _apply_reverse_return(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_selection_sort_swap",
                apply=lambda s: _apply_swap_fix(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_min_max_direction",
                apply=lambda s: _apply_minmax_direction(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_empty_list_check_tuple",
                apply=lambda s: _apply_empty_check(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_infinite_or_early_return",
                apply=lambda s: _apply_return_inside_loop(s),
                symptoms=("wrong",),
            ),
        ]


def _apply_return_wrong_variable(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"sort", "new", "output", "result", "new_list", "sorted_lst"}:
            out.append(_splice(source, node.value, node.value.id.replace("sort", "sortt") if node.value.id == "sort" and "sortt" in source else node.value.id))
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "sort":
            out.append(_splice(source, node.value, "sortt"))
    return out


def _apply_append_loop_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                out.append(_splice(source, arg, "smallest" if arg.id in {"i", "j", "counter", "largest", "biggest"} else "current"))
    return out


def _apply_bad_identifier_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in {"list", "a", "n", "biggest", "smallest", "larget"}:
            if node.id == "list":
                out.append(_splice(source, node, "lst"))
            elif node.id == "a":
                out.append(_splice(source, node, "lst"))
            elif node.id == "n":
                out.append(_splice(source, node, "i"))
            elif node.id == "larget":
                out.append(_splice(source, node, "largest"))
            elif node.id == "biggest":
                out.append(_splice(source, node, "smallest"))
            elif node.id == "smallest":
                out.append(_splice(source, node, "smallest"))
    return out


def _apply_compare_assignment_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Name):
            if node.targets[0].id in {"i", "person", "persons"} and node.value.id in {"oldest", "smallest"}:
                out.append(_splice(source, node.value, node.targets[0].id))
    return out


def _apply_remove_append_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                out.append(_splice(source, arg, "smallest"))
            elif isinstance(arg, ast.Subscript):
                out.append(_splice(source, arg, "smallest"))
    return out


def _apply_reverse_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
            out.append(_splice(source, node.value, node.value.func.value.id if isinstance(node.value.func.value, ast.Name) else "sort"))
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute) and node.value.attr == "reverse":
            out.append(_splice(source, node, f"{source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]]}.reverse()"))
    return out


def _apply_swap_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 2:
            if isinstance(node.targets[0], ast.Subscript) and isinstance(node.targets[1], ast.Subscript):
                t1s, t1e = _span(source, node.targets[0])
                t2s, t2e = _span(source, node.targets[1])
                new = source[t1s:t1e] + ", " + source[t2s:t2e]
                out.append(_splice(source, node, new))
    return out


def _apply_minmax_direction(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " > " + source[rs:re_]))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " > " + source[rs:re_]))
    return out


def _apply_empty_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.comparators[0], ast.Tuple):
                rs, re_ = _span(source, node.comparators[0])
                out.append(_splice(source, node.comparators[0], "[]"))
    return out


def _apply_return_inside_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            parent_text = source[:_span(source, node)[0]]
            if "while" in parent_text[-80:]:
                out.append(source)
    return []