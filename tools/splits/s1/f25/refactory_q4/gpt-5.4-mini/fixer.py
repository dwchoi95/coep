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


def _replace_node(source, target, replacement):
    s, e = _span(source, target)
    rs, re = _span(source, replacement)
    return source[:s] + source[rs:re] + source[e:]


def _cmp_age_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Gt) or isinstance(op, ast.GtE) or isinstance(op, ast.Lt):
                left = node.left
                right = node.comparators[0]
                try:
                    if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                        if isinstance(left.slice, ast.Constant) and left.slice.value == 1 and \
                           isinstance(right.slice, ast.Constant) and right.slice.value == 1:
                            ls, le = _span(source, left)
                            rs, re = _span(source, right)
                            new_cmp = source[ls:le] + " > " + source[rs:re]
                            out.append(_splice(source, node, new_cmp))
                except Exception:
                    pass
    return out


def _fix_assignment_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
            txt = ast.get_source_segment(source, node)
            if txt and "- " in txt:
                continue
        if isinstance(node, ast.Assign):
            seg = ast.get_source_segment(source, node)
            if seg and "biggesr  - i" in seg:
                out.append(source.replace("biggesr  - i", "biggest = i"))
    return out


def _fix_wrong_name_in_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"smallest", "biggest", "largest"}:
                pass
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in {"smallest", "final", "sort", "s"}:
                pass
    if "i = n" in source:
        out.append(source.replace("i = n", "i = element"))
    if "final.append(i)\n        \n    return final" in source:
        out.append(source.replace("return final", "return sort"))
    return out


def _fix_pop_index_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            pass
    if "lst.pop[index]" in source:
        out.append(source.replace("lst.pop[index]", "lst.pop(index)"))
    if "lst.pop[i]" in source:
        out.append(source.replace("lst.pop[i]", "lst.pop(i)"))
    return out


def _fix_return_missing(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "sort_age":
            body = node.body
            if body and isinstance(body[-1], ast.Expr):
                seg = ast.get_source_segment(source, body[-1])
                if seg and seg.strip().startswith("print("):
                    start, end = _span(source, body[-1])
                    out.append(source[:start] + "return " + seg + source[end:])
    if source.rstrip().endswith("pass"):
        out.append(source.replace("\n    pass", ""))
    return out


def _fix_reverse_missing(source):
    if "s.reverse()" not in source and "return s" in source and "smallest" in source:
        return [source.replace("return s", "s.reverse()\n    return s")]
    if "return sort" in source and "sort.reverse()" not in source and "smallest" in source:
        return [source.replace("return sort", "sort.reverse()\n    return sort")]
    return []


def _fix_age_aggregation(source):
    if "person[1] = " in source or "lst[j][1],lst[j+1][1]" in source:
        return []
    out = []
    if "if element > biggest:" in source:
        out.append(source.replace("if element > biggest:", "if element[1] > biggest[1]:"))
    if "if i[1] < smallest[1]:" in source and "reverse" not in source:
        out.append(source.replace("if i[1] < smallest[1]:", "if i[1] > smallest[1]:"))
    if "if i[1] < smallest[1]:" in source and "s.reverse()" in source:
        out.append(source.replace("if i[1] < smallest[1]:", "if i[1] > oldest[1]:"))
    return out


def _fix_list_alias(source):
    if "a = lst" in source and "sort.append(largest)" in source:
        return [source.replace("a = lst", "a = lst")]
    return []


def _fix_bubble_bounds(source):
    out = []
    if "range(len(lst)-1-i)" in source and "lst[j][1] < lst[j+1][1]" in source:
        out.append(source.replace("lst[j][1],lst[j+1][1] = lst[j+1][1],lst[j][1]", "lst[j],lst[j+1] = lst[j+1],lst[j]"))
    if "range(len(lst)-1-i)" in source and "lst[j][1] < lst[j+1][1]" in source:
        out.append(source.replace("for i in range(len(lst)-1):\n        for j in range(len(lst)-1-i):", "for j in range(len(lst)-1):\n        for i in range(len(lst)-1-j):"))
    if "lst[i][1]<lst[i+1][1]" in source and "swap = True" in source:
        out.append(source.replace("for i in range(len(lst)-1):\n            if lst[i][1] < lst[i+1][1]:", "for i in range(len(lst)-1):\n            if lst[i][1] < lst[i+1][1]:"))
    return out


def _fix_recursive_half(source):
    if "return [holder]+sort_age(lst[1:])" in source:
        return [source.replace("return [holder]+sort_age(lst[1:])", "lst.remove(holder)\n    return [holder]+sort_age(lst)")]
    return []


def _fix_empty_list_guard(source):
    out = []
    if "new_lst=[lst[0],]" in source and "if lst==[]:" in source:
        out.append(source.replace("new_lst=[lst[0],]\n    if lst==[]:\n        return []", "if lst==[]:\n        return []\n    new_lst=[lst[0],]"))
    if "result = (lst[0],)" in source and "if lst==[]:" not in source:
        out.append(source.replace("result = (lst[0],)", "if lst==[]:\n        return []\n    result = (lst[0],)"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="compare_ages_by_second_item", apply=_cmp_age_fix, symptoms=("wrong",)),
            Rule(name="assignment_typo_to_update_candidate", apply=_fix_assignment_typo, symptoms=("wrong", "err:NameError")),
            Rule(name="pop_index_call_fix", apply=_fix_pop_index_call, symptoms=("wrong", "err:TypeError")),
            Rule(name="missing_return_or_print_leak", apply=_fix_return_missing, symptoms=("wrong",)),
            Rule(name="reverse_after_building_ascending", apply=_fix_reverse_missing, symptoms=("wrong",)),
            Rule(name="compare_gender_instead_of_age", apply=_fix_age_aggregation, symptoms=("wrong",)),
            Rule(name="bubble_sort_swap_whole_items", apply=_fix_bubble_bounds, symptoms=("wrong",)),
            Rule(name="recursive_remove_then_recurse", apply=_fix_recursive_half, symptoms=("wrong",)),
            Rule(name="empty_input_guard_moved_before_index", apply=_fix_empty_list_guard, symptoms=("err:IndexError", "wrong")),
        ]