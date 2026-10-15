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


def _build_expr(source, node):
    return source[_span(source, node)[0]:_span(source, node)[1]]


def _range_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                left, right = arg.left, arg.right
                if isinstance(right, ast.Constant) and right.value == 1:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new_arg = source[ls:le]
                    out.append(_splice(source, node, "range(" + new_arg + ")"))
            elif isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                left, right = arg.left, arg.right
                if isinstance(right, ast.Constant) and right.value == 1:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new_arg = source[ls:le]
                    out.append(_splice(source, node, "range(" + new_arg + ")"))
    return out


def _wrong_return_list_to_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            name = node.value.id
            for parent in ast.walk(tree):
                if isinstance(parent, ast.FunctionDef):
                    body = parent.body
                    if node in body:
                        for stmt in body:
                            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                                call = stmt.value
                                if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
                                    if call.func.value.id == name and call.func.attr in ("append", "add", "extend"):
                                        return [_splice(source, node, f"return {name}") for _ in []]
    return out


def _max_instead_of_min(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "min" and len(node.args) == 1:
            out.append(_splice(source, node.func, "max"))
    return out


def _min_instead_of_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "max" and len(node.args) == 1:
            out.append(_splice(source, node.func, "min"))
    return out


def _plus_equals_to_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if isinstance(node.target, ast.Name):
                target = node.target.id
                rhs = node.value
                rs, re = _span(source, rhs)
                new = f"{target}.append({source[rs:re]})"
                out.append(_splice(source, node, new))
    return out


def _range_k_minus_one_to_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                ls, le = _span(source, arg.left)
                out.append(_splice(source, node, "range(" + source[ls:le] + ")"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="use_append_instead_of_plus_equals", apply=_plus_equals_to_append, symptoms=("wrong", "err:TypeError")),
            Rule(name="max_instead_of_min", apply=_max_instead_of_min, symptoms=("wrong", "timeout")),
            Rule(name="min_instead_of_max", apply=_min_instead_of_max, symptoms=("wrong", "timeout")),
            Rule(name="range_off_by_one", apply=_range_off_by_one, symptoms=("wrong",)),
            Rule(name="range_k_minus_one_to_k", apply=_range_k_minus_one_to_k, symptoms=("wrong",)),
        ]