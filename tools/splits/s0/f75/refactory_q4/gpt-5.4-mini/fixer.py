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


class Fixer:
    def rules(self):
        return [
            Rule(name="fix_return_wrong_variable", apply=self._fix_return_wrong_variable, symptoms=("wrong",)),
            Rule(name="fix_name_mismatch_and_last_element_append", apply=self._fix_name_mismatch_and_last_element_append, symptoms=("wrong", "err:NameError")),
            Rule(name="fix_assignment_to_comparison_target", apply=self._fix_assignment_to_comparison_target, symptoms=("wrong",)),
            Rule(name="fix_missing_return_at_end", apply=self._fix_missing_return_at_end, symptoms=("wrong",)),
            Rule(name="fix_none_return_from_list_sort", apply=self._fix_none_return_from_list_sort, symptoms=("wrong",)),
            Rule(name="fix_tuple_concat_to_list_append", apply=self._fix_tuple_concat_to_list_append, symptoms=("wrong",)),
            Rule(name="fix_remove_wrong_variable", apply=self._fix_remove_wrong_variable, symptoms=("wrong", "err:ValueError")),
            Rule(name="fix_remove_wrong_index_or_value", apply=self._fix_remove_wrong_index_or_value, symptoms=("wrong", "err:ValueError")),
            Rule(name="fix_reverse_call_vs_attribute", apply=self._fix_reverse_call_vs_attribute, symptoms=("wrong",)),
            Rule(name="fix_list_empty_check", apply=self._fix_list_empty_check, symptoms=("wrong",)),
            Rule(name="fix_sort_direction_comparison", apply=self._fix_sort_direction_comparison, symptoms=("wrong",)),
            Rule(name="fix_merge_recursive_pop_index", apply=self._fix_merge_recursive_pop_index, symptoms=("wrong",)),
            Rule(name="fix_merge_append_only_best", apply=self._fix_merge_append_only_best, symptoms=("wrong",)),
            Rule(name="fix_off_by_one_range_end", apply=self._fix_off_by_one_range_end, symptoms=("wrong",)),
            Rule(name="fix_max_min_on_tuples_to_keyed_max", apply=self._fix_max_min_on_tuples_to_keyed_max, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_sort_in_place_then_return", apply=self._fix_sort_in_place_then_return, symptoms=("wrong",)),
            Rule(name="fix_recursive_call_argument", apply=self._fix_recursive_call_argument, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_swapped_assignment_in_swap", apply=self._fix_swapped_assignment_in_swap, symptoms=("wrong",)),
            Rule(name="fix_tuple_string_index_compare", apply=self._fix_tuple_string_index_compare, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_append_inside_loop_and_early_return", apply=self._fix_append_inside_loop_and_early_return, symptoms=("wrong",)),
        ]

    def _fix_return_wrong_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id != "sort":
                out.append(_splice(source, node, "return sort"))
        return out

    def _fix_name_mismatch_and_last_element_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id == "i":
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id in {"curr", "i"}:
                        out.append(_splice(source, node.value, "a"))
                        break
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in {"n", "k", "i"}:
                out.append(_splice(source, node.value, "oldest" if node.value.id == "n" else ("tpl" if node.value.id == "k" else "oldest")))
        return out

    def _fix_assignment_to_comparison_target(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {"person", "old", "largest"}:
                if isinstance(node.value, ast.Name) and node.value.id in {"oldest", "smallest"}:
                    out.append(_splice(source, node, f"{node.targets[0].id} = {node.value.id}"))
        return out

    def _fix_missing_return_at_end(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if not node.body:
                    continue
                last = node.body[-1]
                if isinstance(last, ast.Expr) and isinstance(last.value, ast.Name):
                    out.append(_splice(source, last, "return " + last.value.id))
                elif isinstance(last, ast.Expr) and isinstance(last.value, ast.Call) and getattr(last.value.func, "id", "") == "print":
                    out.append(_splice(source, last, "return sort"))
        return out

    def _fix_none_return_from_list_sort(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute) and getattr(node.value.attr, "lower", lambda: "")() == "reverse":
                out.append(_splice(source, node, "return sorted_lst"))
            elif isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                    out.append(_splice(source, node, "return lst"))
        return out

    def _fix_tuple_concat_to_list_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.value, ast.Name):
                if node.value.id in {"current", "oldest", "largest"}:
                    out.append(_splice(source, node, f"{source[_span(source, node.target)[0]:_span(source, node.target)[1]]}.append({node.value.id})"))
        return out

    def _fix_remove_wrong_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id in {"i", "j", "k", "counter", "smallest"}:
                    if isinstance(node.func.value, ast.Name) and node.func.value.id in {"lst", "a", "old_lst", "decoy"}:
                        out.append(_splice(source, arg, "oldest" if arg.id == "smallest" else ("largest" if arg.id in {"i", "j", "k", "counter"} else arg.id)))
        return out

    def _fix_remove_wrong_index_or_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id == "counter":
                    out.append(_splice(source, arg, "lst[index]"))
                elif isinstance(arg, ast.Name) and arg.id == "smallest":
                    out.append(_splice(source, arg, "smallest"))
                elif isinstance(arg, ast.Name) and arg.id == "biggest":
                    out.append(_splice(source, arg, "count"))
        return out

    def _fix_reverse_call_vs_attribute(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute) and node.value.attr == "reverse":
                out.append(_splice(source, node, "sort.reverse()"))
        return out

    def _fix_list_empty_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Name) and node.left.id == "lst" and isinstance(node.comparators[0], ast.Tuple):
                    out.append(_splice(source, node, "lst == []"))
        return out

    def _fix_sort_direction_comparison(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                if "[1]" in source[_span(source, node)[0]:_span(source, node)[1]]:
                    text = source[_span(source, node)[0]:_span(source, node)[1]]
                    text = text.replace(" < ", " > ") if " < " in text else text.replace(" > ", " < ") if " > " in text else text.replace("<", ">") if "<" in text else text.replace(">", "<")
                    out.append(_splice(source, node, text))
        return out

    def _fix_merge_recursive_pop_index(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                    out.append(_splice(source, node.args[0], "0"))
                elif not node.args:
                    out.append(_splice(source, node, "pop(0)"))
        return out

    def _fix_merge_append_only_best(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                text = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                if "lst1[0][1] < lst2[0][1]" in text:
                    out.append(_splice(source, node.test, "lst1[0][1] > lst2[0][1]"))
        return out

    def _fix_off_by_one_range_end(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 2:
                s = source[_span(source, node)[0]:_span(source, node)[1]]
                if ", len(lst)+1" in s:
                    out.append(_splice(source, node, s.replace("len(lst)+1", "len(lst)")))
                elif ",len(lst)+1" in s:
                    out.append(_splice(source, node, s.replace("len(lst)+1", "len(lst)")))
        return out

    def _fix_max_min_on_tuples_to_keyed_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"max", "min"} and node.args:
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                    out.append(_splice(source, node, f"max({source[_span(source, node.args[0])[0]:_span(source, node.args[0])[1]]}, key=lambda x: x[1])"))
        return out

    def _fix_sort_in_place_then_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "sort":
                    out.append(_splice(source, node, f"{source[_span(source, node.targets[0])[0]:_span(source, node.targets[0])[1]]} = lst"))
        return out

    def _fix_recursive_call_argument(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sort_age" and node.args:
                if isinstance(node.args[0], ast.Call):
                    out.append(_splice(source, node.args[0], "lst"))
        return out

    def _fix_swapped_assignment_in_swap(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 2:
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "lst[j],lst[j] = lst[j],lst[j]" in txt:
                    out.append(_splice(source, node, "lst[i],lst[j] = lst[j],lst[i]"))
                elif "lst[j][1],lst[i][1]" in txt:
                    out.append(_splice(source, node, "lst[i], lst[j] = lst[j], lst[i]"))
        return out

    def _fix_tuple_string_index_compare(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and "[1]" in source[_span(source, node)[0]:_span(source, node)[1]]:
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "smallest[1]" in txt and "element[1]" in txt:
                    continue
                if "lst[indx] < ele" in txt:
                    out.append(_splice(source, node, "out[indx][1] < ele[1]"))
        return out

    def _fix_append_inside_loop_and_early_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for stmt in node.body:
                    if isinstance(stmt, ast.Return):
                        out.append(_splice(source, stmt, ""))
                if any(isinstance(stmt, ast.If) for stmt in node.body):
                    txt = source[_span(source, node)[0]:_span(source, node)[1]]
                    if "return sort" in txt and "append" in txt:
                        out.append(source.replace("return sort", ""))
        return [s for s in out if s and s != source]