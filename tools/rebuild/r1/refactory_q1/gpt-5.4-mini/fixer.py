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


def _replace_node(source, node, new_text):
    try:
        return [_splice(source, node, new_text)]
    except Exception:
        return []


def _find_parent_map(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


class Fixer:
    def rules(self):
        return [
            Rule(name="empty_seq_returns_zero", apply=self._empty_seq_returns_zero, symptoms=("wrong",)),
            Rule(name="fix_return_none_on_exact_match_branch", apply=self._fix_return_none_on_exact_match_branch, symptoms=("wrong",)),
            Rule(name="fix_return_none_in_loop", apply=self._fix_return_none_in_loop, symptoms=("wrong",)),
            Rule(name="fix_early_return_in_for", apply=self._fix_early_return_in_for, symptoms=("wrong",)),
            Rule(name="fix_strict_lt_to_lte", apply=self._fix_strict_lt_to_lte, symptoms=("wrong",)),
            Rule(name="fix_strict_gt_to_gte", apply=self._fix_strict_gt_to_gte, symptoms=("wrong",)),
            Rule(name="fix_wrong_final_return_len_minus_one", apply=self._fix_wrong_final_return_len_minus_one, symptoms=("wrong",)),
            Rule(name="fix_wrong_return_len_plus_one", apply=self._fix_wrong_return_len_plus_one, symptoms=("wrong",)),
            Rule(name="fix_return_x_instead_of_index", apply=self._fix_return_x_instead_of_index, symptoms=("wrong",)),
            Rule(name="fix_return_count_minus_one", apply=self._fix_return_count_minus_one, symptoms=("wrong",)),
            Rule(name="fix_return_none_to_break_or_value", apply=self._fix_return_none_to_break_or_value, symptoms=("wrong",)),
            Rule(name="fix_empty_check_order", apply=self._fix_empty_check_order, symptoms=("err:IndexError", "wrong")),
            Rule(name="fix_range_len_off_by_one", apply=self._fix_range_len_off_by_one, symptoms=("err:IndexError", "wrong")),
            Rule(name="fix_range_len_function", apply=self._fix_range_len_function, symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_seq_indexing_operator", apply=self._fix_seq_indexing_operator, symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_empty_check_bool_or_tuple", apply=self._fix_empty_check_bool_or_tuple, symptoms=("wrong",)),
            Rule(name="fix_return_len_seq_when_missing", apply=self._fix_return_len_seq_when_missing, symptoms=("wrong",)),
        ]

    def _empty_seq_returns_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = ast.get_source_segment(source, node.test) or ""
                if ("seq == ()" in txt or "seq==()" in txt or "seq == []" in txt or "seq==[]" in txt or "not seq" in txt) and any(isinstance(b, ast.Return) and getattr(b.value, "value", None) is None for b in node.body):
                    ret = next((b for b in node.body if isinstance(b, ast.Return) and getattr(b.value, "value", None) is None), None)
                    if ret:
                        out.append(_splice(source, ret, "return 0"))
        return out

    def _fix_return_none_on_exact_match_branch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                parent = None
                for p in ast.walk(tree):
                    for c in ast.iter_child_nodes(p):
                        if c is node:
                            parent = p
                            break
                if isinstance(parent, ast.If) and ast.get_source_segment(source, parent.test) and "x <=" in ast.get_source_segment(source, parent.test):
                    out.append(_splice(source, node, "return i"))
                    out.append(_splice(source, node, "return position"))
        return out

    def _fix_return_none_in_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                txt = ast.get_source_segment(source, node) or ""
                if "return" == txt.strip():
                    out.append(_splice(source, node, "return result"))
        return out

    def _fix_early_return_in_for(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and node.body:
                last = node.body[-1]
                if isinstance(last, ast.Return):
                    seg = ast.get_source_segment(source, last) or ""
                    if "return len(seq)" in seg or "return i + 1" in seg or "return i+1" in seg:
                        pass
                for stmt in node.body:
                    if isinstance(stmt, ast.If):
                        for b in stmt.body:
                            if isinstance(b, ast.Return):
                                seg = ast.get_source_segment(source, b) or ""
                                if "return len(seq)" in seg or "return x" in seg or "return None" in seg or "return count-1" in seg or "return count - 1" in seg:
                                    out.append(_splice(source, b, seg.replace("return x", "return i").replace("return count-1", "return count").replace("return count - 1", "return count").replace("return None", "return len(seq)").replace("return x", "return i")))
        return out

    def _fix_strict_lt_to_lte(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left and right:
                    out.append(_splice(source, node, f"{left} <= {right}"))
        return out

    def _fix_strict_gt_to_gte(self, source):
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
                    out.append(_splice(source, node, f"{left} >= {right}"))
        return out

    def _fix_wrong_final_return_len_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if "len(seq)-1" in seg or "len(seq) - 1" in seg:
                    out.append(_splice(source, node, seg.replace("-1", "")))
        return out

    def _fix_wrong_return_len_plus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if "len(seq)+1" in seg or "len(seq) + 1" in seg:
                    out.append(_splice(source, node, seg.replace("+1", "")))
        return out

    def _fix_return_x_instead_of_index(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if seg.strip() == "return x":
                    out.append(_splice(source, node, "return i"))
        return out

    def _fix_return_count_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if "return count-1" in seg or "return count - 1" in seg:
                    out.append(_splice(source, node, seg.replace("-1", "")))
        return out

    def _fix_return_none_to_break_or_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if seg.strip() == "return":
                    out.append(_splice(source, node, "break"))
        return out

    def _fix_empty_check_order(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = ast.get_source_segment(source, node.test) or ""
                if ("x < seq[0]" in test or "x <= seq[0]" in test) and ("seq == ()" in test or "seq == []" in test or "not seq" in test):
                    new = test.replace("x < seq[0] or ", "").replace("x <= seq[0] or ", "")
                    if "or not seq" in test:
                        new = new.replace("or not seq", "")
                    out.append(_splice(source, node.test, "len(seq) == 0 or " + new if "len(seq)" not in new else new))
        return out

    def _fix_range_len_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                seg = ast.get_source_segment(source, node) or ""
                if "len(seq)-1" in seg:
                    out.append(_splice(source, node, seg.replace("len(seq)-1", "len(seq)")))
                elif "len(seq)+1" in seg:
                    out.append(_splice(source, node, seg.replace("len(seq)+1", "len(seq)")))
        return out

    def _fix_range_len_function(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
                seg = ast.get_source_segment(source, node.iter) or ""
                if "len(range(seq))" in seg:
                    out.append(_splice(source, node.iter, "range(len(seq))"))
        return out

    def _fix_seq_indexing_operator(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                seg = ast.get_source_segment(source, node) or ""
                if "(" in seg and ")" in seg and "[" not in seg.split("(")[0]:
                    if "seq(" in seg:
                        out.append(_splice(source, node, seg.replace("(", "[").replace(")", "]", 1)))
        return out

    def _fix_empty_check_bool_or_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                seg = ast.get_source_segment(source, node) or ""
                if "== () or []" in seg or "==[]or()" in seg or "== () and []" in seg or "== () or []" in seg:
                    out.append(_splice(source, node, seg.replace("or []", "or seq == []").replace("and []", "or seq == []")))
        return out

    def _fix_return_len_seq_when_missing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node) or ""
                if seg.strip() in {"return i+1", "return i + 1"}:
                    out.append(_splice(source, node, "return len(seq)"))
        return out