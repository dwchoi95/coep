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


def _name(node):
    return isinstance(node, ast.Name)


def _subscript(node):
    return isinstance(node, ast.Subscript)


def _is_len_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
    )


def _counter_cmp_to_eq1(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Gt)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == 1
        ):
            new_text = source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " == 1"
            out.append(_replace_node(source, node, new_text))
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.GtE)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == 1
        ):
            new_text = source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " == 1"
            out.append(_replace_node(source, node, new_text))
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.LtE)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == 1
        ):
            new_text = source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " == 1"
            out.append(_replace_node(source, node, new_text))
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.NotEq)
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and node.comparators[0].value == 1
        ):
            new_text = source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " == 1"
            out.append(_replace_node(source, node, new_text))
    return out


def _fix_wrong_return_true(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is True:
            out.append(_replace_node(source, node, "return False"))
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is False:
            out.append(_replace_node(source, node, "return True"))
    return out


def _fix_unique_count_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"count", "counter", "total", "result", "number"}:
            out.append(_replace_node(source, node, f"return {node.value.id} == 1"))
    return out


def _fix_contains_return_false(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            for st in node.body:
                if isinstance(st, ast.For):
                    for inner in ast.walk(st):
                        if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Constant) and inner.value.value is False:
                            out.append(_replace_node(source, inner, "continue"))
    return out


def _fix_contains_unique_day_final_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            if node.body and isinstance(node.body[-1], ast.Return):
                ret = node.body[-1]
                if isinstance(ret.value, ast.Constant) and ret.value.value is True:
                    out.append(_replace_node(source, ret, "return False"))
                if isinstance(ret.value, ast.Name) and ret.value.id in {"false", "False"}:
                    out.append(_replace_node(source, ret, "return False"))
    return out


def _fix_bad_unique_day_call_arg(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "unique_day"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Subscript)
        ):
            arg = node.args[0]
            if isinstance(arg.slice, ast.Constant) and arg.slice.value == 0:
                s, e = _span(source, arg)
                out.append(_splice(source, arg, source[s:e].replace("[0]", "[1]")))
    return out


def _fix_day_month_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            if node.slice.value == 0:
                s, e = _span(source, node.slice)
                out.append(source[:s] + "1" + source[e:])
            elif node.slice.value == 1:
                pass
    return out


def _fix_unique_day_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Subscript):
                if isinstance(right.slice, ast.Constant) and right.slice.value in {0, 1}:
                    if right.slice.value == 0:
                        s, e = _span(source, right.slice)
                        out.append(source[:s] + "1" + source[e:])
    return out


def _fix_return_unique_day_bool(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"r", "tf"}:
            out.append(_replace_node(source, node, f"return {node.value.id}"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="count_should_equal_one", apply=_counter_cmp_to_eq1, symptoms=("wrong",)),
            Rule(name="return_true_false_literals", apply=_fix_wrong_return_true, symptoms=("wrong",)),
            Rule(name="return_counter_as_boolean", apply=_fix_unique_count_return, symptoms=("wrong",)),
            Rule(name="contains_unique_day_needs_false_fallthrough", apply=_fix_contains_return_false, symptoms=("wrong",)),
            Rule(name="contains_unique_day_final_false", apply=_fix_contains_unique_day_final_return, symptoms=("wrong",)),
            Rule(name="unique_day_call_should_use_day_field", apply=_fix_bad_unique_day_call_arg, symptoms=("wrong",)),
            Rule(name="subscript_zero_to_one", apply=_fix_day_month_index, symptoms=("wrong",)),
            Rule(name="contains_unique_day_return_flag", apply=_fix_return_unique_day_bool, symptoms=("wrong",)),
        ]