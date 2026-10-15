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


def _replace_node(source, old, new):
    return _splice(source, old, ast.get_source_segment(source, new))


def _replace_expr(source, old, new_text):
    return _splice(source, old, new_text)


def _compare_eq_to_lt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            out.append(_splice(source, node, f"{left} < {right}"))
    return out


def _compare_le_to_lt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            out.append(_splice(source, node, f"{left} < {right}"))
    return out


def _compare_lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            out.append(_splice(source, node, f"{left} <= {right}"))
    return out


def _wrong_max_index_to_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            seg = ast.get_source_segment(source, node.value)
            if seg and ("index(max(" in seg or "index(max(seq))" in seg) and "+ 1" in seg:
                new = seg.replace("list(seq).index(max(seq))+1", "len(seq)")
                new = new.replace("list(seq).index(max(seq)))+1", "len(seq)")
                new = new.replace("(list(seq).index(max(seq)))+1", "len(seq)")
                out.append(_splice(source, node.value, new))
    return out


def _seq_len_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left in ("list(seq)", "seq") and right == "[]":
                out.append(_splice(source, node, "len(seq) == 0"))
            elif left == "[]" and right in ("list(seq)", "seq"):
                out.append(_splice(source, node, "len(seq) == 0"))
    return out


def _replace_seq_last_with_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left == "seq[-1]" and right == "x":
                out.append(_splice(source, node, "seq[-1] < x"))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            left = ast.get_source_segment(source, node.left)
            right = ast.get_source_segment(source, node.comparators[0])
            if left == "x" and right == "start":
                out.append(_splice(source, node, "x <= start"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="empty_sequence_check_to_len_zero",
                apply=_seq_len_zero,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="strict_equality_misused_for_ordering",
                apply=_compare_eq_to_lt,
                symptoms=("wrong",),
            ),
            Rule(
                name="less_equal_should_be_less",
                apply=_compare_le_to_lt,
                symptoms=("wrong",),
            ),
            Rule(
                name="less_should_be_less_equal",
                apply=_compare_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_max_index_returned_instead_of_len",
                apply=_wrong_max_index_to_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="use_last_element_instead_of_nonexistent_name",
                apply=_replace_seq_last_with_len,
                symptoms=("err:NameError",),
            ),
        ]