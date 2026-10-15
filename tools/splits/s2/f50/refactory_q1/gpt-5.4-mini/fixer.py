from src.core.repair import Rule
import ast


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


def _empty_returns_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            out.append(_splice(source, node, "return 0"))
    return out


def _lt_to_lte(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
            right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
            out.append(_splice(source, node, f"{left} <= {right}"))
    return out


def _gt_to_gte(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
            right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
            out.append(_splice(source, node, f"{left} >= {right}"))
    return out


def _range_n_to_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 1:
                a = node.args[0]
                txt = source[_span(source, a)[0]:_span(source, a)[1]]
                if txt.isidentifier():
                    out.append(_splice(source, node, f"range(len({txt}))"))
    return out


def _return_len_plus_one_to_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
            left, right = node.value.left, node.value.right
            if isinstance(right, ast.Constant) and right.value == 1:
                ltxt = source[_span(source, left)[0]:_span(source, left)[1]]
                if ltxt.startswith("len("):
                    out.append(_splice(source, node, f"return {ltxt}"))
    return out


def _if_return_none_to_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            out.append(_splice(source, node, "return 0"))
    return out


def _fix_empty_checks(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left = node.left
            right = node.comparators[0]
            ltxt = source[_span(source, left)[0]:_span(source, left)[1]]
            rtxt = source[_span(source, right)[0]:_span(source, right)[1]]
            if (ltxt in ("seq", "s", "lst", "seq ")) and isinstance(right, ast.Tuple) and len(right.elts) == 0:
                out.append(_splice(source, node, f"not {ltxt}"))
            if (ltxt in ("seq", "s", "lst", "new_seq", "a")) and isinstance(right, ast.List) and len(right.elts) == 0:
                out.append(_splice(source, node, f"not {ltxt}"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="empty_sequence_returns_zero", apply=_empty_returns_zero, symptoms=("wrong", "err:TypeError")),
            Rule(name="strict_lt_to_lte", apply=_lt_to_lte, symptoms=("wrong",)),
            Rule(name="strict_gt_to_gte", apply=_gt_to_gte, symptoms=("wrong",)),
            Rule(name="range_bound_to_len", apply=_range_n_to_len, symptoms=("wrong", "err:TypeError")),
            Rule(name="return_len_plus_one_to_len", apply=_return_len_plus_one_to_len, symptoms=("wrong",)),
            Rule(name="fix_empty_sequence_check", apply=_fix_empty_checks, symptoms=("wrong",)),
        ]