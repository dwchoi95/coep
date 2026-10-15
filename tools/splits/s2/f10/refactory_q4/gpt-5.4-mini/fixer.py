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


def _fix_return_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            name = node.value.id
            func = None
            for p in ast.walk(tree):
                if isinstance(p, ast.FunctionDef):
                    for stmt in p.body:
                        if stmt is node:
                            func = p
                            break
                if func:
                    break
            if func is None:
                continue
            target = None
            for stmt in func.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name):
                            target = t.id
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    target = stmt.target.id
            if target and target != name:
                out.append(_splice(source, node, f"return {target}"))
    return out


def _fix_empty_list_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.Eq):
                left, right = node.left, node.comparators[0]
                if isinstance(right, ast.Tuple) and len(right.elts) == 0:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " == []"))
    return out


def _fix_sort_mutation_to_max_extract(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "sort" and len(node.args) == 0 and len(node.keywords) == 2:
                kw_names = {k.arg for k in node.keywords}
                if "key" in kw_names and "reverse" in kw_names:
                    out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]]))
    return out


def _fix_return_variable_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        assigned = []
        for stmt in func.body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        assigned.append(t.id)
        for stmt in ast.walk(func):
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
                if stmt.value.id not in assigned and assigned:
                    out.append(_splice(source, stmt, f"return {assigned[-1]}"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="return_assigned_result_name",
                apply=_fix_return_name,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="empty_list_check_tuple_to_list",
                apply=_fix_empty_list_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="replace_sort_call_with_value",
                apply=_fix_sort_mutation_to_max_extract,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_last_assigned_variable",
                apply=_fix_return_variable_mismatch,
                symptoms=("wrong", "err:NameError"),
            ),
        ]