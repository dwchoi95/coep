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


def _name(source, node):
    return source[_span(source, node)[0]:_span(source, node)[1]]


def _replace_node(source, target, new_text):
    return _splice(source, target, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(name="append_wrong_variable_after_max", apply=self._append_wrong_variable_after_max, symptoms=("wrong",)),
            Rule(name="append_wrong_variable_after_remove", apply=self._append_wrong_variable_after_remove, symptoms=("wrong",)),
            Rule(name="typo_oldest_or_element_vs_biggest", apply=self._typo_oldest_or_element_vs_biggest, symptoms=("wrong",)),
            Rule(name="remove_result_of_remove", apply=self._remove_result_of_remove, symptoms=("wrong",)),
            Rule(name="fix_return_slice_bound", apply=self._fix_return_slice_bound, symptoms=("wrong",)),
            Rule(name="fix_recursive_call_variable", apply=self._fix_recursive_call_variable, symptoms=("wrong",)),
            Rule(name="fix_pop_call_parentheses", apply=self._fix_pop_call_parentheses, symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_list_append_call_brackets", apply=self._fix_list_append_call_brackets, symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_list_remove_call_brackets", apply=self._fix_list_remove_call_brackets, symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_off_by_one_range_stop", apply=self._fix_off_by_one_range_stop, symptoms=("wrong", "timeout")),
            Rule(name="fix_while_le_to_lt", apply=self._fix_while_le_to_lt, symptoms=("wrong", "timeout")),
            Rule(name="fix_while_ge_to_gt_zero", apply=self._fix_while_ge_to_gt_zero, symptoms=("wrong", "timeout")),
            Rule(name="fix_missing_counter_increment", apply=self._fix_missing_counter_increment, symptoms=("timeout", "wrong")),
            Rule(name="fix_max_remove_append_sequence", apply=self._fix_max_remove_append_sequence, symptoms=("wrong",)),
            Rule(name="fix_sort_function_call_shadowing", apply=self._fix_sort_function_call_shadowing, symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_sort_result_name_mismatch", apply=self._fix_sort_result_name_mismatch, symptoms=("err:NameError", "wrong")),
            Rule(name="fix_return_list_when_k_zero", apply=self._fix_return_list_when_k_zero, symptoms=("wrong",)),
            Rule(name="fix_double_for_bubble_bound", apply=self._fix_double_for_bubble_bound, symptoms=("wrong",)),
        ]

    def _append_wrong_variable_after_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and call.args:
                    arg = call.args[0]
                    if isinstance(arg, ast.Name) and arg.id in {"numbers", "number", "i", "element", "elements", "x", "item", "largest", "biggest", "maximum", "maxi"}:
                        out.append(_replace_node(source, arg, "biggest"))
                    elif isinstance(arg, ast.Name) and arg.id == "oldest":
                        out.append(_replace_node(source, arg, "biggest"))
        return out

    def _append_wrong_variable_after_remove(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and call.args:
                    arg = call.args[0]
                    if isinstance(arg, ast.Name) and arg.id in {"numbers", "number", "i", "element", "elements", "x", "item"}:
                        out.append(_replace_node(source, arg, "biggest"))
        return out

    def _typo_oldest_or_element_vs_biggest(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"oldest", "oldest ", "elem", "ele"}:
                out.append(_replace_node(source, node, "biggest"))
            if isinstance(node, ast.Name) and node.id == "element":
                parent = None
                for p in ast.walk(tree):
                    for ch in ast.iter_child_nodes(p):
                        if ch is node:
                            parent = p
                if isinstance(parent, ast.Compare):
                    out.append(_replace_node(source, node, "elements"))
        return out

    def _remove_result_of_remove(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "remove":
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        out.append(_replace_node(source, node, f"{target.id} = {source[_span(source, call.func.value)[0]:_span(source, call.func.value)[1]]}"))
        return out

    def _fix_return_slice_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Add):
                if isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 1:
                    out.append(_replace_node(source, node.slice.right, "0"))
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == 5:
                out.append(_replace_node(source, node.slice, "k"))
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Sub):
                if isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 1:
                    out.append(_replace_node(source, node.slice.right, "0"))
        return out

    def _fix_recursive_call_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "top_k" and len(node.args) == 2:
                if isinstance(node.args[0], ast.Name) and node.args[0].id in {"new_lst", "new_list", "newlst", "new_lst2", "new_list_2", "new_list2"}:
                    out.append(_replace_node(source, node.args[0], "new_list"))
        return out

    def _fix_pop_call_parentheses(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "pop":
                out.append(_replace_node(source, node, f"{source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]]}.pop({source[_span(source, node.slice)[0]:_span(source, node.slice)[1]]})"))
        return out

    def _fix_list_append_call_brackets(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "append":
                out.append(_replace_node(source, node, f"{source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]]}.append({source[_span(source, node.slice)[0]:_span(source, node.slice)[1]]})"))
        return out

    def _fix_list_remove_call_brackets(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "remove":
                out.append(_replace_node(source, node, f"{source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]]}.remove({source[_span(source, node.slice)[0]:_span(source, node.slice)[1]]})"))
        return out

    def _fix_off_by_one_range_stop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                    out.append(_replace_node(source, arg.right, "0"))
        return out

    def _fix_while_le_to_lt(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
                out.append(_replace_node(source, node, source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " < " + source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]))
        return out

    def _fix_while_ge_to_gt_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                out.append(_replace_node(source, node, source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " > " + source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]))
        return out

    def _fix_missing_counter_increment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                body = node.body
                if body and isinstance(body[-1], ast.Expr):
                    txt = source[_span(source, body[-1])[0]:_span(source, body[-1])[1]]
                    if "counter" not in txt and any(isinstance(n, ast.Name) and n.id == "counter" for n in ast.walk(node.test)):
                        insert_at = _span(source, body[-1])[1]
                        out.append(source[:insert_at] + "\n        counter += 1" + source[insert_at:])
        return out

    def _fix_max_remove_append_sequence(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "max":
                if isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                    if name in {"maximum", "maxi", "big", "largest", "highest"}:
                        out.append(_replace_node(source, node, f"{name} = max(lst)"))
        return out

    def _fix_sort_function_call_shadowing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == node.targets[0].id:
                    out.append(_replace_node(source, node.value.func, "sort"))
        return out

    def _fix_sort_result_name_mismatch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"new_lst", "newlst", "sort_lst", "sort_list"}:
                out.append(_replace_node(source, node, "result"))
        return out

    def _fix_return_list_when_k_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "lst":
                out.append(_replace_node(source, node.value, "[]"))
        return out

    def _fix_double_for_bubble_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                if len(node.iter.args) == 1:
                    arg = node.iter.args[0]
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "len":
                        out.append(_replace_node(source, node.iter, f"range(len({source[_span(source, arg.args[0])[0]:_span(source, arg.args[0])[1]]}))"))
        return out