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
        segment = ast.get_source_segment(source, new_node)
    except Exception:
        segment = None
    if segment is None:
        return None
    return _splice(source, target, segment)


def _digital_root_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = node.left
            right = node.comparators[0]
            if isinstance(right, ast.Constant) and right.value == 10:
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + " <= " + source[rs:re]
                out.append(_splice(source, node, new_cmp))
    return out


def _range_upper_to_inclusive(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2:
                a0, a1 = node.args
                if isinstance(a0, ast.Constant) and getattr(a0, "value", None) == 1:
                    if isinstance(a1, ast.Name):
                        s, e = _span(source, a1)
                        out.append(_splice(source, a1, source[s:e] + " + 1"))
    return out


def _less_to_less_equal(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re]
            out.append(_splice(source, node, new_cmp))
    return out


def _equal_to_not_equal(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            new_cmp = source[ls:le] + " != " + source[rs:re]
            out.append(_splice(source, node, new_cmp))
    return out


def _plus_one_to_plus_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if isinstance(node.right, ast.Constant) and node.right.value == 1:
                s, e = _span(source, node.right)
                out.append(source[:s] + "0" + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="digital_root_count_range_fix",
                apply=_range_upper_to_inclusive,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_to_le",
                apply=_less_to_less_equal,
                symptoms=("wrong",),
            ),
            Rule(
                name="eq_to_neq_miscount",
                apply=_equal_to_not_equal,
                symptoms=("wrong",),
            ),
            Rule(
                name="off_by_one_plus_one_to_zero",
                apply=_plus_one_to_plus_zero,
                symptoms=("wrong",),
            ),
        ]