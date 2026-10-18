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


class Fixer:
    def rules(self):
        return [
            Rule(name="fix_wrong_list_reference_and_target_container",
                 apply=_fix_wrong_list_reference_and_target_container,
                 symptoms=("wrong", "err:NameError", "err:TypeError")),
            Rule(name="fix_return_wrong_variable",
                 apply=_fix_return_wrong_variable,
                 symptoms=("wrong",)),
            Rule(name="fix_append_result_of_append_or_extend",
                 apply=_fix_append_result_of_append_or_extend,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_count_membership_target",
                 apply=_fix_count_membership_target,
                 symptoms=("wrong",)),
            Rule(name="fix_list_typed_loop_target_shadowing",
                 apply=_fix_list_typed_loop_target_shadowing,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_ordered_dict_list_wrap",
                 apply=_fix_ordered_dict_list_wrap,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_set_solution_to_ordered_dict",
                 apply=_fix_set_solution_to_ordered_dict,
                 symptoms=("wrong",)),
            Rule(name="fix_reverse_method_used_as_value",
                 apply=_fix_reverse_method_used_as_value,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="fix_pop_without_call",
                 apply=_fix_pop_without_call,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_extend_scalar_to_append",
                 apply=_fix_extend_scalar_to_append,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_incorrect_empty_return",
                 apply=_fix_incorrect_empty_return,
                 symptoms=("wrong",)),
            Rule(name="fix_count_comparison_direction",
                 apply=_fix_count_comparison_direction,
                 symptoms=("wrong",)),
            Rule(name="fix_range_off_by_one_and_empty_index",
                 apply=_fix_range_off_by_one_and_empty_index,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="fix_variable_name_occurrences_typo",
                 apply=_fix_variable_name_occurrences_typo,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_newlist_new_lst_mismatch",
                 apply=_fix_newlist_new_lst_mismatch,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_tuple_building_with_wrong_operator",
                 apply=_fix_tuple_building_with_wrong_operator,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_self_membership_vs_item_membership",
                 apply=_fix_self_membership_vs_item_membership,
                 symptoms=("wrong",)),
            Rule(name="fix_insert_front_to_append",
                 apply=_fix_insert_front_to_append,
                 symptoms=("wrong",)),
        ]


