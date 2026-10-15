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


def _src_for_node(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _replace_node(source, target, repl):
    return _splice(source, target, _src_for_node(source, repl))


class Fixer:
    def rules(self):
        return [
            Rule(
                name="remove_unneeded_print",
                symptoms=("wrong", "timeout"),
                apply=self._remove_unneeded_print,
            ),
            Rule(
                name="fix_missing_return_reverse",
                symptoms=("wrong",),
                apply=self._fix_return_reverse_attr,
            ),
            Rule(
                name="fix_return_reverse_call",
                symptoms=("wrong",),
                apply=self._fix_return_reverse_call,
            ),
            Rule(
                name="reverse_sorted_output",
                symptoms=("wrong",),
                apply=self._reverse_sorted_output,
            ),
            Rule(
                name="min_to_max_age_selection",
                symptoms=("wrong",),
                apply=self._min_to_max_age_selection,
            ),
            Rule(
                name="selection_remove_wrong_name",
                symptoms=("wrong",),
                apply=self._selection_remove_wrong_name,
            ),
            Rule(
                name="selection_append_wrong_name",
                symptoms=("wrong",),
                apply=self._selection_append_wrong_name,
            ),
            Rule(
                name="selection_assign_instead_of_update",
                symptoms=("wrong",),
                apply=self._selection_assign_instead_of_update,
            ),
            Rule(
                name="strictless_to_strictgreater_age_compare",
                symptoms=("wrong",),
                apply=self._strictless_to_strictgreater_age_compare,
            ),
            Rule(
                name="strictgreater_to_strictless_age_compare",
                symptoms=("wrong",),
                apply=self._strictgreater_to_strictless_age_compare,
            ),
            Rule(
                name="fix_loop_over_full_list",
                symptoms=("wrong",),
                apply=self._fix_loop_over_full_list,
            ),
            Rule(
                name="fix_off_by_one_range",
                symptoms=("wrong",),
                apply=self._fix_off_by_one_range,
            ),
            Rule(
                name="fix_wrong_index_pop",
                symptoms=("wrong",),
                apply=self._fix_wrong_index_pop,
            ),
            Rule(
                name="fix_return_list_reverse",
                symptoms=("wrong",),
                apply=self._fix_return_list_reverse,
            ),
            Rule(
                name="fix_return_none_from_sort",
                symptoms=("wrong",),
                apply=self._fix_return_none_from_sort,
            ),
        ]

    def _parse(self, source):
        try:
            return ast.parse(source)
        except SyntaxError:
            return None

    def _remove_unneeded_print(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                f = node.value.func
                if isinstance(f, ast.Name) and f.id == "print":
                    out.append(_splice(source, node, ""))
        return out

    def _fix_return_reverse_attr(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                v = node.value
                if isinstance(v, ast.Attribute) and v.attr == "reverse":
                    out.append(_splice(source, node, "return " + _src_for_node(source, v.value) + ".reverse()"))
        return out

    def _fix_return_reverse_call(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                f = node.value.func
                if isinstance(f, ast.Attribute) and f.attr == "reverse" and not node.value.args and not node.value.keywords:
                    out.append(_splice(source, node, _src_for_node(source, node.value.value) + ".reverse()\nreturn " + _src_for_node(source, node.value.value)))
        return out

    def _reverse_sorted_output(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                out.append(_splice(source, node, "return " + node.value.id + "[::-1]"))
        return out

    def _min_to_max_age_selection(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Lt):
                    txt = _src_for_node(source, node)
                    if "[1]" in txt:
                        out.append(_splice(source, node, txt.replace("<", ">", 1)))
        return out

    def _selection_remove_wrong_name(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        assigns = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                assigns[node.targets[0].id] = node
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove" and len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                arg = node.args[0].id
                if arg in assigns:
                    out.append(_splice(source, node.args[0], assigns[arg].targets[0].id))
        return out

    def _selection_append_wrong_name(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        selects = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Subscript) or isinstance(node.value, ast.Name):
                    selects[node.targets[0].id] = node.value
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                nm = node.args[0].id
                if nm in selects:
                    out.append(_splice(source, node.args[0], _src_for_node(source, selects[nm])))
        return out

    def _selection_assign_instead_of_update(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Name):
                    continue
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript):
                txt = _src_for_node(source, node)
                if "[" in txt and "]" in txt and "=" in txt:
                    out.append(source)
                    break
        return [x for x in out if x != source]

    def _strictless_to_strictgreater_age_compare(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                txt = _src_for_node(source, node)
                if "[1]" in txt:
                    out.append(_splice(source, node, txt.replace("<", ">", 1)))
        return out

    def _strictgreater_to_strictless_age_compare(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                txt = _src_for_node(source, node)
                if "[1]" in txt:
                    out.append(_splice(source, node, txt.replace(">", "<", 1)))
        return out

    def _fix_loop_over_full_list(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and isinstance(node.target, ast.Name):
                if _src_for_node(source, node.iter) == "a":
                    out.append(_splice(source, node.iter, "lst"))
        return out

    def _fix_off_by_one_range(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 2:
                a0, a1 = node.args
                if isinstance(a0, ast.Constant) and a0.value == 1 and isinstance(a1, ast.Call):
                    txt = _src_for_node(source, node)
                    if "len(lst)+1" in txt:
                        out.append(_splice(source, node, txt.replace("len(lst)+1", "len(lst)")))
        return out

    def _fix_wrong_index_pop(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Attribute):
                    out.append(_splice(source, arg, "index"))
        return out

    def _fix_return_list_reverse(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                f = node.value.func
                if isinstance(f, ast.Attribute) and f.attr == "reverse":
                    out.append(_splice(source, node, "return " + _src_for_node(source, f.value) + ""))
        return out

    def _fix_return_none_from_sort(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "sort":
                    out.append(_splice(source, node, "return " + _src_for_node(source, node.value.func.value) + ""))
        return out