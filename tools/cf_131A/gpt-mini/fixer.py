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


class Fixer:
    def rules(self):
        return [
            Rule(
                name="capitalize_to_swapcase_in_capslock_check",
                apply=self._capitalize_to_swapcase_in_capslock_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="title_to_swapcase_in_capslock_check",
                apply=self._title_to_swapcase_in_capslock_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_to_lowercase_after_upper_check",
                apply=self._capitalize_to_lowercase_after_upper_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_len_one_branch_add_swapcase",
                apply=self._missing_len_one_branch_add_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_len_one_branch_add_upper",
                apply=self._missing_len_one_branch_add_upper,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_condition_to_upper",
                apply=self._capitalize_condition_to_upper,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_condition_to_upper_and_first_lower",
                apply=self._capitalize_condition_to_upper_and_first_lower,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_body_to_swapcase_loop",
                apply=self._capitalize_body_to_swapcase_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="isupper_missing_len_one_branch",
                apply=self._isupper_missing_len_one_branch,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_to_swapcase_assignment",
                apply=self._capitalize_to_swapcase_assignment,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_to_lower_in_equal_upper_check",
                apply=self._capitalize_to_lower_in_equal_upper_check,
                symptoms=("wrong",),
            ),
        ]

    def _capitalize_to_swapcase_in_capslock_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "capitalize" and not node.args and not node.keywords:
                out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".swapcase()"))
        return out

    def _title_to_swapcase_in_capslock_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "title" and not node.args and not node.keywords:
                out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".swapcase()"))
        return out

    def _capitalize_to_lowercase_after_upper_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "capitalize" and not node.args and not node.keywords:
                out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".lower()"))
        return out

    def _missing_len_one_branch_add_swapcase(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = ast.get_source_segment(source, node.test) or ""
                if "len(" in txt and "== 1" in txt and "swapcase" in source[_span(source, node)[0]:_span(source, node)[1]]:
                    continue
                if isinstance(node.test, ast.BoolOp) and any(isinstance(v, ast.Compare) for v in node.test.values):
                    seg = ast.get_source_segment(source, node.test) or ""
                    if "word[1:]" in seg or "s[1:]" in seg or "a[1:]" in seg or "old_word[1:]" in seg:
                        insertion = " or len(" + (seg.split("[")[0].split()[-1]) + ") == 1"
                        out.append(_splice(source, node.test, seg + insertion))
        return out

    def _missing_len_one_branch_add_upper(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                seg = ast.get_source_segment(source, node.test) or ""
                if "len(" in seg and "== 1" in seg:
                    continue
                if ".isupper()" in seg and "[1:]" in seg:
                    name = None
                    for n in ast.walk(node.test):
                        if isinstance(n, ast.Name):
                            name = n.id
                            break
                    if name:
                        out.append(_splice(source, node.test, seg + " or len(" + name + ") == 1"))
        return out

    def _capitalize_condition_to_upper(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                seg = ast.get_source_segment(source, node)
                if seg and ".capitalize()" in seg:
                    out.append(_splice(source, node, seg.replace(".capitalize()", ".upper()")))
        return out

    def _capitalize_condition_to_upper_and_first_lower(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                seg = ast.get_source_segment(source, node)
                if seg and "[0:]" in seg and ".capitalize()" in seg:
                    out.append(_splice(source, node, seg.replace("[0:]", "[0:].upper()")))
        return out

    def _capitalize_body_to_swapcase_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "capitalize":
                out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".swapcase()"))
        return out

    def _isupper_missing_len_one_branch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                seg = ast.get_source_segment(source, node.test) or ""
                if ".isupper()" in seg and "len(" not in seg:
                    name = None
                    for n in ast.walk(node.test):
                        if isinstance(n, ast.Name):
                            name = n.id
                            break
                    if name:
                        out.append(_splice(source, node.test, seg + " or len(" + name + ") == 1"))
        return out

    def _capitalize_to_swapcase_assignment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                seg = ast.get_source_segment(source, node.value)
                if seg and ".capitalize()" in seg:
                    out.append(_splice(source, node.value, seg.replace(".capitalize()", ".swapcase()")))
        return out

    def _capitalize_to_lower_in_equal_upper_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "capitalize":
                seg = ast.get_source_segment(source, node)
                if seg:
                    out.append(_splice(source, node, seg.replace(".capitalize()", ".lower()")))
        return out