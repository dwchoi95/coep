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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="return_inside_loop_should_be_after_loop",
                apply=self._return_inside_loop_should_be_after_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_to_lte_in_search_comparison",
                apply=self._strict_lt_to_lte,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_to_gte_in_counting_search",
                apply=self._strict_gt_to_gte_counter,
                symptoms=("wrong",),
            ),
            Rule(
                name="else_returns_len_inside_loop_should_be_loop_else",
                apply=self._loop_else_return_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_return_value_should_be_index_not_x_or_sequence",
                apply=self._wrong_return_value,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_bound_off_by_one_extend_to_len_plus_one",
                apply=self._range_len_to_len_plus_one,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="return_len_plus_one_should_be_len",
                apply=self._return_len_plus_one_to_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="empty_sequence_check_should_be_len_zero_or_not_seq",
                apply=self._empty_check_fix,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="break_then_return_i_should_return_len",
                apply=self._break_return_i_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_none_on_empty_should_return_zero",
                apply=self._none_on_empty_fix,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="loop_variable_mismatch_should_use_return_counter",
                apply=self._loop_var_mismatch_counter,
                symptoms=("wrong",),
            ),
        ]

    def _parse(self, source):
        try:
            return ast.parse(source)
        except SyntaxError:
            return None

    def _strict_lt_to_lte(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.comparators[0])
                out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re]))
        return out

    def _return_inside_loop_should_be_after_loop(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for idx, stmt in enumerate(func.body[:-1]):
                if isinstance(stmt, ast.For) and len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Return):
                    ret = stmt.body[0]
                    if not isinstance(func.body[idx + 1], ast.Return):
                        new_for = source[_span(source, stmt)[0]:_span(source, stmt)[1]]
                        tail = source[_span(source, ret)[0]:_span(source, ret)[1]]
                        repl = source[_span(source, stmt)[0]:_span(source, ret)[1]].replace(
                            source[_span(source, ret)[0]:_span(source, ret)[1]], ""
                        )
                        # remove return from loop body by splicing the return out only
                        out.append(_splice(source, ret, ""))
        return out

    def _loop_else_return_len(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and node.orelse:
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return):
                    ret = node.orelse[0]
                    text = source[_span(source, ret)[0]:_span(source, ret)[1]]
                    if "len(" in text or "i + 1" in text or "i+1" in text:
                        out.append(source)
        return []

    def _wrong_return_value(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if txt.strip() == "return x":
                    out.append(_replace_node(source, node, "return i"))
                elif txt.strip() == "return seq":
                    out.append(_replace_node(source, node, "return 0"))
                elif txt.strip() == "return ()":
                    out.append(_replace_node(source, node, "return 0"))
                elif txt.strip() == "return None":
                    out.append(_replace_node(source, node, "return 0"))
                elif txt.strip() == "return i + 1":
                    out.append(_replace_node(source, node, "return len(seq)"))
                elif txt.strip() == "return len(seq) + 1":
                    out.append(_replace_node(source, node, "return len(seq)"))
        return out

    def _range_len_to_len_plus_one(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "len(seq) + 1" in txt:
                    out.append(_replace_node(source, node, txt.replace("len(seq) + 1", "len(seq)")))
                elif "range(l)" in txt:
                    out.append(_replace_node(source, node, txt.replace("range(l)", "range(len(seq))")))
        return out

    def _return_len_plus_one_to_len(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "len(seq)+1" in txt.replace(" ", "") or "len(seq) + 1" in txt:
                    out.append(_replace_node(source, node, "return len(seq)"))
        return out

    def _empty_check_fix(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "seq == () or []" in txt:
                    out.append(_replace_node(source, node, "len(seq) == 0"))
                if "seq == () or seq == []" in txt:
                    out.append(_replace_node(source, node, "len(seq) == 0"))
                if "seq == ()" in txt and "or" not in txt:
                    out.append(_replace_node(source, node, "len(seq) == 0"))
        return out

    def _break_return_i_fix(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Break):
                parent_txt = source[_span(source, node)[0]:_span(source, node)[1]]
                out.append(_replace_node(source, node, "return len(seq)"))
        return out

    def _none_on_empty_fix(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if txt.strip() == "return":
                    out.append(_replace_node(source, node, "return 0"))
                elif txt.strip() == "return None":
                    out.append(_replace_node(source, node, "return 0"))
        return out

    def _strict_gt_to_gte_counter(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.comparators[0])
                out.append(_splice(source, node, source[ls:le] + " >= " + source[rs:re]))
        return out

    def _loop_var_mismatch_counter(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                if any(isinstance(n, ast.Break) for n in ast.walk(node)):
                    continue
                body_txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "position" in body_txt and "return position" not in body_txt:
                    out.append(body_txt.replace("return i", "return position"))
        return out