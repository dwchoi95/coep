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


def _replace_node(source, old, new_node):
    return _splice(source, old, ast.get_source_segment(source, new_node))


def _lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left is None or right is None:
                continue
            out.append(_splice(source, node, f"{left} <= {right}"))
    return out


def _ge_to_gt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left is None or right is None:
                continue
            out.append(_splice(source, node, f"{left} > {right}"))
    return out


def _gt_to_ge(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left is None or right is None:
                continue
            out.append(_splice(source, node, f"{left} >= {right}"))
    return out


def _return_none_to_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is None:
            out.append(_splice(source, node, "return 0"))
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            out.append(_splice(source, node, "return 0"))
    return out


def _return_none_to_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is None:
            out.append(_splice(source, node, "return len(seq)"))
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            out.append(_splice(source, node, "return len(seq)"))
    return out


def _return_in_for_to_else(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and node.body:
            last = node.body[-1]
            if isinstance(last, ast.Return):
                txt = ast.get_source_segment(source, last)
                if txt is None:
                    continue
                prefix = source[_span(source, node)[0]:_span(source, last)[0]]
                suffix = source[_span(source, last)[1]:_span(source, node)[1]]
                out.append(source[:_span(source, node)[0]] + prefix + suffix + source[_span(source, node)[1]:])
    return out


def _range_len_plus1_to_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                left = ast.get_source_segment(source, arg.left)
                right = ast.get_source_segment(source, arg.right)
                if left == "len(seq)" and right == "1":
                    out.append(_splice(source, arg, "len(seq)"))
                if right == "len(seq)" and left == "1":
                    out.append(_splice(source, arg, "len(seq)"))
    return out


def _return_stmt_to_break(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            out.append(_splice(source, node, "break"))
    return out


def _index_method_to_direct_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "index":
            if len(node.args) == 1:
                obj = ast.get_source_segment(source, node.func.value)
                arg = ast.get_source_segment(source, node.args[0])
                if obj is not None and arg is not None:
                    out.append(_splice(source, node, f"{obj}.index({arg})"))
    return out


def _eq_empty_to_len_empty(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left in {"seq", "list(seq)"} and right in {"[]", "()"}:
                out.append(_splice(source, node, "len(seq) == 0"))
            elif right in {"seq", "list(seq)"} and left in {"[]", "()"}:
                out.append(_splice(source, node, "len(seq) == 0"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="strict_lt_should_be_lte", apply=_lt_to_le, symptoms=("wrong", "timeout")),
            Rule(name="ge_bound_should_be_gt", apply=_ge_to_gt, symptoms=("wrong",)),
            Rule(name="gt_bound_should_be_gte", apply=_gt_to_ge, symptoms=("wrong",)),
            Rule(name="return_none_should_be_zero", apply=_return_none_to_zero, symptoms=("wrong", "err:TypeError")),
            Rule(name="return_none_should_be_len", apply=_return_none_to_len, symptoms=("wrong",)),
            Rule(name="premature_return_in_loop_should_fallthrough", apply=_return_in_for_to_else, symptoms=("wrong",)),
            Rule(name="range_len_plus_one_off_by_one", apply=_range_len_plus1_to_len, symptoms=("wrong", "timeout")),
            Rule(name="return_stmt_inside_loop_should_break", apply=_return_stmt_to_break, symptoms=("wrong",)),
            Rule(name="use_direct_index_instead_of_value_index", apply=_index_method_to_direct_index, symptoms=("wrong",)),
            Rule(name="empty_sequence_check_should_use_len", apply=_eq_empty_to_len_empty, symptoms=("wrong",)),
        ]