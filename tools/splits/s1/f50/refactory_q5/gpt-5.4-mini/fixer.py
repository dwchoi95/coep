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
            Rule(name="append_selected_value_not_loop_variable",
                 apply=self._append_selected_value_not_loop_variable,
                 symptoms=("wrong",)),
            Rule(name="return_sorted_prefix_not_original_list",
                 apply=self._return_sorted_prefix_not_original_list,
                 symptoms=("wrong",)),
            Rule(name="fix_misnamed_new_list_return",
                 apply=self._fix_misnamed_new_list_return,
                 symptoms=("wrong",)),
            Rule(name="fix_missing_return_of_accumulator",
                 apply=self._fix_missing_return_of_accumulator,
                 symptoms=("wrong",)),
            Rule(name="fix_wrong_append_argument_in_max_loop",
                 apply=self._fix_wrong_append_argument_in_max_loop,
                 symptoms=("wrong",)),
            Rule(name="fix_sort_helper_call_name",
                 apply=self._fix_sort_helper_call_name,
                 symptoms=("wrong",)),
            Rule(name="fix_hardcoded_slice_bound",
                 apply=self._fix_hardcoded_slice_bound,
                 symptoms=("wrong",)),
            Rule(name="fix_wrong_attribute_or_subscript_on_number",
                 apply=self._fix_wrong_attribute_or_subscript_on_number,
                 symptoms=("wrong",)),
            Rule(name="fix_pop_argument_from_max_to_index",
                 apply=self._fix_pop_argument_from_max_to_index,
                 symptoms=("wrong",)),
            Rule(name="fix_pop_return_from_none_to_value",
                 apply=self._fix_pop_return_from_none_to_value,
                 symptoms=("wrong",)),
            Rule(name="fix_missing_loop_increment_return",
                 apply=self._fix_missing_loop_increment_return,
                 symptoms=("wrong",)),
            Rule(name="fix_wrong_index_in_comparison",
                 apply=self._fix_wrong_index_in_comparison,
                 symptoms=("wrong",)),
            Rule(name="fix_off_by_one_range_upper_bound",
                 apply=self._fix_off_by_one_range_upper_bound,
                 symptoms=("wrong",)),
            Rule(name="fix_assigned_alias_then_mutate_original",
                 apply=self._fix_assigned_alias_then_mutate_original,
                 symptoms=("wrong",)),
            Rule(name="fix_return_false_for_large_k",
                 apply=self._fix_return_false_for_large_k,
                 symptoms=("wrong",)),
        ]

    def _parse(self, source):
        try:
            return ast.parse(source)
        except SyntaxError:
            return None

    def _append_selected_value_not_loop_variable(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for i, stmt in enumerate(fn.body):
                if isinstance(stmt, ast.While) and isinstance(stmt.test, ast.Name) and stmt.test.id in {"lst", "lst_res"}:
                    body = stmt.body
                    for j in range(len(body) - 1):
                        a, b = body[j], body[j + 1]
                        if isinstance(a, ast.For) and isinstance(b, ast.Expr):
                            if isinstance(b.value, ast.Call) and isinstance(b.value.func, ast.Attribute) and b.value.func.attr == "append":
                                if len(b.value.args) == 1 and isinstance(b.value.args[0], ast.Name):
                                    loop_var = a.target.id if isinstance(a.target, ast.Name) else None
                                    if loop_var and b.value.args[0].id == loop_var:
                                        for n in ast.walk(stmt):
                                            if isinstance(n, ast.Name) and n.id == loop_var:
                                                out.append(_replace_node(source, n, "largest"))
                                                return out
        return []

    def _return_sorted_prefix_not_original_list(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                if isinstance(node.value.value, ast.Name) and node.value.value.id in {"lst", "data_list", "sort_list", "sort", "new_lst", "new_list"}:
                    sl = node.value.slice
                    if isinstance(sl, ast.Name) and sl.id == "k":
                        out.append(_replace_node(source, node.value.value, "product" if node.value.value.id == "lst" else node.value.value.id))
                        return out
        return []

    def _fix_misnamed_new_list_return(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.List):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"new_lst", "new_list", "result"}:
                    target_name = node.targets[0].id
                    for ret in ast.walk(tree):
                        if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Name) and ret.value.id in {"new_lst", "new_list"}:
                            out.append(_replace_node(source, ret.value, target_name))
                            return out
        return []

    def _fix_missing_return_of_accumulator(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not any(isinstance(s, ast.Return) for s in node.body):
                    for s in node.body[::-1]:
                        if isinstance(s, ast.While):
                            for inner in ast.walk(s):
                                if isinstance(inner, ast.Name) and inner.id in {"new_lst", "newlist", "op", "l"}:
                                    ret = "\n    return " + inner.id
                                    out.append(source + ret)
                                    return out
        return []

    def _fix_wrong_append_argument_in_max_loop(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id in {"lst", "new_lst"}:
                    out.append(_replace_node(source, node.args[0], "maximum"))
                    return out
        return []

    def _fix_sort_helper_call_name(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "sort":
                    out.append(_replace_node(source, node.value.func, "sort"))
                    return out
        return []

    def _fix_hardcoded_slice_bound(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == 3:
                out.append(_replace_node(source, node.slice, "k"))
                return out
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Sub):
                if isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 1:
                    out.append(_replace_node(source, node.slice, "k"))
                    return out
        return []

    def _fix_wrong_attribute_or_subscript_on_number(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in {"i", "element", "ele"}:
                out.append(_replace_node(source, node, node.value.id))
                return out
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in {"r", "result"} and node.attr == "append":
                return []
        return []

    def _fix_pop_argument_from_max_to_index(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                    inner = node.args[0]
                    if isinstance(inner.func, ast.Name) and inner.func.id == "max":
                        out.append(_replace_node(source, inner, "lst.index(max(lst))"))
                        return out
        return []

    def _fix_pop_return_from_none_to_value(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                    inner = node.args[0]
                    if isinstance(inner.func, ast.Attribute) and inner.func.attr == "remove":
                        out.append(_replace_node(source, node, f"{node.func.value.id}.append({inner.func.value.id})" if isinstance(node.func.value, ast.Name) and isinstance(inner.func.value, ast.Name) else "new.append(top)"))
                        return out
        return []

    def _fix_missing_loop_increment_return(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                txt = ast.get_source_segment(source, node)
                if txt and "counter+=" in txt and "return" not in txt:
                    return source + "\n    return new_lst"
        return []

    def _fix_wrong_index_in_comparison(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                if isinstance(node.left, ast.Subscript):
                    if isinstance(node.left.slice, ast.Constant) and isinstance(node.left.slice.value, int):
                        return []
                seg = ast.get_source_segment(source, node)
                if seg and "[1]" in seg and ".index" not in seg:
                    out.append(_replace_node(source, node, seg.replace("[1]", "")))
                    return out
        return []

    def _fix_off_by_one_range_upper_bound(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
                call = node.iter
                if isinstance(call.func, ast.Name) and call.func.id == "range" and len(call.args) == 2:
                    seg = ast.get_source_segment(source, call)
                    if seg and "-1" in seg and "0,k" not in seg:
                        out.append(_replace_node(source, call.args[1], "k"))
                        return out
        return []

    def _fix_assigned_alias_then_mutate_original(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Name) and node.value.id == "lst" and node.targets[0].id in {"sorted_lst", "lst_res"}:
                    out.append(_replace_node(source, node.value, "[]"))
                    return out
        return []

    def _fix_return_false_for_large_k(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is False:
                out.append(_replace_node(source, node.value, "[]"))
                return out
        return []