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


def _replace_node(source, target, replacement):
    return _splice(source, target, replacement)


class Fixer:
    def rules(self):
        return [
            Rule("add_empty_seq_guard", self._add_empty_seq_guard, ("wrong", "err:IndexError")),
            Rule("fix_len_zero_check", self._fix_len_zero_check, ("wrong", "err:IndexError")),
            Rule("fix_strict_upper_bound", self._fix_strict_upper_bound, ("wrong",)),
            Rule("fix_return_none_in_loop", self._fix_return_none_in_loop, ("wrong",)),
            Rule("fix_return_zero_on_empty", self._fix_return_zero_on_empty, ("wrong",)),
            Rule("fix_return_len_minus_one", self._fix_return_len_minus_one, ("wrong",)),
            Rule("fix_return_i_plus_one_to_len", self._fix_return_i_plus_one_to_len, ("wrong",)),
            Rule("fix_return_i_plus_one_to_len_inside_loop", self._fix_return_i_plus_one_to_len_inside_loop, ("wrong",)),
            Rule("fix_wrong_bare_return", self._fix_wrong_bare_return, ("wrong",)),
            Rule("fix_compare_operator_lt_to_lte", self._fix_compare_operator_lt_to_lte, ("wrong",)),
            Rule("fix_compare_operator_gte_to_gt", self._fix_compare_operator_gte_to_gt, ("wrong",)),
            Rule("fix_compare_operator_gt_to_gte", self._fix_compare_operator_gt_to_gte, ("wrong",)),
            Rule("fix_loop_bound_minus_one", self._fix_loop_bound_minus_one, ("wrong",)),
            Rule("fix_range_len_call", self._fix_range_len_call, ("err:TypeError",)),
            Rule("fix_name_indexing_brackets", self._fix_name_indexing_brackets, ("err:TypeError",)),
            Rule("fix_missing_else_continue", self._fix_missing_else_continue, ("wrong",)),
            Rule("fix_break_instead_of_return", self._fix_break_instead_of_return, ("wrong",)),
        ]

    def _add_empty_seq_guard(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            if not fn.body or not isinstance(fn.body[0], ast.If):
                continue
            first = fn.body[0]
            txt = ast.get_source_segment(source, first.test) or ""
            if "seq == () or seq == []" in txt or "seq == [] or seq == ()" in txt or "seq == () or []" in txt or "seq == () and []" in txt:
                continue
            for node in ast.walk(first.test):
                if isinstance(node, ast.Compare):
                    seg = ast.get_source_segment(source, node) or ""
                    if "seq == ()" in seg and "seq == []" not in seg:
                        out.append(_replace_node(source, node, seg + " or seq == []"))
                        break
        return out

    def _fix_len_zero_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                seg = ast.get_source_segment(source, node) or ""
                if "len(seq) == 0" in seg or "len(seq)==0" in seg:
                    continue
                if "seq == ()" in seg and "or seq == []" not in seg:
                    out.append(_replace_node(source, node, "len(seq) == 0"))
        return out

    def _fix_strict_upper_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
                seg = ast.get_source_segment(source, node) or ""
                if "seq[-1]" in seg or "seq[len(seq)-1]" in seg:
                    out.append(_replace_node(source, node, seg.replace("<=", ">")))
        return out

    def _fix_return_none_in_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                out.append(_splice(source, node, "return len(seq)"))
        return out

    def _fix_return_zero_on_empty(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value == 1:
                out.append(_splice(source, node, "return 0"))
        return out

    def _fix_return_len_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if "len(seq)-1" in seg.replace(" ", ""):
                    out.append(_splice(source, node, "return len(seq)"))
        return out

    def _fix_return_i_plus_one_to_len(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if "i + 1" in seg or "i+1" in seg:
                    out.append(_splice(source, node, "return len(seq)"))
        return out

    def _fix_return_i_plus_one_to_len_inside_loop(self, source):
        return self._fix_return_i_plus_one_to_len(source)

    def _fix_wrong_bare_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                out.append(_splice(source, node, "return len(seq)"))
        return out

    def _fix_compare_operator_lt_to_lte(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                seg = ast.get_source_segment(source, node)
                if seg and "x <" in seg and "seq" in seg:
                    out.append(_splice(source, node, seg.replace("<", "<=", 1)))
        return out

    def _fix_compare_operator_gte_to_gt(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                seg = ast.get_source_segment(source, node) or ""
                if "seq[-1]" in seg or "seq[len(seq)-1]" in seg:
                    out.append(_splice(source, node, seg.replace(">=", ">")))
        return out

    def _fix_compare_operator_gt_to_gte(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                seg = ast.get_source_segment(source, node) or ""
                if "seq[i]" in seg or "elem" in seg or "element" in seg:
                    out.append(_splice(source, node, seg.replace(">", "<=", 1)))
        return out

    def _fix_loop_bound_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                seg = ast.get_source_segment(source, node) or ""
                if "len(seq)-1" in seg.replace(" ", ""):
                    out.append(_splice(source, node, seg.replace("len(seq)-1", "len(seq)")))
        return out

    def _fix_range_len_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                seg = ast.get_source_segment(source, node) or ""
                if "len(range(seq))" in seg.replace(" ", ""):
                    out.append(_splice(source, node, "range(len(seq))"))
        return out

    def _fix_name_indexing_brackets(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                seg = ast.get_source_segment(source, node) or ""
                if node.value.id in {"seq", "list", "seq"} and "[" in seg and "]" in seg:
                    continue
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                seg = ast.get_source_segment(source, node) or ""
                if node.func.id == "len" and "len[i]" in seg:
                    out.append(_splice(source, node, "seq[i]"))
                if node.func.id == "enumerate" and "seq(i)" in seg:
                    out.append(_splice(source, node, "seq[i]"))
        return out

    def _fix_missing_else_continue(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                    seg = ast.get_source_segment(source, node.test) or ""
                    if "x > elem" in seg and "continue" not in ast.get_source_segment(source, node)[:50]:
                        out.append(_splice(source, node.body[0], "continue"))
        return out

    def _fix_break_instead_of_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Break):
                out.append(_splice(source, node, "return i"))
        return out