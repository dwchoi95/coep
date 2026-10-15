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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _is_search_func(tree):
    return isinstance(tree, ast.Module) and any(
        isinstance(n, ast.FunctionDef) and n.name == "search" for n in tree.body
    )


def _replace_first_occurrence(source, old_node, new_text):
    return _splice(source, old_node, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="empty_sequence_returns_zero",
                apply=self._empty_sequence_returns_zero,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_to_le_in_comparison",
                apply=self._lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_to_ge_in_comparison",
                apply=self._gt_to_ge,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_constant_return_to_len_or_zero",
                apply=self._wrong_constant_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="off_by_one_return_len_after_scan",
                apply=self._off_by_one_return_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_none_in_search_loop",
                apply=self._return_none_in_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_return_after_helper",
                apply=self._missing_outer_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_default_empty_return",
                apply=self._wrong_default_empty_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_len_plus_one_to_len",
                apply=self._range_len_plus_one,
                symptoms=("wrong", "timeout"),
            ),
        ]

    def _empty_sequence_returns_zero(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
                if node.value.value in (None, False, (), "empty", "not found", "none"):
                    out.append(_splice(source, node, "return 0"))
        return out

    def _lt_to_le(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re]))
        return out

    def _gt_to_ge(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " >= " + source[rs:re]))
        return out

    def _wrong_constant_return(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = ast.get_source_segment(source, node) or ""
                if "return x" in txt:
                    out.append(_splice(source, node, "return i"))
                elif "return x," in txt:
                    out.append(_splice(source, node, "return 0"))
                elif "return (x,)" in txt or "return [x,]" in txt or "return 'empty'" in txt:
                    out.append(_splice(source, node, "return 0"))
                elif "return seq" in txt:
                    out.append(_splice(source, node, "return 0"))
        return out

    def _off_by_one_return_len(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = ast.get_source_segment(source, node) or ""
                if "return i + 1" in txt or "return i+1" in txt:
                    out.append(_splice(source, node, "return len(seq)"))
                elif "return len(seq) + 1" in txt or "return len(seq)+1" in txt:
                    out.append(_splice(source, node, "return len(seq)"))
                elif "return seq.index(seq[-1])+1" in txt:
                    out.append(_splice(source, node, "return len(seq)"))
                elif "return seq.index(seq[-1]) + 1" in txt:
                    out.append(_splice(source, node, "return len(seq)"))
        return out

    def _return_none_in_loop(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                out.append(_splice(source, node, "return result"))
        return out

    def _missing_outer_return(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "search":
                for inner in node.body:
                    if isinstance(inner, ast.FunctionDef):
                        s, e = _span(source, node)
                        if source[e - 1] != "\n":
                            rep = source[s:e] + "\n    return helper(index)"
                        else:
                            rep = source[s:e] + "    return helper(index)\n"
                        out.append(source[:e] + "    return helper(index)" + source[e:])
                        break
        return out

    def _wrong_default_empty_return(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = ast.get_source_segment(source, node) or ""
                if "if seq == () or []" in txt or "if seq == () or seq == []" in txt:
                    out.append(_splice(source, node.test, "seq == () or seq == []"))
        return out

    def _range_len_plus_one(self, source):
        tree = _parse(source)
        if tree is None or not _is_search_func(tree):
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                txt = ast.get_source_segment(source, node) or ""
                if "len(seq) + 1" in txt or "len(seq)+1" in txt:
                    out.append(_splice(source, node, "range(len(seq))"))
                elif "len(range(seq))" in txt:
                    out.append(_splice(source, node, "range(len(seq))"))
                elif txt.strip() == "range(seq)":
                    out.append(_splice(source, node, "range(len(seq))"))
        return out