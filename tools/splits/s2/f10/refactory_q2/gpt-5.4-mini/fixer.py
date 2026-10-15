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


def _replace_name_in_expr(source, expr, old, new):
    out = []
    for n in ast.walk(expr):
        if isinstance(n, ast.Name) and n.id == old:
            out.append((n, new))
    if len(out) != 1:
        return None
    n, new_name = out[0]
    return _splice(source, n, new_name)


def _fix_unique_day_eq_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unique_day"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left = node.left
                comp = node.comparators[0]
                if isinstance(left, ast.Subscript) and isinstance(comp, ast.Name) and comp.id in {"days", "day"}:
                    new_cmp = None
                    ls, le = _span(source, left)
                    rs, re = _span(source, comp)
                    new_cmp = source[ls:le] + " == " + "day"
                    out.append(_splice(source, node, new_cmp))
                elif isinstance(comp, ast.Subscript) and isinstance(left, ast.Name) and left.id in {"days", "day"}:
                    ls, le = _span(source, left)
                    rs, re = _span(source, comp)
                    new_cmp = "day" + " == " + source[rs:re]
                    out.append(_splice(source, node, new_cmp))
    return out


def _fix_unique_month_eq_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unique_month"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left = node.left
                comp = node.comparators[0]
                if isinstance(left, ast.Subscript) and isinstance(comp, ast.Name) and comp.id in {"month", "months"}:
                    ls, le = _span(source, left)
                    rs, re = _span(source, comp)
                    out.append(_splice(source, node, source[ls:le] + " == month"))
                elif isinstance(comp, ast.Subscript) and isinstance(left, ast.Name) and left.id in {"month", "months"}:
                    ls, le = _span(source, left)
                    rs, re = _span(source, comp)
                    out.append(_splice(source, node, "month" + " == " + source[rs:re]))
    return out


def _fix_contains_unique_day_call_arg(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
                if len(node.args) >= 2:
                    arg = node.args[1]
                    if isinstance(arg, ast.Name) and arg.id == "possible_birthdays":
                        new_call = source[_span(source, node.args[0])[0]:_span(source, node.args[0])[1]] + ", possible_birthdays"
                        out.append(_splice(source, node, f"unique_day({source[_span(source, node.args[0])[0]:_span(source, node.args[0])[1]]}, possible_birthdays)"))
                    elif isinstance(arg, ast.Name) and arg.id == "birthdays_month":
                        out.append(_splice(source, node, f"unique_day({source[_span(source, node.args[0])[0]:_span(source, node.args[0])[1]]}, possible_birthdays)"))
    return out


def _fix_contains_unique_day_self_filter(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
                if len(node.args) == 2:
                    second = node.args[1]
                    if isinstance(second, ast.Name) and second.id in {"birthdays_month", "months", "value", "x", "tup"}:
                        out.append(_splice(source, second, "possible_birthdays"))
    return out


def _fix_contains_unique_day_month_in_item(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                if isinstance(node.left, ast.Name) and node.left.id == "month":
                    out.append(_splice(source, node, "i[0] == month"))
    return out


def _fix_return_counter_eq1(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in {"unique_day", "unique_month"}:
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                    if isinstance(node.left, ast.Name) and node.left.id in {"count", "counter", "result", "num", "appearance"}:
                        out.append(_splice(source, node, f"{source[_span(source, node.left)[0]:_span(source, node.left)[1]]} == 1"))
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
                    if isinstance(node.left, ast.Name) and node.left.id in {"result", "count", "counter", "num", "appearance"}:
                        if len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 1:
                            out.append(_splice(source, node, f"{source[_span(source, node.left)[0]:_span(source, node.left)[1]]} == 1"))
    return out


def _fix_unique_month_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unique_month"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Subscript) and isinstance(node.left.slice, ast.Constant) and node.left.slice.value == 1:
                    out.append(_splice(source, node.left, source[_span(source, node.left.value)[0]:_span(source, node.left.value)[1]] + "[0]"))
                elif isinstance(node.comparators[0], ast.Subscript) and isinstance(node.comparators[0].slice, ast.Constant) and node.comparators[0].slice.value == 1:
                    out.append(_splice(source, node.comparators[0], source[_span(source, node.comparators[0].value)[0]:_span(source, node.comparators[0].value)[1]] + "[0]"))
    return out


def _fix_unique_day_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unique_day"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Subscript) and isinstance(node.left.slice, ast.Constant) and node.left.slice.value == 0:
                    out.append(_splice(source, node.left, source[_span(source, node.left.value)[0]:_span(source, node.left.value)[1]] + "[1]"))
                elif isinstance(node.comparators[0], ast.Subscript) and isinstance(node.comparators[0].slice, ast.Constant) and node.comparators[0].slice.value == 0:
                    out.append(_splice(source, node.comparators[0], source[_span(source, node.comparators[0].value)[0]:_span(source, node.comparators[0].value)[1]] + "[1]"))
    return out


def _fix_contains_unique_day_len_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                out.append(_splice(source, node.iter, "possible_birthdays"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="unique_day_compares_day_to_counter_name", apply=_fix_unique_day_eq_name, symptoms=("wrong",)),
            Rule(name="unique_month_compares_month_to_counter_name", apply=_fix_unique_month_eq_name, symptoms=("wrong",)),
            Rule(name="contains_unique_day_passes_filtered_collection_to_unique_day", apply=_fix_contains_unique_day_self_filter, symptoms=("wrong",)),
            Rule(name="contains_unique_day_use_possible_birthdays_in_call", apply=_fix_contains_unique_day_call_arg, symptoms=("wrong",)),
            Rule(name="contains_unique_day_month_membership_check", apply=_fix_contains_unique_day_month_in_item, symptoms=("wrong",)),
            Rule(name="unique_count_should_be_equality_one", apply=_fix_return_counter_eq1, symptoms=("wrong",)),
            Rule(name="unique_month_index_zero_instead_of_one", apply=_fix_unique_month_index, symptoms=("wrong",)),
            Rule(name="unique_day_index_one_instead_of_zero", apply=_fix_unique_day_index, symptoms=("wrong",)),
            Rule(name="contains_unique_day_range_loop_to_iterable", apply=_fix_contains_unique_day_len_loop, symptoms=("wrong",)),
        ]