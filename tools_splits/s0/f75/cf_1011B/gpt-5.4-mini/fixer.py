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


def _replace_constant(source, target_value, new_value):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == target_value:
            s, e = _span(source, node)
            candidate = source[:s] + str(new_value) + source[e:]
            if candidate != source and candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
    return out


def _change_compare_constant(source, old_value, new_value):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            comp = node.comparators[0]
            if isinstance(comp, ast.Constant) and comp.value == old_value:
                s, e = _span(source, comp)
                candidate = source[:s] + str(new_value) + source[e:]
                if candidate != source and candidate not in seen:
                    seen.add(candidate)
                    out.append(candidate)
    return out


def _range_upper_plus_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) >= 1:
            last = node.args[-1]
            s, e = _span(source, last)
            candidate = source[:s] + f"({source[s:e]}) + 1" + source[e:]
            if candidate != source and candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
    return out


def _lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            candidate = source[:ls] + source[ls:le] + " <= " + source[rs:re_] + source[re_:]
            if candidate != source and candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
    return out


def _fix_binary_search_upper_bound(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id == "r" and isinstance(node.value, ast.Constant) and node.value.value == 100:
                s, e = _span(source, node.value)
                candidate = source[:s] + "100000" + source[e:]
                if candidate != source and candidate not in seen:
                    seen.add(candidate)
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="binary_search_upper_bound_too_small",
                apply=_fix_binary_search_upper_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="constant_upper_bound_100_to_100000",
                apply=lambda s: _replace_constant(s, 100, 100000),
                symptoms=("wrong",),
            ),
            Rule(
                name="range_upper_bound_plus_one",
                apply=_range_upper_plus_one,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="strict_lt_to_le",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="compare_constant_1_to_0_or_2",
                apply=lambda s: _change_compare_constant(s, 1, 0) + _change_compare_constant(s, 1, 2),
                symptoms=("wrong",),
            ),
        ]