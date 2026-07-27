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


def _const_int(node, value):
    return isinstance(node, ast.Constant) and node.value == value and isinstance(node.value, int)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="off_by_one_range_or_while_bound",
                apply=self._off_by_one_bound,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="slice_result_by_k_not_constant",
                apply=self._fix_constant_slice,
                symptoms=("wrong",),
            ),
            Rule(
                name="append_and_remove_with_function_call_not_subscript",
                apply=self._fix_call_brackets,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="remove_extra_final_element_in_loop",
                apply=self._drop_extra_iteration,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="return_built_result_not_input",
                apply=self._return_result_not_lst,
                symptoms=("wrong",),
            ),
            Rule(
                name="compare_list_item_to_max_not_index",
                apply=self._fix_index_vs_value_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_recursive_variable_name",
                apply=self._fix_recursive_call_name,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="missing_remove_in_max_loop",
                apply=self._add_remove_after_max,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="missing_k_zero_guard",
                apply=self._add_k_zero_guard,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_nested_loop_bound_or_index",
                apply=self._fix_nested_loop_swap_sort,
                symptoms=("wrong",),
            ),
            Rule(
                name="append_max_then_return_prefix_k",
                apply=self._fix_return_prefix_and_k,
                symptoms=("wrong",),
            ),
            Rule(
                name="reset_while_condition_to_strict",
                apply=self._fix_while_non_strict,
                symptoms=("wrong", "timeout"),
            ),
        ]

    def _off_by_one_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, ast.LtE):
                    left, right = node.left, node.comparators[0]
                    seg = ast.get_source_segment(source, node)
                    if seg:
                        out.append(_splice(source, node, seg.replace("<=", "<", 1)))
                elif isinstance(op, ast.GtE):
                    seg = ast.get_source_segment(source, node)
                    if seg:
                        out.append(_splice(source, node, seg.replace(">=", ">", 1)))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                args = node.args
                if len(args) == 1 and _const_int(args[0], 0):
                    continue
                if len(args) == 1:
                    seg = ast.get_source_segment(source, node)
                    if seg and "range(" in seg and seg.endswith(")"):
                        out.append(_splice(source, node, seg[:-1] + " + 1)"))
        return out

    def _fix_constant_slice(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                sl = node.slice
                if _const_int(sl.lower, 0) and sl.upper and _const_int(sl.upper, 5):
                    seg = ast.get_source_segment(source, node)
                    if seg:
                        out.append(_splice(source, node, seg.replace(":5", ":k", 1)))
                if _const_int(sl.lower, 0) and sl.upper is not None and ast.get_source_segment(source, sl.upper) == "k-1":
                    seg = ast.get_source_segment(source, node)
                    if seg:
                        out.append(_splice(source, node, seg.replace("k-1", "k", 1)))
        return out

    def _fix_call_brackets(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                if node.value.id in {"rs", "result", "newlist", "op"}:
                    seg = ast.get_source_segment(source, node)
                    if seg and "[" in seg and "]" in seg:
                        out.append(_splice(source, node, seg.replace("[", "(", 1).replace("]", ")", 1)))
        return out

    def _drop_extra_iteration(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
                seg = ast.get_source_segment(source, node)
                if seg and "counter <= k" in seg:
                    out.append(_splice(source, node, seg.replace("<= k", "< k", 1)))
                if seg and "len(l) <= k" in seg:
                    out.append(_splice(source, node, seg.replace("<= k", "< k", 1)))
                if seg and "while k >= 0" in seg:
                    out.append(_splice(source, node, seg.replace(">= 0", "> 0", 1)))
        return out

    def _return_result_not_lst(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "lst":
                out.append(_splice(source, node, "return result"))
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "r":
                out.append(_splice(source, node, "return rs"))
        return out

    def _fix_index_vs_value_compare(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Name) and node.left.id == "i":
                    seg = ast.get_source_segment(source, node)
                    if seg and "i ==" in seg:
                        out.append(_splice(source, node, seg.replace("i", "lst[i]", 1)))
        return out

    def _fix_recursive_call_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "top_k":
                if len(node.args) == 2:
                    arg2 = node.args[1]
                    if isinstance(arg2, ast.BinOp) and isinstance(arg2.op, ast.Sub):
                        seg = ast.get_source_segment(source, node)
                        if seg and "new_lst" in seg:
                            out.append(_splice(source, node, seg.replace("new_lst", "new_list", 1)))
        return out

    def _add_remove_after_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "max":
                    parent = ast.get_source_segment(source, node)
                    if parent and "max(lst)" in parent:
                        out.append(_splice(source, node, parent + "\n            lst.remove(element)"))
        return out

    def _add_k_zero_guard(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                if isinstance(node.test.ops[0], ast.Eq):
                    seg = ast.get_source_segment(source, node.test)
                    if seg and "lst == []" in seg and "k == 0" not in seg:
                        out.append(_splice(source, node.test, seg.replace("lst == []", "lst == [] or k == 0", 1)))
        return out

    def _fix_nested_loop_swap_sort(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                seg = ast.get_source_segment(source, node)
                if seg == "lst[1]" or seg == "lst[1+i]":
                    out.append(_splice(source, node, "lst[i+1]"))
        return out

    def _fix_return_prefix_and_k(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                seg = ast.get_source_segment(source, node)
                if seg and "return result[:k]" not in seg:
                    out.append(_splice(source, node, "return result[:k]"))
                if seg and "return tmp[:5]" in seg:
                    out.append(_splice(source, node, "return tmp[:k]"))
        return out

    def _fix_while_non_strict(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                if isinstance(node.test.ops[0], ast.GtE):
                    seg = ast.get_source_segment(source, node.test)
                    if seg and "while k >= 0" in seg:
                        out.append(_splice(source, node.test, seg.replace(">= 0", "> 0", 1)))
                if isinstance(node.test.ops[0], ast.LtE):
                    seg = ast.get_source_segment(source, node.test)
                    if seg and "while len(newlist) < k" in seg:
                        continue
        return out