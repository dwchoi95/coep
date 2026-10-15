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


def _replace_node(source, old, new):
    return _splice(source, old, new)


class Fixer:
    def rules(self):
        return [
            Rule(name="guard_empty_before_indexing", apply=self._guard_empty_before_indexing, symptoms=("wrong", "err:IndexError")),
            Rule(name="strict_lt_to_lte", apply=self._strict_lt_to_lte, symptoms=("wrong",)),
            Rule(name="strict_gt_to_gte_in_search", apply=self._strict_gt_to_gte_in_search, symptoms=("wrong",)),
            Rule(name="wrong_return_x_or_element", apply=self._wrong_return_x_or_element, symptoms=("wrong",)),
            Rule(name="return_len_plus_one_to_len", apply=self._return_len_plus_one_to_len, symptoms=("wrong",)),
            Rule(name="return_in_loop_to_after_loop", apply=self._return_in_loop_to_after_loop, symptoms=("wrong",)),
            Rule(name="off_by_one_minus_one", apply=self._off_by_one_minus_one, symptoms=("wrong",)),
            Rule(name="while_self_increment_to_increment_by_one", apply=self._while_self_increment_to_increment_by_one, symptoms=("timeout", "wrong")),
            Rule(name="fix_newseq_before_use", apply=self._fix_newseq_before_use, symptoms=("err:UnboundLocalError", "wrong")),
        ]

    def _guard_empty_before_indexing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = ast.unparse(node.test)
                if "seq == () or seq == []" in test or "seq == [] or seq == ()" in test or "seq == () or []" in test or "seq == [] or ()" in test:
                    if node.body and any(isinstance(s, ast.Return) and s.value is not None for s in node.body):
                        pass
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = ast.get_source_segment(source, node.test) or ""
                if "len(seq) == 0 or x < seq[0]" in txt or "x <= seq[0] or seq == () or seq == []" in txt:
                    new_test = txt.replace(" or x < seq[0]", "").replace("x <= seq[0] or ", "").replace(" or seq == () or seq == []", "")
                    out.append(_replace_node(source, node.test, f"len(seq) == 0 or {new_test}" if "len(seq) == 0" not in new_test else new_test))
        return out

    def _strict_lt_to_lte(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left is not None and right is not None:
                    out.append(_replace_node(source, node, f"{left} <= {right}"))
        return out

    def _strict_gt_to_gte_in_search(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left and right:
                    out.append(_replace_node(source, node, f"{left} >= {right}"))
        return out

    def _wrong_return_x_or_element(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "x":
                out.append(_replace_node(source, node.value, "i"))
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "elem":
                out.append(_replace_node(source, node.value, "i"))
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                seg = ast.get_source_segment(source, node.value)
                if seg == "len(seq)+1":
                    out.append(_replace_node(source, node.value, "len(seq)"))
        return out

    def _return_len_plus_one_to_len(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node.value)
                if seg == "i + 1" or seg == "i+1":
                    out.append(_replace_node(source, node.value, "len(seq)"))
                elif seg == "len(seq)+1" or seg == "len(seq) + 1":
                    out.append(_replace_node(source, node.value, "len(seq)"))
        return out

    def _return_in_loop_to_after_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for stmt in node.body:
                    if isinstance(stmt, ast.Return):
                        seg = ast.get_source_segment(source, stmt)
                        if seg is not None and "return" in seg:
                            new = seg.replace("return", "break", 1)
                            out.append(_replace_node(source, stmt, new))
        return out

    def _off_by_one_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node.value)
                if seg == "i - 1" or seg == "count-1" or seg == "count - 1":
                    out.append(_replace_node(source, node.value, "i"))
        return out

    def _while_self_increment_to_increment_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                tgt = ast.get_source_segment(source, node.target)
                val = ast.get_source_segment(source, node.value)
                if tgt and val and tgt == val:
                    out.append(_replace_node(source, node.value, "1"))
        return out

    def _fix_newseq_before_use(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                seg = ast.get_source_segment(source, node.test) or ""
                if "newseq[-1] < x" in seg:
                    out.append(_replace_node(source, node.test, "seq[-1] < x"))
        return out