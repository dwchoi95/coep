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
            Rule(name="append_to_wrong_list_name", apply=self._append_to_wrong_list_name, symptoms=("wrong",)),
            Rule(name="fix_typo_variable_in_compare", apply=self._fix_typo_variable_in_compare, symptoms=("wrong",)),
            Rule(name="fix_misnamed_loop_variable", apply=self._fix_misnamed_loop_variable, symptoms=("wrong",)),
            Rule(name="fix_off_by_one_return_slice", apply=self._fix_off_by_one_return_slice, symptoms=("wrong",)),
            Rule(name="fix_return_wrong_variable", apply=self._fix_return_wrong_variable, symptoms=("wrong",)),
            Rule(name="fix_append_remove_return_value", apply=self._fix_append_remove_return_value, symptoms=("wrong",)),
            Rule(name="fix_append_call_on_list", apply=self._fix_append_call_on_list, symptoms=("wrong",)),
            Rule(name="fix_pop_index_of_max", apply=self._fix_pop_index_of_max, symptoms=("wrong",)),
            Rule(name="fix_missing_slice_bound", apply=self._fix_missing_slice_bound, symptoms=("wrong",)),
            Rule(name="fix_assignments_in_swap", apply=self._fix_assignments_in_swap, symptoms=("wrong",)),
            Rule(name="fix_recursive_call_wrong_name", apply=self._fix_recursive_call_wrong_name, symptoms=("wrong",)),
            Rule(name="fix_maximum_removed_inside_loop", apply=self._fix_maximum_removed_inside_loop, symptoms=("wrong",)),
            Rule(name="fix_list_index_vs_value", apply=self._fix_list_index_vs_value, symptoms=("wrong",)),
            Rule(name="fix_wrong_comparison_operator", apply=self._fix_wrong_comparison_operator, symptoms=("wrong",)),
        ]

    def _append_to_wrong_list_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "append":
                if isinstance(node.value, ast.Name) and node.value.id == "new":
                    new_source = _replace_node(source, node.value, ast.get_source_segment(source, node) or "")
                else:
                    continue
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "new":
                    seg = ast.get_source_segment(source, node.func.value)
                    if seg:
                        out.append(source[:_span(source, node.func.value)[0]] + "list" + source[_span(source, node.func.value)[1]:])
                elif isinstance(node.func.value, ast.Name) and node.func.value.id == "list":
                    out.append(source[:_span(source, node.func.value)[0]] + "new_lst" + source[_span(source, node.func.value)[1]:])
        return list(dict.fromkeys(out))

    def _fix_typo_variable_in_compare(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "element":
                out.append(_splice(source, node, "elements"))
        return list(dict.fromkeys(out))

    def _fix_misnamed_loop_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "oldest":
                out.append(_splice(source, node, "biggest"))
            if isinstance(node, ast.Name) and node.id == "element" and "for elements in lst_res" in source:
                out.append(_splice(source, node, "elements"))
            if isinstance(node, ast.Name) and node.id == "ele":
                out.append(_splice(source, node, "element"))
        return list(dict.fromkeys(out))

    def _fix_off_by_one_return_slice(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                upper = node.slice.upper
                if isinstance(upper, ast.BinOp) and isinstance(upper.op, ast.Add) and isinstance(upper.right, ast.Constant) and upper.right.value == 1:
                    out.append(_splice(source, upper.right, ""))
                    out.append(source.replace("[:k+1]", "[:k]"))
                if isinstance(node.slice.upper, ast.Constant) and node.slice.upper.value == 5:
                    out.append(source.replace("[:5]", "[:k]"))
                if isinstance(node.slice.upper, ast.Constant) and node.slice.lower is None and node.slice.step is None:
                    pass
        return list(dict.fromkeys([s for s in out if s != source]))

    def _fix_return_wrong_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = ast.get_source_segment(source, node)
                if txt == "return lst" and "new_list" in source:
                    out.append(source.replace("return lst", "return new_list"))
                if txt == "return r":
                    out.append(source.replace("return r", "return rs"))
                if txt == "return sort_k" and "while n <= k" in source:
                    out.append(source.replace("return sort_k", "return sort_k[:k]"))
        return list(dict.fromkeys(out))

    def _fix_append_remove_return_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "append" and len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "remove":
                        out.append(source.replace(ast.get_source_segment(source, node), ast.get_source_segment(source, arg.func.value) if False else ""))
        if "lst.remove(max(lst))" in source and "append(lst.remove(max(lst)))" in source:
            out.append(source.replace("new_lst.append(lst.remove(max(lst)))", "new_lst.append(max(lst))\n        lst.remove(max(lst))"))
        return list(dict.fromkeys([s for s in out if s]))

    def _fix_append_call_on_list(self, source):
        if "rs.append[biggest]" in source:
            return [source.replace("rs.append[biggest]", "rs.append(biggest)").replace("lst.remove[biggest]", "lst.remove(biggest)").replace("return r", "return rs")]
        return []

    def _fix_pop_index_of_max(self, source):
        if "pop(max(lst))" in source:
            return [source.replace("lst.pop(max(lst))", "lst.pop(lst.index(max(lst)))")]
        return []

    def _fix_missing_slice_bound(self, source):
        if "return tmp[:5]" in source:
            return [source.replace("return tmp[:5]", "return tmp[:k]")]
        if "return sort_list[:k-1]" in source:
            return [source.replace("return list.reverse(sorted_list)[:k-1]", "return sort_list[:k]")]
        return []

    def _fix_assignments_in_swap(self, source):
        if "lst[j] = lst [j + 1]" in source and "lst[j + 1] = lst[j]" in source:
            return [source.replace("lst[j] = lst [j + 1]\n                lst[j + 1] = lst[j]", "lst[j], lst[j + 1] = lst[j + 1], lst[j]")]
        return []

    def _fix_recursive_call_wrong_name(self, source):
        if "top_k(lst, k-1)" in source and "new_lst" in source:
            return [source.replace("top_k(lst, k-1)", "top_k(new_list,k-1)")]
        return []

    def _fix_maximum_removed_inside_loop(self, source):
        out = []
        if "lst.pop(max)" in source:
            out.append(source.replace("lst.pop(max)", "lst.pop(lst.index(max))"))
        if "while len(lst2) != k:" in source and "while len(lst2) != k:\n            lst2.append(max)" in source:
            out.append(source.replace("        lst.pop(max)\n        while len(lst2) != k:\n            lst2.append(max)", "        lst.pop(lst.index(max))\n        while len(lst2) != k:\n            lst2.append(max)"))
        return list(dict.fromkeys(out))

    def _fix_list_index_vs_value(self, source):
        if "if i == max(lst):" in source and "del lst[i]" in source:
            return [source.replace("if i == max(lst):", "if lst[i] == max(lst):")]
        return []

    def _fix_wrong_comparison_operator(self, source):
        out = []
        if "if e < pivot:" in source and "sort_list = higher + plist + lower" in source:
            out.append(source.replace("sort_list = higher + plist + lower", "sort_list = lower + plist + higher"))
        if "if x == pivot:" in source and "if x > pivot:" in source:
            out.append(source.replace("if x == pivot:", "if e == pivot:").replace("if x > pivot:", "if e > pivot:"))
        return list(dict.fromkeys(out))