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


def _replace_node(source, old_node, new_node_src):
    return _splice(source, old_node, new_node_src)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="empty_sequence_returns_zero",
                symptoms=("wrong", "err:IndexError"),
                apply=self._empty_sequence_returns_zero,
            ),
            Rule(
                name="strict_ge_tail_should_use_gt_len",
                symptoms=("wrong",),
                apply=self._fix_tail_ge_and_return_len,
            ),
            Rule(
                name="strict_lt_should_be_lte_in_search",
                symptoms=("wrong",),
                apply=self._lt_to_lte,
            ),
            Rule(
                name="return_len_minus_one_to_len",
                symptoms=("wrong",),
                apply=self._return_len_minus_one_to_len,
            ),
            Rule(
                name="return_none_or_false_to_zero_for_empty_search",
                symptoms=("wrong",),
                apply=self._empty_return_fix,
            ),
            Rule(
                name="missing_final_return_len",
                symptoms=("wrong",),
                apply=self._add_final_return_len,
            ),
            Rule(
                name="off_by_one_range_upper_bound",
                symptoms=("wrong",),
                apply=self._range_upper_bound_fix,
            ),
            Rule(
                name="while_condition_membership_bug",
                symptoms=("wrong", "timeout"),
                apply=self._while_membership_fix,
            ),
            Rule(
                name="wrong_variable_in_comparison_or_return",
                symptoms=("wrong",),
                apply=self._wrong_name_fixes,
            ),
            Rule(
                name="comparison_chain_boundary_fix",
                symptoms=("wrong",),
                apply=self._boundary_chain_fix,
            ),
            Rule(
                name="loop_else_return_len",
                symptoms=("wrong",),
                apply=self._loop_else_return_len,
            ),
        ]

    def _parse(self, source):
        try:
            return ast.parse(source)
        except SyntaxError:
            return None

    def _empty_sequence_returns_zero(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = ast.get_source_segment(source, node.test) or ""
                if any(k in txt for k in ("seq == ()", "seq == []", "not seq", "len(seq) == 0", "len(seq)==0")):
                    body = node.body
                    if body and isinstance(body[0], ast.Return):
                        seg = ast.get_source_segment(source, body[0].value) or ""
                        if seg.strip() in ("None", "False", "()", "seq", "[x]", "[]"):
                            out.append(_replace_node(source, body[0].value, "0"))
        return out

    def _fix_tail_ge_and_return_len(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                seg = ast.get_source_segment(source, node)
                if seg and "seq[-1]" in seg and "x" in seg:
                    out.append(_replace_node(source, node, seg.replace(">=", ">")))
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node.value) or ""
                if seg.strip() in ("i", "i+1", "i + 1", "len(seq)-1", "len(seq) - 1", "seq.index(seq[-1]) + 1"):
                    out.append(_replace_node(source, node.value, "len(seq)"))
        return out

    def _lt_to_lte(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                seg = ast.get_source_segment(source, node)
                if seg:
                    out.append(_replace_node(source, node, seg.replace("<", "<=" , 1)))
        return out

    def _return_len_minus_one_to_len(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node.value) or ""
                if "len(seq)-1" in seg.replace(" ", "") or "len(seq) - 1" in seg:
                    out.append(_replace_node(source, node.value, "len(seq)"))
        return out

    def _empty_return_fix(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node.value) or ""
                if seg.strip() in ("None", "False", "seq", "()", "[x]", "[]"):
                    out.append(_replace_node(source, node.value, "0"))
        return out

    def _add_final_return_len(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            if fn.name != "search" or not fn.body:
                continue
            last = fn.body[-1]
            if isinstance(last, ast.Expr) and isinstance(last.value, ast.Constant) and isinstance(last.value.value, str):
                insert_at = _span(source, last)[1]
                out.append(source[:insert_at] + "\n    return len(seq)" + source[insert_at:])
            elif not isinstance(last, ast.Return):
                insert_at = _span(source, last)[1]
                out.append(source[:insert_at] + "\n    return len(seq)" + source[insert_at:])
        return out

    def _range_upper_bound_fix(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                seg = ast.get_source_segment(source, node)
                if seg and "len(seq)-1" in seg.replace(" ", ""):
                    out.append(_replace_node(source, node, seg.replace("len(seq)-1", "len(seq)")))
        return out

    def _while_membership_fix(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                seg = ast.get_source_segment(source, node.test) or ""
                if " in range(" in seg:
                    out.append(_replace_node(source, node.test, seg.replace(" in range(", " < ").replace(")", "", 1)))
        return out

    def _wrong_name_fixes(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                seg = ast.get_source_segment(source, node) or ""
                if "seq == 0" in seg:
                    out.append(_replace_node(source, node, seg.replace("seq == 0", "seq == []")))
                if "newseq[-1] < x" in seg and "newseq" in seg:
                    out.append(_replace_node(source, node, seg.replace("newseq[-1]", "seq[-1]").replace("len(newseq)", "len(seq)")))
                if "x <= elem" in seg and "else" in source:
                    pass
            if isinstance(node, ast.Name):
                if node.id in ("ele", "eleme", "list1"):
                    out.append(_replace_node(source, node, {"ele": "elem", "eleme": "elem", "list1": "seq"}[node.id]))
        return out

    def _boundary_chain_fix(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                seg = ast.get_source_segment(source, node) or ""
                if "x <= seq[0] or seq == 0" in seg:
                    out.append(_replace_node(source, node, seg.replace("seq == 0", "seq == []")))
                if "x < seq[0]" in seg and "elif" not in seg:
                    out.append(_replace_node(source, node, seg.replace("<", "<=")))
        return out

    def _loop_else_return_len(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            if fn.name != "search":
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.For):
                    if node.orelse:
                        continue
                    if node.body and isinstance(node.body[-1], ast.Return):
                        continue
                    insert_at = _span(source, node)[1]
                    out.append(source[:insert_at] + "\n    return len(seq)" + source[insert_at:])
                    break
        return out