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
            out.append(_splice(source, n, new))
    return out


def _fix_count_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Gt):
                left, right = node.left, node.comparators[0]
                if isinstance(right, ast.Constant) and right.value == 1:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
            elif isinstance(op, ast.GtE):
                left, right = node.left, node.comparators[0]
                if isinstance(right, ast.Constant) and right.value == 2:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
            elif isinstance(op, ast.LtE):
                left, right = node.left, node.comparators[0]
                if isinstance(right, ast.Constant) and right.value == 1:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
    return out


def _fix_day_name_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "unique_day"]:
        params = [a.arg for a in func.args.args]
        if len(params) >= 1:
            day_param = params[0]
            for n in ast.walk(func):
                if isinstance(n, ast.Name) and n.id == "day":
                    out.append(_splice(source, n, day_param))
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and n.id == "count_dates":
                out.append(_splice(source, n, "count_dates"))
    return list(dict.fromkeys(out))


def _fix_unique_day_calls(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
            if len(node.args) >= 1 and isinstance(node.args[0], ast.Subscript):
                idx = node.args[0]
                if isinstance(idx.slice, ast.Constant) and idx.slice.value == 1:
                    continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
            if len(node.args) >= 1:
                arg = node.args[0]
                if isinstance(arg, ast.Subscript) and isinstance(arg.slice, ast.Constant) and arg.slice.value == 1:
                    continue
    return out


def _fix_contains_unique_day_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value in (True, False):
                pass
    return out


def _fix_common_ast(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "day":
            parents = []
            for p in ast.walk(tree):
                for c in ast.iter_child_nodes(p):
                    if c is node:
                        parents.append(p)
            if any(isinstance(p, ast.FunctionDef) and p.name == "unique_day" for p in parents):
                params = [a.arg for a in [p for p in parents if isinstance(p, ast.FunctionDef) and p.name == "unique_day"][0].args.args]
                if params:
                    out.append(_splice(source, node, params[0]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            right = node.comparators[0]
            if isinstance(right, ast.Constant) and right.value == 1:
                left = node.left
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
            right = node.comparators[0]
            if isinstance(right, ast.Constant) and right.value == 2:
                left = node.left
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            right = node.comparators[0]
            if isinstance(right, ast.Constant) and right.value == 1:
                left = node.left
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Subscript):
                sub = node.args[0]
                if isinstance(sub.slice, ast.Constant) and sub.slice.value == 1:
                    continue

    return list(dict.fromkeys(out))


class Fixer:
    def rules(self):
        return [
            Rule(name="compare_count_equality", apply=_fix_count_compare, symptoms=("wrong",)),
            Rule(name="unique_day_parameter_name", apply=_fix_day_name_mismatch, symptoms=("wrong",)),
            Rule(name="contains_unique_day_spelling", apply=_fix_common_ast, symptoms=("wrong",)),
        ]