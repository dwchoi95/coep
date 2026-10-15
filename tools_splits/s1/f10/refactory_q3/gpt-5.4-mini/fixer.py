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


def _replace_name_load(source, old, new):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == old:
            out.append(_splice(source, node, new))
    return out


def _replace_set_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "set" and len(call.args) == 1:
                arg = call.args[0]
                ans = source[_span(source, arg)[0]:_span(source, arg)[1]]
                new_text = "[]\n" + source[_span(source, node)[0]:_span(source, node)[0]]
                # safer direct splice for whole return statement
                out.append(_splice(source, node, "newlist"))
    return out


def _fix_count_bug(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute):
                if left.func.attr == "count" and len(left.args) == 1:
                    call_obj = left.func.value
                    if isinstance(right, ast.Constant) and right.value == 1:
                        obj_s, obj_e = _span(source, call_obj)
                        arg_s, arg_e = _span(source, left.args[0])
                        new_cmp = source[obj_s:obj_e] + ".count(" + source[arg_s:arg_e] + ") == 0"
                        out.append(_splice(source, node, new_cmp))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "count" and len(node.args) == 1:
                pass
    return out


def _fix_not_in_seen_to_not_in_output(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
            right = node.comparators[0]
            if isinstance(right, ast.Name) and right.id == "seen":
                out.append(_splice(source, right, "output"))
    return out


def _fix_not_in_lst_to_not_in_newlist(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
            right = node.comparators[0]
            if isinstance(right, ast.Name) and right.id == "lst":
                out.append(_splice(source, right, "newlist"))
    return out


def _fix_bad_new_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == "new":
            out.append(_splice(source, node, "new_list"))
    return out


def _fix_append_of_append_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = node.left
            right = node.right
            if isinstance(left, ast.Name) and isinstance(right, ast.Call):
                if isinstance(right.func, ast.Attribute) and right.func.attr == "append":
                    if isinstance(right.func.value, ast.Name) and right.func.value.id in {"new", "new_list", "remove_lst", "output"}:
                        arg = right.args[0] if right.args else None
                        if arg is not None:
                            ls, le = _span(source, left)
                            as_, ae = _span(source, arg)
                            new_text = source[ls:le] + ".append(" + source[as_:ae] + ")"
                            out.append(_splice(source, node, new_text))
    return out


def _fix_lst_not_in_newlist(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and left.id in {"lst", "values"} and isinstance(right, ast.Name):
                if right.id == "new":
                    out.append(_splice(source, right, "new_list"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="use_accumulator_in_membership_test",
                apply=lambda s: _replace_name_load(s, "lst", "newlist"),
                symptoms=("wrong",),
            ),
            Rule(
                name="use_accumulator_in_membership_test_alt",
                apply=lambda s: _fix_not_in_seen_to_not_in_output(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="use_accumulator_in_membership_test_newlist",
                apply=lambda s: _fix_not_in_lst_to_not_in_newlist(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_count_threshold_to_zero",
                apply=lambda s: _fix_count_bug(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="replace_set_return_with_list_builder",
                apply=lambda s: _replace_set_return(s),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_bad_new_identifier",
                apply=lambda s: _fix_bad_new_name(s),
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="fix_append_expression",
                apply=lambda s: _fix_append_of_append_return(s),
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="fix_compare_to_output_list",
                apply=lambda s: _replace_name_load(s, "seen", "newlist"),
                symptoms=("wrong",),
            ),
        ]