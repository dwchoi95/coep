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


def _replace_node(source, target, replacement):
    s, e = _span(source, target)
    return source[:s] + replacement + source[e:]


def _make_add_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            out.append(_replace_node(source, node.op, "Sub()"))
    return out


def _fix_digit_root_pattern(source):
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
                new = _splice(source, node.ops[0], ">=")
                out.append(new)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            if isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 9:
                new = _splice(source, node.ops[0], "<")
                out.append(new)
    return out


def _range_upper_plus_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2 and isinstance(node.args[1], ast.BinOp) and isinstance(node.args[1].op, ast.Add):
                if isinstance(node.args[1].right, ast.Constant) and node.args[1].right.value == 1:
                    out.append(_replace_node(source, node.args[1], source[_span(source, node.args[1].left)[0]:_span(source, node.args[1].right)[1]]))
    return out


def _wrong_self_product_to_pair_product(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mult):
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_text = source[ls:le] + " != " + source[rs:re]
                out.append(_splice(source, node, new_text))
    return out


def _fix_mod_9_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Mod):
                if isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 9:
                    repl = source[_span(source, node.slice.left)[0]:_span(source, node.slice.left)[1]]
                    out.append(_replace_node(source, node.slice, repl))
    return out


def _fix_range_start(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2 and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                out.append(_replace_node(source, node.args[0], "1"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="digit_root_base_case_cmp", apply=_fix_digit_root_pattern, symptoms=("wrong",)),
            Rule(name="range_upper_off_by_one", apply=_range_upper_plus_one, symptoms=("wrong",)),
            Rule(name="self_product_miscompare", apply=_wrong_self_product_to_pair_product, symptoms=("wrong",)),
            Rule(name="mod_nine_indexing", apply=_fix_mod_9_index, symptoms=("wrong",)),
            Rule(name="range_start_one", apply=_fix_range_start, symptoms=("wrong",)),
            Rule(name="augadd_to_sub", apply=_make_add_rule, symptoms=("wrong",)),
        ]