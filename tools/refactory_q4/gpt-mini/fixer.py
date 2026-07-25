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


def _replace_node(source, target, new_text):
    return _splice(source, target, new_text)


def _compare_op_spans(source, compare_node):
    left = compare_node.left
    right = compare_node.comparators[0]
    ls, le = _span(source, left)
    rs, re = _span(source, right)
    return ls, le, rs, re


def _rule_empty_list_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Eq) and isinstance(node.comparators[0], ast.Tuple):
                tup = node.comparators[0]
                if len(tup.elts) == 0:
                    left = node.left
                    ls, le = _span(source, left)
                    ts, te = _span(source, tup)
                    out.append(_replace_node(source, node, source[ls:le] + " == []"))
            if isinstance(op, ast.Eq) and isinstance(node.comparators[0], ast.List):
                lst = node.comparators[0]
                if len(lst.elts) == 0:
                    left = node.left
                    ls, le = _span(source, left)
                    out.append(_replace_node(source, node, source[ls:le] + " == ()"))
    return out


def _rule_min_to_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "min" and len(node.args) == 1:
            arg = node.args[0]
            s, e = _span(source, node)
            as_, ae = _span(source, arg)
            out.append(source[s:as_] + "max" + source[as_:ae] + source[e:])
    return out


def _rule_max_to_min(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "max" and len(node.args) == 1:
            arg = node.args[0]
            s, e = _span(source, node)
            as_, ae = _span(source, arg)
            out.append(source[s:as_] + "min" + source[as_:ae] + source[e:])
    return out


def _rule_pop_noarg_to_pop0(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "pop" and len(node.args) == 0 and len(node.keywords) == 0:
                s, e = _span(source, node)
                out.append(source[s:e - 1] + "(0)")
    return out


def _rule_pop0_to_pop_noarg(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "pop" and len(node.args) == 1 and len(node.keywords) == 0:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and arg.value == 0:
                    s, e = _span(source, node)
                    out.append(source[s:e].replace("(0)", "()", 1))
    return out


def _rule_reverse_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            v = node.value.id
            s, e = _span(source, node)
            out.append(source[s:e].replace(v, f"{v}[::-1]", 1))
    return out


def _rule_swap_lt_gt_in_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le, rs, re = _compare_op_spans(source, node)
                out.append(source[:le] + " > " + source[rs:re] + source[re:])
            elif isinstance(node.ops[0], ast.Gt):
                left, right = node.left, node.comparators[0]
                ls, le, rs, re = _compare_op_spans(source, node)
                out.append(source[:le] + " < " + source[rs:re] + source[re:])
    return out


def _rule_add_reverse_before_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        rets = [n for n in func.body if isinstance(n, ast.Return)]
        if len(rets) == 1:
            ret = rets[0]
            if isinstance(ret.value, ast.Name):
                name = ret.value.id
                insert_at = _span(source, ret)[0]
                out.append(source[:insert_at] + f"{name}.reverse()\n    " + source[insert_at:])
    return out


def _rule_change_extend_reverse_to_reset(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            continue
        if isinstance(node, ast.Assign):
            continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "extend" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.List) and len(arg.elts) == 1:
                    elt = arg.elts[0]
                    if isinstance(elt, ast.Subscript):
                        s, e = _span(source, node)
                        out.append(source[s:e].replace("extend", "insert", 1))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="empty_list_check", apply=_rule_empty_list_check, symptoms=("wrong", "err:TypeError")),
            Rule(name="min_to_max", apply=_rule_min_to_max, symptoms=("wrong",)),
            Rule(name="max_to_min", apply=_rule_max_to_min, symptoms=("wrong",)),
            Rule(name="pop_noarg_to_pop0", apply=_rule_pop_noarg_to_pop0, symptoms=("wrong", "timeout")),
            Rule(name="pop0_to_pop_noarg", apply=_rule_pop0_to_pop_noarg, symptoms=("wrong",)),
            Rule(name="reverse_return", apply=_rule_reverse_return, symptoms=("wrong",)),
            Rule(name="swap_compare_direction", apply=_rule_swap_lt_gt_in_compare, symptoms=("wrong",)),
            Rule(name="reverse_before_return", apply=_rule_add_reverse_before_return, symptoms=("wrong",)),
            Rule(name="extend_to_insert_slip", apply=_rule_change_extend_reverse_to_reset, symptoms=("wrong",)),
        ]