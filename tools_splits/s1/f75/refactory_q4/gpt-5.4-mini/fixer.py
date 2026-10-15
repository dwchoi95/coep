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


def _replace_node(source, target, new_node):
    try:
        new_text = ast.get_source_segment(source, new_node)
    except Exception:
        return None
    if new_text is None:
        return None
    return _splice(source, target, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(name="fix_append_wrong_name", apply=_fix_append_wrong_name, symptoms=("wrong", "err:NameError")),
            Rule(name="fix_remove_misspelling", apply=_fix_remove_misspelling, symptoms=("wrong", "err:AttributeError")),
            Rule(name="fix_list_append_of_none", apply=_fix_list_append_of_none, symptoms=("wrong",)),
            Rule(name="fix_reverse_called", apply=_fix_reverse_called, symptoms=("wrong",)),
            Rule(name="fix_return_reverse_method", apply=_fix_return_reverse_method, symptoms=("wrong",)),
            Rule(name="fix_sort_call_with_key", apply=_fix_sort_call_with_key, symptoms=("wrong",)),
            Rule(name="fix_max_min_age_key", apply=_fix_max_min_age_key, symptoms=("wrong",)),
            Rule(name="fix_compare_age_vs_tuple", apply=_fix_compare_age_vs_tuple, symptoms=("wrong",)),
            Rule(name="fix_compare_reversed_operands", apply=_fix_compare_reversed_operands, symptoms=("wrong",)),
            Rule(name="fix_assignment_instead_of_update", apply=_fix_assignment_instead_of_update, symptoms=("wrong",)),
            Rule(name="fix_pop_argument", apply=_fix_pop_argument, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_remove_index_vs_element", apply=_fix_remove_index_vs_element, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_range_off_by_one", apply=_fix_range_off_by_one, symptoms=("wrong",)),
            Rule(name="fix_empty_tuple_check", apply=_fix_empty_tuple_check, symptoms=("wrong",)),
            Rule(name="fix_empty_list_check", apply=_fix_empty_list_check, symptoms=("wrong",)),
            Rule(name="fix_append_missing_return", apply=_fix_append_missing_return, symptoms=("wrong",)),
        ]


def _fix_append_wrong_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
            if isinstance(node.func.value, ast.Name) and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id in {"biggest", "oldest", "smallest", "largest", "curr", "i"}:
                    continue
                continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, ast.Name):
                    if arg.id in {"i", "j", "k", "x"}:
                        seg = ast.get_source_segment(source, arg)
                        if seg:
                            out.append(_splice(source, arg, "smallest"))
    return out


def _fix_remove_misspelling(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr not in {"remove", "append", "sort"}:
            if node.attr == "removal":
                s, e = _span(source, node)
                out.append(source[:s] + source[s:e].replace("removal", "remove") + source[e:])
    return out


def _fix_list_append_of_none(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    tgt = node.targets[0]
                    s1, e1 = _span(source, tgt)
                    s2, e2 = _span(source, call)
                    out.append(source[:s1] + source[s2:e2] + source[e1:])
    return out


def _fix_reverse_called(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "reverse":
            if isinstance(node.ctx, ast.Load):
                s, e = _span(source, node)
                out.append(source[:s] + "reverse()" + source[e:])
    return out


def _fix_return_reverse_method(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute) and node.value.attr == "reverse":
            s, e = _span(source, node.value)
            out.append(source[:s] + source[s:e].replace("reverse", "reverse()") + source[e:])
    return out


def _fix_sort_call_with_key(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
            if node.keywords:
                for kw in node.keywords:
                    if kw.arg == "key":
                        s, e = _span(source, kw.value)
                        out.append(source[:s] + "lambda p: p[1]" + source[e:])
    return out


def _fix_max_min_age_key(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"max", "min"}:
            if node.keywords:
                for kw in node.keywords:
                    if kw.arg == "key":
                        s, e = _span(source, kw.value)
                        out.append(source[:s] + "lambda p: p[1]" + source[e:])
    return out


def _fix_compare_age_vs_tuple(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.left, ast.Name) and node.left.id in {"i", "item", "element", "person", "x", "ele"}:
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"largest", "smallest", "oldest", "biggest", "largest_tup"}:
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    op = node.ops[0]
                    if isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                        out.append(source[:ls] + source[ls:le] + "[1]" + source[le:rs] + source[rs:re] + "[1]" + source[re:])
    return out


def _fix_compare_reversed_operands(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.left, ast.Subscript) and isinstance(node.comparators[0], ast.Name):
                op = node.ops[0]
                if isinstance(op, ast.Lt):
                    left = ast.get_source_segment(source, node.left)
                    right = ast.get_source_segment(source, node.comparators[0])
                    if left and right:
                        s, e = _span(source, node)
                        out.append(source[:s] + right + " > " + left + source[e:])
    return out


def _fix_assignment_instead_of_update(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in {"person", "i", "j", "x"} and node.value.id in {"oldest", "smallest", "largest", "biggest", "curr"}:
                    s, e = _span(source, node)
                    out.append(source[:s] + f"{node.value.id} = {node.targets[0].id}" + source[e:])
    return out


def _fix_pop_argument(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Subscript):
                s, e = _span(source, arg)
                out.append(source[:s] + source[_span(source, arg.value)[0]:_span(source, arg.value)[1]] + source[e:])
    return out


def _fix_remove_index_vs_element(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Name) and arg.id in {"i", "j", "k"}:
                continue
            if isinstance(arg, ast.Name):
                continue
    return out


def _fix_range_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2:
                a0, a1 = node.args
                if isinstance(a0, ast.Constant) and a0.value == 1 and isinstance(a1, ast.Call):
                    continue
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                    if isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                        s, e = _span(source, arg.right)
                        out.append(source[:s] + "0" + source[e:])
    return out


def _fix_empty_tuple_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.comparators[0], ast.Tuple) and len(node.comparators[0].elts) == 0:
                s, e = _span(source, node.comparators[0])
                out.append(source[:s] + "[]" + source[e:])
    return out


def _fix_empty_list_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.left, ast.Name):
                s, e = _span(source, node)
                txt = ast.get_source_segment(source, node)
                if txt and txt.strip() == f"{node.left.id} == ()":
                    out.append(source[:s] + f"{node.left.id} == []" + source[e:])
    return out


def _fix_append_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.body:
                last = node.body[-1]
                if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
                    call = last.value
                    if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                        s, e = _span(source, last)
                        out.append(source[:s] + source[s:e].replace(ast.get_source_segment(source, last), "return " + ast.get_source_segment(source, call.func.value) if isinstance(call.func.value, ast.Name) else "return None") + source[e:])
    return out