def _fix_wrong_list_reference_and_target_container(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
            s, e = _span(source, node.iter)
            out.append(source[:s] + "lst" + source[e:])
        if isinstance(node, ast.Compare):
            for side in [node.left] + node.comparators:
                if isinstance(side, ast.Name) and side.id == "list":
                    s, e = _span(source, side)
                    out.append(source[:s] + "lst" + source[e:])
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "list":
            s, e = _span(source, node.value)
            out.append(source[:s] + "lst" + source[e:])
    return list(dict.fromkeys(out))


def _fix_return_wrong_variable(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            name = node.value.id
            for cand in ("new_list", "new_lst", "output", "result", "keep", "removed", "remove_lst", "a", "newlist", "lst1", "final"):
                if cand in source and cand != name:
                    s, e = _span(source, node.value)
                    out.append(source[:s] + cand + source[e:])
                    break
    return list(dict.fromkeys(out))


def _fix_append_result_of_append_or_extend(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Attribute) and f.attr in {"append", "extend"}:
                s, e = _span(source, node)
                new = source[s:e].replace(" = " + source[_span(source, node.value)[0]:_span(source, node.value)[1]], "")
                out.append(source[:s] + new.split("=", 1)[0].strip() + "." + f.attr + "(" + ", ".join(source[_span(source, a)[0]:_span(source, a)[1]] for a in node.value.args) + ")" + source[e:])
    return list(dict.fromkeys(out))


def _fix_count_membership_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
            left, right = node.left, node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Name) and left.id == right.id:
                continue
            if isinstance(right, ast.Name) and right.id != "new_list" and right.id != "new_lst" and right.id != "output" and right.id != "result":
                for cand in ("new_list", "new_lst", "output", "result", "keep", "a", "final", "pst", "new"):
                    if cand in source:
                        rs, re = _span(source, right)
                        out.append(source[:rs] + cand + source[re:])
                        break
    return list(dict.fromkeys(out))


def _fix_list_typed_loop_target_shadowing(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id in {"list", "new_lst", "new_list"}:
            if isinstance(node.iter, ast.Name) and node.iter.id != "lst":
                s, e = _span(source, node.iter)
                out.append(source[:s] + "lst" + source[e:])
            if node.target.id == "lst" and "i" in source:
                s, e = _span(source, node.target)
                out.append(source[:s] + "i" + source[e:])
    return list(dict.fromkeys(out))


def _fix_ordered_dict_list_wrap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Name) and f.id == "OrderedDict":
                s, e = _span(source, node.value)
                out.append(source[:s] + "list(" + source[s:e] + ")" + source[e:])
            if isinstance(f, ast.Name) and f.id == "lists":
                s, e = _span(source, f)
                out.append(source[:s] + "list" + source[e:])
    return list(dict.fromkeys(out))


def _fix_set_solution_to_ordered_dict(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    if "set(lst)" not in source:
        return []
    return [source.replace("set(lst)", "OrderedDict.fromkeys(lst)") if "from collections import OrderedDict" in source else "from collections import OrderedDict\n\n" + source.replace("set(lst)", "OrderedDict.fromkeys(lst)")]


def _fix_reverse_method_used_as_value(source):
    if ".reverse" not in source:
        return []
    out = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "reverse" and isinstance(node.ctx, ast.Load):
            s, e = _span(source, node)
            out.append(source[:s] + source[s:e] + "()" + source[e:])
    return list(dict.fromkeys(out))


def _fix_pop_without_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "pop" and isinstance(node.ctx, ast.Load):
            s, e = _span(source, node)
            out.append(source[:s] + source[s:e] + "()" + source[e:])
    return list(dict.fromkeys(out))


def _fix_extend_scalar_to_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Name) or isinstance(arg, ast.Constant):
                s, e = _span(source, arg)
                out.append(source[:s] + "[" + source[s:e] + "]" + source[e:])
    return list(dict.fromkeys(out))


def _fix_incorrect_empty_return(source):
    if "return None" in source:
        return [source.replace("return None", "return []")]
    return []


def _fix_count_comparison_direction(source):
    if "count(" not in source and ".count(" not in source:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Eq) and isinstance(node.left, ast.Call):
                if getattr(node.left.func, "attr", None) == "count":
                    s, e = _span(source, op)
                    out.append(source[:s] + "==" + source[e:])
            if isinstance(op, ast.Gt) and isinstance(node.left, ast.Call):
                if getattr(node.left.func, "attr", None) == "count":
                    s, e = _span(source, op)
                    out.append(source[:s] + "==" + source[e:])
            if isinstance(op, ast.Lt) and isinstance(node.left, ast.Call):
                if getattr(node.left.func, "attr", None) == "count":
                    s, e = _span(source, op)
                    out.append(source[:s] + ">=" + source[e:])
    return list(dict.fromkeys(out))


def _fix_range_off_by_one_and_empty_index(source):
    if "range(len(lst)-1)" in source:
        return [source.replace("range(len(lst)-1)", "range(len(lst))")]
    if "range(0, len(lst)-1)" in source:
        return [source.replace("range(0, len(lst)-1)", "range(0, len(lst))")]
    return []


def _fix_variable_name_occurrences_typo(source):
    if "occurences" in source:
        return [source.replace("occurences", "occurrences")]
    return []


def _fix_newlist_new_lst_mismatch(source):
    out = []
    if "newlist" in source and "new_lst" in source:
        out.append(source.replace("newlist", "new_lst"))
    if "new_list" in source and "new_lst" in source and "return new_list" in source:
        out.append(source.replace("return new_list", "return new_lst"))
    return list(dict.fromkeys(out))


def _fix_tuple_building_with_wrong_operator(source):
    if "new_list += (x)" in source:
        return [source.replace("new_list += (x)", "new_list += (x,)")]
    return []


def _fix_self_membership_vs_item_membership(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
            if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Name):
                s, e = _span(source, node.ops[0])
                out.append(source[:s] + "not in" + source[e:])
    return list(dict.fromkeys(out))


def _fix_insert_front_to_append(source):
    if ".insert(0," in source:
        return [source.replace(".insert(0,", ".append(")]
    if "insert(len[new_lst]-1" in source:
        return [source.replace("insert(len[new_lst]-1", "insert(len(new_lst)",)]
    return []