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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(name="assign_comparison_target_correctly", apply=_fix_name_assignment, symptoms=("wrong",)),
            Rule(name="comparison_target_should_be_person", apply=_fix_person_assignment, symptoms=("wrong",)),
            Rule(name="append_to_output_list", apply=_fix_append_target, symptoms=("wrong",)),
            Rule(name="missing_return_after_loop", apply=_fix_missing_return, symptoms=("wrong",)),
            Rule(name="remove_selected_item_not_index_or_age", apply=_fix_pop_remove_mismatch, symptoms=("wrong",)),
            Rule(name="return_sorted_list_not_none", apply=_fix_reverse_return, symptoms=("wrong",)),
            Rule(name="lower_bound_in_sort_by_age", apply=_fix_sort_key_return_age, symptoms=("wrong",)),
            Rule(name="append_removed_item_instead_of_last_loop_var", apply=_fix_append_last_var, symptoms=("wrong",)),
            Rule(name="replace_print_with_return", apply=_fix_print_tail, symptoms=("wrong",)),
            Rule(name="merge_sort_compare_age_not_gender", apply=_fix_merge_compare, symptoms=("wrong",)),
            Rule(name="split_halves_with_integer_division", apply=_fix_half_split, symptoms=("wrong",)),
            Rule(name="collect_selected_persons_not_first_element", apply=_fix_list0_collection, symptoms=("wrong",)),
            Rule(name="fix_descending_insertion_sort_condition", apply=_fix_insertion_sort_compare, symptoms=("wrong",)),
            Rule(name="fix_bubble_sort_reverse_condition", apply=_fix_bubble_sort_condition, symptoms=("wrong",)),
        ]


def _fix_name_assignment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.value, ast.Name) and node.value.id == "n":
                tgt = node.targets[0]
                if isinstance(tgt, ast.Name) and tgt.id == "i":
                    out.append(_replace_node(source, node.value, "element"))
    return out


def _fix_person_assignment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.value, ast.Name) and node.value.id == "oldest":
                tgt = node.targets[0]
                if isinstance(tgt, ast.Name) and tgt.id == "person":
                    out.append(_replace_node(source, node.targets[0], "oldest"))
    return out


def _fix_append_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "append":
            if isinstance(node.value, ast.Name) and node.value.id in {"final", "sort"}:
                parent = node
                for p in ast.walk(tree):
                    pass
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and len(call.args) == 1:
                if isinstance(call.func.value, ast.Name) and call.func.value.id == "final":
                    out.append(_replace_node(source, call.func.value, "newlst"))
                elif isinstance(call.func.value, ast.Name) and call.func.value.id == "sorted":
                    out.append(_replace_node(source, call.func.value, "new_lst"))
    return out


def _fix_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "sort_age":
            if not any(isinstance(n, ast.Return) for n in node.body):
                last = node.body[-1]
                if isinstance(last, ast.Expr):
                    out.append(source[:_span(source, last)[0]] + "    return sort\n" + source[_span(source, last)[1]:])
    return out


def _fix_pop_remove_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "lst":
            sl = node.slice
            if isinstance(sl, ast.Name) and sl.id == "i":
                out.append(_replace_node(source, node, "oldest"))
    return out


def _fix_reverse_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                if node.value.func.attr == "reverse":
                    out.append(_replace_node(source, node.value, "lst"))
    return out


def _fix_sort_key_return_age(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name) and node.targets[0].id == "smallest":
                if isinstance(node.value, ast.Subscript):
                    out.append(_replace_node(source, node.value, "lst[0]"))
    return out


def _fix_append_last_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, ast.Name) and arg.id == "smallest":
                    out.append(_replace_node(source, arg, "oldest"))
                if isinstance(arg, ast.Name) and arg.id == "biggest":
                    out.append(_replace_node(source, arg, "oldest"))
    return out


def _fix_print_tail(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "print":
                out.append(_replace_node(source, node, "    return sort\n"))
    return out


def _fix_merge_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_replace_node(source, node, source[ls:le] + " > " + source[rs:re]))
            elif isinstance(left, ast.Subscript) and isinstance(right, ast.Name) and right.id in {"right", "left"}:
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_replace_node(source, node, source[ls:le] + " > " + source[rs:re]))
    return out


def _fix_half_split(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if isinstance(node.left, ast.Name) and node.left.id == "n":
                out.append(_replace_node(source, node, "len(lst) // 2"))
    return out


def _fix_list0_collection(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "lst":
            if isinstance(node.slice, ast.Constant) and node.slice.value == 0:
                out.append(_replace_node(source, node, "i"))
    return out


def _fix_insertion_sort_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_replace_node(source, node, source[ls:le] + " > " + source[rs:re]))
    return out


def _fix_bubble_sort_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_replace_node(source, node, source[ls:le] + " < " + source[rs:re]))
    return out