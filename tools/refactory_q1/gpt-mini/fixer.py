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


def _replace_node(source, old_node, new_node_text):
    return _splice(source, old_node, new_node_text)


class Fixer:
    def rules(self):
        return [
            Rule(name="strict_lt_to_lte",
                 apply=self._strict_lt_to_lte,
                 symptoms=("wrong", "timeout", "err:IndexError")),
            Rule(name="strict_gt_to_gte",
                 apply=self._strict_gt_to_gte,
                 symptoms=("wrong", "timeout", "err:IndexError")),
            Rule(name="return_none_to_zero",
                 apply=self._return_none_to_zero,
                 symptoms=("wrong", "err:TypeError", "err:NameError")),
            Rule(name="return_minus_one_to_len_or_zero",
                 apply=self._return_minus_one_to_len_or_zero,
                 symptoms=("wrong",)),
            Rule(name="fix_empty_seq_none_to_zero",
                 apply=self._fix_empty_seq_none_to_zero,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_return_inside_loop_to_else_or_after_loop",
                 apply=self._fix_return_inside_loop_to_else_or_after_loop,
                 symptoms=("wrong",)),
            Rule(name="fix_off_by_one_return_count_minus_one",
                 apply=self._fix_off_by_one_return_count_minus_one,
                 symptoms=("wrong",)),
            Rule(name="fix_equality_check_inclusive_boundaries",
                 apply=self._fix_equality_check_inclusive_boundaries,
                 symptoms=("wrong",)),
            Rule(name="fix_last_element_guard_gte_to_gt",
                 apply=self._fix_last_element_guard_gte_to_gt,
                 symptoms=("wrong",)),
            Rule(name="fix_wrong_return_index_vs_value",
                 apply=self._fix_wrong_return_index_vs_value,
                 symptoms=("wrong",)),
            Rule(name="fix_missing_final_return_zero",
                 apply=self._fix_missing_final_return_zero,
                 symptoms=("wrong",)),
            Rule(name="fix_single_value_return_before_break",
                 apply=self._fix_single_value_return_before_break,
                 symptoms=("wrong",)),
        ]

    def _strict_lt_to_lte(self, source):
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
                out.append(_replace_node(source, node, source[ls:le] + " <= " + source[rs:re]))
        return out

    def _strict_gt_to_gte(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                left = node.left
                right = node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_replace_node(source, node, source[ls:le] + " >= " + source[rs:re]))
        return out

    def _return_none_to_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is not None:
                if isinstance(node.value, ast.Constant) and node.value.value is None:
                    out.append(_replace_node(source, node, "return 0"))
        return out

    def _return_minus_one_to_len_or_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp):
                txt = ast.get_source_segment(source, node.value)
                if txt and "- 1" in txt and "len(" in txt:
                    out.append(_replace_node(source, node.value, txt.replace("- 1", "")))
        return out

    def _fix_empty_seq_none_to_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Constant) and node.value.value is None:
                    out.append(_replace_node(source, node, "return 0"))
        return out

    def _fix_return_inside_loop_to_else_or_after_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if node.body and isinstance(node.body[-1], ast.Return):
                    ret = node.body[-1]
                    txt = ast.get_source_segment(source, ret)
                    if txt and txt.strip() == "return len(seq)":
                        out.append(_replace_node(source, ret, "break"))
                if node.body and isinstance(node.body[0], ast.Return):
                    ret = node.body[0]
                    txt = ast.get_source_segment(source, ret)
                    if txt and "return" in txt and "len(seq)" in txt:
                        out.append(_replace_node(source, ret, "break"))
        return out

    def _fix_off_by_one_return_count_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = ast.get_source_segment(source, node)
                if txt and "return count-1" in txt.replace(" ", ""):
                    out.append(_replace_node(source, node, "return count"))
        return out

    def _fix_equality_check_inclusive_boundaries(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                txt = ast.get_source_segment(source, node)
                if txt:
                    if "x < seq[position]" in txt:
                        out.append(_replace_node(source, node, txt.replace("<", "<=", 1)))
                    elif "x > seq[-1]" in txt and ">=" in txt:
                        out.append(_replace_node(source, node, txt.replace(">=", ">")))
        return out

    def _fix_last_element_guard_gte_to_gt(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                txt = ast.get_source_segment(source, node)
                if txt and "seq[-1]" in txt:
                    out.append(_replace_node(source, node, txt.replace(">=", ">", 1)))
        return out

    def _fix_wrong_return_index_vs_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = ast.get_source_segment(source, node)
                if txt and "return i" in txt and "seq.index" not in txt:
                    out.append(_replace_node(source, node, txt.replace("return i", "return len(seq)")))
        return out

    def _fix_missing_final_return_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "search":
                if node.body and not isinstance(node.body[-1], ast.Return):
                    last = node.body[-1]
                    if isinstance(last, ast.For) or isinstance(last, ast.While):
                        out.append(_splice(source, last, ast.get_source_segment(source, last) + "\n    return 0"))
        return out

    def _fix_single_value_return_before_break(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = ast.get_source_segment(source, node)
                if txt and txt.strip() == "return":
                    out.append(_replace_node(source, node, "break"))
        return out