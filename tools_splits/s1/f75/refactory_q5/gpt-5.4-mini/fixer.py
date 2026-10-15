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
            Rule(name="append_before_remove_max", apply=self._append_before_remove_max, symptoms=("wrong", "timeout")),
            Rule(name="append_wrong_loop_var", apply=self._append_wrong_loop_var, symptoms=("wrong",)),
            Rule(name="use_correct_list_name", apply=self._use_correct_list_name, symptoms=("wrong", "err:NameError")),
            Rule(name="return_result_not_lst", apply=self._return_result_not_lst, symptoms=("wrong",)),
            Rule(name="rename_oldest_to_biggest", apply=self._rename_oldest_to_biggest, symptoms=("wrong", "err:NameError")),
            Rule(name="fix_element_name_in_for", apply=self._fix_element_name_in_for, symptoms=("wrong", "err:NameError")),
            Rule(name="use_found_max_not_loop_var", apply=self._use_found_max_not_loop_var, symptoms=("wrong",)),
            Rule(name="fix_sort_recursion_variable", apply=self._fix_sort_recursion_variable, symptoms=("wrong", "err:NameError")),
            Rule(name="fix_return_slice_variable", apply=self._fix_return_slice_variable, symptoms=("wrong",)),
            Rule(name="fix_off_by_one_slice", apply=self._fix_off_by_one_slice, symptoms=("wrong",)),
            Rule(name="fix_inclusive_while_bound", apply=self._fix_inclusive_while_bound, symptoms=("wrong", "timeout")),
            Rule(name="fix_append_remove_swap", apply=self._fix_append_remove_swap, symptoms=("wrong",)),
            Rule(name="fix_pop_index_max", apply=self._fix_pop_index_max, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_list_call_brackets", apply=self._fix_list_call_brackets, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_list_to_element_append", apply=self._fix_list_to_element_append, symptoms=("wrong",)),
            Rule(name="fix_sort_return_name", apply=self._fix_sort_return_name, symptoms=("wrong",)),
            Rule(name="fix_k_zero_branch", apply=self._fix_k_zero_branch, symptoms=("wrong",)),
        ]

    def _append_before_remove_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "top_k"]:
            for w in ast.walk(func):
                if isinstance(w, ast.While) and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id == "max" for x in ast.walk(w)):
                    body = w.body
                    if len(body) >= 2 and isinstance(body[0], ast.Expr) and isinstance(body[1], ast.Expr):
                        t0 = body[0].value
                        t1 = body[1].value
                        if isinstance(t0, ast.Call) and isinstance(t0.func, ast.Attribute) and t0.func.attr == "remove" and isinstance(t1, ast.Call) and isinstance(t1.func, ast.Attribute) and t1.func.attr == "append":
                            out.append(_replace_node(source, t0, source[_span(source, t1[0])[0]:_span(source, t1[0])[1]] if False else source[_span(source, t1)[0]:_span(source, t1)[1]]))
        return out

    def _append_wrong_loop_var(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id in {"numbers", "element", "i"}:
                    parent = node
                    out.append(_replace_node(source, arg, ast.get_source_segment(source, arg) or arg.id))
        return []

    def _use_correct_list_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "new":
                out.append(_replace_node(source, node, "new_lst"))
        return out

    def _return_result_not_lst(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                sl = node.value
                if isinstance(sl.value, ast.Name) and sl.value.id == "lst":
                    out.append(_replace_node(source, sl.value, "result"))
        return out

    def _rename_oldest_to_biggest(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "oldest":
                out.append(_replace_node(source, node, "biggest"))
        return out

    def _fix_element_name_in_for(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "element":
                out.append(_replace_node(source, node, "elements"))
        return out

    def _use_found_max_not_loop_var(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                c = node.value
                if isinstance(c.func, ast.Attribute) and c.func.attr == "append" and len(c.args) == 1 and isinstance(c.args[0], ast.Name):
                    arg = c.args[0]
                    if arg.id in {"i", "element"}:
                        out.append(_replace_node(source, arg, "largest"))
        return out

    def _fix_sort_recursion_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "new_lst":
                out.append(_replace_node(source, node, "new_list"))
        return out

    def _fix_return_slice_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                sub = node.value
                if isinstance(sub.value, ast.Name) and sub.value.id == "sort" and isinstance(sub.slice, ast.Slice) and isinstance(sub.slice.upper, ast.Constant) and sub.slice.upper.value == 3:
                    out.append(_replace_node(source, sub.slice.upper, "k"))
        return out

    def _fix_off_by_one_slice(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice) and isinstance(node.slice.upper, ast.Constant) and node.slice.upper.value in {k for k in range(0, 10)}:
                if node.slice.upper.value == 1:
                    out.append(_replace_node(source, node.slice.upper, "k"))
        return out

    def _fix_inclusive_while_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
                out.append(_replace_node(source, node.ops[0], "<"))
        return out

    def _fix_append_remove_swap(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                inner = node.args[0]
                if isinstance(inner.func, ast.Attribute) and inner.func.attr == "remove":
                    arg = inner.args[0] if inner.args else None
                    if arg is not None:
                        out.append(_replace_node(source, node, ast.get_source_segment(source, arg) or "max(lst)"))
        return out

    def _fix_pop_index_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id == "largest":
                    out.append(_replace_node(source, arg, "lst.index(max(lst))"))
        return out

    def _fix_list_call_brackets(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"append", "remove"}:
                out.append(_replace_node(source, node.func.attr and node.func, ast.get_source_segment(source, node.func) + "()"))
        return out

    def _fix_list_to_element_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id == "lst":
                out.append(_replace_node(source, node.args[0], "maximum"))
        return out

    def _fix_sort_return_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "lst":
                out.append(_replace_node(source, node.value, "sort_list"))
        return out

    def _fix_k_zero_branch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left == "k" and right == "0":
                    out.append(_replace_node(source, node.comparators[0], "0"))
        return out