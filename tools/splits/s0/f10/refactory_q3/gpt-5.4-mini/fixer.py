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


def _iter_nodes(tree):
    return ast.walk(tree)


def _wrap_in_list_literal(source, expr):
    return "[" + source[_span(source, expr)[0]:_span(source, expr)[1]] + "]"


def _fixed_append_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in _iter_nodes(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
            left, right = node.left, node.comparators[0]
            if isinstance(right, ast.Name):
                parent_func = None
                for p in _iter_nodes(tree):
                    if isinstance(p, ast.FunctionDef):
                        parent_func = p
                        break
                if parent_func is None:
                    continue
                target = right.id
                replacement = source[_span(source, left)[0]:_span(source, left)[1]]
                new_cmp = source[_span(source, left)[0]:_span(source, left)[1]] + " not in " + target
                out.append(_splice(source, node, new_cmp))
    return out


def _append_or_concat_to_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in _iter_nodes(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if isinstance(node.target, ast.Name):
                rhs = node.value
                if isinstance(rhs, ast.Name):
                    new_text = f"{source[_span(source, node.target)[0]:_span(source, node.target)[1]]}.append({source[_span(source, rhs)[0]:_span(source, rhs)[1] if hasattr(rhs,'end_col_offset') else _span(source, rhs)[1]]})"
                    out.append(_splice(source, node, new_text))
                elif isinstance(rhs, ast.Call) and isinstance(rhs.func, ast.Name):
                    pass
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "insert" and len(call.args) == 2:
                obj = call.func.value
                if isinstance(obj, ast.Name) and len(call.args) == 2 and isinstance(call.args[0], ast.Constant) and call.args[0].value == 0:
                    new_text = source[_span(source, obj)[0]:_span(source, obj)[1]] + ".append(" + source[_span(source, call.args[1])[0]:_span(source, call.args[1])[1]] + ")"
                    out.append(_splice(source, node, new_text))
    return out


def _fix_return_inside_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for stmt in func.body:
            if isinstance(stmt, ast.For):
                for inner in stmt.body:
                    if isinstance(inner, ast.Return):
                        new_text = ""
                        out.append(_splice(source, inner, new_text))
                        return out
    return []


def _fix_lst_not_lst0(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == "lst":
                if len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Constant) and node.value.args[0].value == 0:
                    new_text = "[]"
                    out.append(_splice(source, node.value, new_text))
    return out


def _fix_list_initialized_to_first_element(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Subscript):
            if isinstance(node.value.value, ast.Name) and node.value.value.id == "lst":
                sl = node.value.slice
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    out.append(_splice(source, node.value, "[]"))
    return out


def _fix_count_one_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            cmp = node.test
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq):
                if isinstance(cmp.comparators[0], ast.Constant) and cmp.comparators[0].value == 1:
                    left_s, left_e = _span(source, cmp.left)
                    comp_s, comp_e = _span(source, cmp.comparators[0])
                    new_test = source[left_s:left_e] + " != " + source[comp_s:comp_e]
                    out.append(_splice(source, cmp, new_test))
    return out


def _fix_range_len_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Add):
                if isinstance(node.args[0].right, ast.Constant) and node.args[0].right.value == 1:
                    left = node.args[0].left
                    if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                        out.append(_splice(source, node, f"range(len({source[_span(source, left.args[0])[0]:_span(source, left.args[0])[1]]}))"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="use_result_container_not_input", apply=_fixed_append_rule, symptoms=("wrong",)),
            Rule(name="append_singleton_not_augassign_or_insert_front", apply=_append_or_concat_to_append, symptoms=("wrong",)),
            Rule(name="remove_early_return_in_loop", apply=_fix_return_inside_loop, symptoms=("wrong",)),
            Rule(name="replace_lst_call_with_empty_list", apply=_fix_lst_not_lst0, symptoms=("err:TypeError", "wrong")),
            Rule(name="replace_first_element_seed_with_empty_list", apply=_fix_list_initialized_to_first_element, symptoms=("wrong",)),
            Rule(name="count_equals_one_should_use_membership", apply=_fix_count_one_condition, symptoms=("wrong",)),
            Rule(name="fix_range_len_plus_one", apply=_fix_range_len_off_by_one, symptoms=("wrong",)),
        ]