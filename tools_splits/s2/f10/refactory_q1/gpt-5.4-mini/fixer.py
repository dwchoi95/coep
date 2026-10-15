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
            Rule(
                name="strict_lt_should_be_lte",
                apply=self._lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_should_be_gte",
                apply=self._gt_to_ge,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_inside_loop_should_be_after_loop",
                apply=self._move_inner_return_to_loop_else,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_return_len_plus_one_or_wrong_default",
                apply=self._fix_len_plus_one_and_wrong_tail_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="empty_check_should_guard_before_indexing",
                apply=self._prepend_empty_guard,
                symptoms=("err:IndexError", "wrong"),
            ),
            Rule(
                name="off_by_one_range_upper_bound",
                apply=self._fix_range_minus_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="insert_instead_of_return",
                apply=self._fix_insert_based_search,
                symptoms=("wrong",),
            ),
            Rule(
                name="while_position_doubling_or_stuck",
                apply=self._fix_position_increment_and_while_search,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="recursive_helper_missing_return_tail",
                apply=self._fix_recursive_helper_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="replace_max_min_boundary_logic_with_linear_scan",
                apply=self._fix_max_min_boundary_search,
                symptoms=("wrong",),
            ),
        ]

    def _lt_to_le(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re_]))
        return out

    def _gt_to_ge(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " >= " + source[rs:re_]))
        return out

    def _move_inner_return_to_loop_else(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            if not fn.body or not isinstance(fn.body[-1], ast.For):
                continue
            loop = fn.body[-1]
            if not loop.body:
                continue
            last = loop.body[-1]
            if isinstance(last, ast.Return):
                ret_src = source[_span(source, last)[0]:_span(source, last)[1]]
                if loop.orelse:
                    continue
                new_loop = source[_span(source, loop)[0]:_span(source, loop)[1]]
                insert_pos = _span(source, loop)[1]
                replaced = source[:_span(source, last)[0]] + source[_span(source, last)[1]:]
                replaced = replaced[:insert_pos - (len(source[_span(source, last)[0]:_span(source, last)[1]]))] + replaced[insert_pos - (len(source[_span(source, last)[0]:_span(source, last)[1]])):]
                out.append(source.replace(ret_src, "", 1).replace(
                    source[_span(source, loop)[0]:_span(source, loop)[1]],
                    source[_span(source, loop)[0]:_span(source, loop)[1]] + "\n    else:\n        return len(seq)",
                    1,
                ))
        return out

    def _fix_len_plus_one_and_wrong_tail_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "len(seq)+1" in txt or "i + 1" in txt or "i+1" in txt or "return seq" in txt:
                    out.append(source[:_span(source, node)[0]] + "return len(seq)" + source[_span(source, node)[1]:])
                if txt.strip() == "return":
                    out.append(source[:_span(source, node)[0]] + "return 0" + source[_span(source, node)[1]:])
        return out

    def _prepend_empty_guard(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            src = source[_span(source, fn)[0]:_span(source, fn)[1]]
            if "seq[0]" in src or "seq[-1]" in src or "max(seq)" in src or "min(seq)" in src:
                if "if len(seq) == 0" not in src and "if seq == []" not in src and "if seq == ()" not in src:
                    insert_at = _span(source, fn.body[0])[0]
                    out.append(source[:insert_at] + "    if len(seq) == 0:\n        return 0\n" + source[insert_at:])
        return out

    def _fix_range_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "len(seq)-1" in txt:
                    out.append(source[:_span(source, node)[0]] + txt.replace("len(seq)-1", "len(seq)") + source[_span(source, node)[1]:])
        return out

    def _fix_insert_based_search(self, source):
        if "seq.insert(x, i)" in source and "return seq" in source:
            return [source.replace("seq.insert(x, i)", "return i").replace("return seq", "return len(seq)")]
        return []

    def _fix_position_increment_and_while_search(self, source):
        out = []
        if "position += position" in source:
            out.append(source.replace("position += position", "position += 1"))
        if "while position < len(seq)-1" in source:
            out.append(source.replace("while position < len(seq)-1", "while position < len(seq)"))
        if "return 0" in source and "if x > next_element" in source:
            out.append(source.replace("return 0", "return i", 1))
        return out

    def _fix_recursive_helper_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            if any(isinstance(n, ast.FunctionDef) for n in ast.walk(fn) if n is not fn):
                body_src = source[_span(source, fn)[0]:_span(source, fn)[1]]
                if "return helper(index+1)" in body_src or "return helper(index + 1)" in body_src:
                    out.append(body_src.replace("return helper(index+1)", "return helper(index+1)"))
                if fn.body and isinstance(fn.body[-1], ast.FunctionDef):
                    continue
        if "def helper(index):" in source and "return helper(index+1)" in source:
            return [source + ""]
        return out

    def _fix_max_min_boundary_search(self, source):
        out = []
        if "max(seq)" in source or "min(seq)" in source:
            if "for i in range(len(seq))" in source and "return len(seq)" in source:
                s = source
                s = s.replace("if max(seq) < x:\n        return len(seq)\n    if x <= min(seq):\n        return 0\n", "")
                s = s.replace("if x <= seq[0]:\n        return 0\n    elif x > seq[-1]:\n        return len(seq)\n    elif seq == ():\n        return 0\n", "if seq == () or seq == []:\n        return 0\n")
                out.append(s)
        return out