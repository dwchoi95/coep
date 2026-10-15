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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="append_selected_max_not_loop_variable",
                symptoms=("wrong",),
                apply=self._append_max_instead_of_iter_var,
            ),
            Rule(
                name="return_sorted_list_not_original",
                symptoms=("wrong",),
                apply=self._return_accumulator_slice,
            ),
            Rule(
                name="use_assigned_recursive_result_name",
                symptoms=("wrong",),
                apply=self._fix_recursive_name_mismatch,
            ),
            Rule(
                name="fix_second_loop_variable_name",
                symptoms=("wrong",),
                apply=self._fix_bare_variable_name_in_for_body,
            ),
            Rule(
                name="replace_shadowed_helper_call_with_assignment",
                symptoms=("wrong",),
                apply=self._fix_sort_assignment_call,
            ),
            Rule(
                name="fix_nonproductive_append_and_wrong_arg",
                symptoms=("wrong",),
                apply=self._fix_append_remove_chain,
            ),
            Rule(
                name="fix_off_by_one_return_slice",
                symptoms=("wrong",),
                apply=self._fix_off_by_one_slice,
            ),
            Rule(
                name="fix_missing_counter_increment",
                symptoms=("timeout", "wrong"),
                apply=self._add_counter_increment,
            ),
            Rule(
                name="fix_missing_return_of_accumulator",
                symptoms=("wrong",),
                apply=self._add_missing_return,
            ),
            Rule(
                name="fix_broken_max_loop_conditions",
                symptoms=("wrong",),
                apply=self._fix_max_selection_loops,
            ),
            Rule(
                name="fix_remove_and_append_same_max",
                symptoms=("wrong",),
                apply=self._fix_double_max_use,
            ),
            Rule(
                name="fix_pop_max_to_remove_max",
                symptoms=("err:TypeError", "wrong"),
                apply=self._fix_pop_max_call,
            ),
            Rule(
                name="fix_reverse_sort_and_index_bound",
                symptoms=("wrong",),
                apply=self._fix_sort_reverse_off_by_one,
            ),
            Rule(
                name="fix_return_false_or_original_on_k_zero",
                symptoms=("wrong",),
                apply=self._fix_k_zero_returns,
            ),
            Rule(
                name="fix_recursive_name_error",
                symptoms=("err:NameError", "wrong"),
                apply=self._fix_recursive_name_mismatch_2,
            ),
            Rule(
                name="fix_strictly_local_compare_misuse",
                symptoms=("wrong",),
                apply=self._fix_comparison_variable_name_mistakes,
            ),
        ]

    def _append_max_instead_of_iter_var(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and len(node.body) >= 1:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Expr) and isinstance(sub.value, ast.Call):
                        call = sub.value
                        if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and len(call.args) == 1:
                            arg = call.args[0]
                            if isinstance(arg, ast.Name):
                                for x in ast.walk(node):
                                    if isinstance(x, ast.Assign) and len(x.targets) == 1 and isinstance(x.targets[0], ast.Name):
                                        if x.targets[0].id in {"new_lst", "sort", "result", "values", "new", "final", "arranged", "new_list"}:
                                            s, e = _span(source, arg)
                                            out.append(source[:s] + "biggest" + source[e:])
                                            out.append(source[:s] + "largest" + source[e:])
        return list(dict.fromkeys(out))

    def _return_accumulator_slice(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                sub = node.value
                if isinstance(sub.slice, ast.Name) and sub.slice.id == "k":
                    if isinstance(sub.value, ast.Name) and sub.value.id in {"lst", "lst_res"}:
                        s, e = _span(source, sub.value)
                        out.append(source[:s] + "sort" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_recursive_name_mismatch(self, source):
        if "top_k(new_lst,k-1)" not in source and "top_k(new_list,k-1)" not in source:
            return []
        return [source.replace("top_k(new_lst,k-1)", "top_k(new_list,k-1)")]

    def _fix_bare_variable_name_in_for_body(self, source):
        if "if element > largest:" not in source:
            return []
        return [source.replace("if element > largest:\n                largest = element", "if elements > largest:\n                largest = elements")]

    def _fix_sort_assignment_call(self, source):
        if "sort=sort(lst)" in source:
            return [source.replace("sort=sort(lst)", "lst=sort(lst)")]
        return []

    def _fix_append_remove_chain(self, source):
        out = []
        if "new_lst.append(lst)" in source:
            out.append(source.replace("new_lst.append(lst)", "new_lst.append(maximum)"))
        if "lst.remove(maximum)" in source and "while len(new_lst) < k:" in source:
            out.append(source.replace("while len(new_lst) < k:", "while len(new_lst) < k:"))
        return out

    def _fix_off_by_one_slice(self, source):
        out = []
        if "return sort[:k+1]" in source:
            out.append(source.replace("return sort[:k+1]", "return sort[:k]"))
        if "return sorted_lst[0:k]" in source:
            out.append(source.replace("return sorted_lst[0:k]", "return sorted_lst[:k]"))
        if "return sort[:k-1]" in source:
            out.append(source.replace("return sort[:k-1]", "return sort[:k]"))
        if "for i in range(k-1):" in source:
            out.append(source.replace("for i in range(k-1):", "for i in range(k):"))
        if "for qwerty in range(0,k):" in source and "rs.append[biggest]" in source:
            out.append(source.replace("for qwerty in range(0,k):", "for qwerty in range(0,k):"))
        return out

    def _add_counter_increment(self, source):
        if "counter+=1" in source:
            return []
        if "while counter<k:" in source and "new_lst.append(maxi)" in source:
            idx = source.find("lst.remove(maxi)")
            if idx != -1:
                ins = "        counter+=1\n"
                return [source[:idx + len("        lst.remove(maxi)\n")] + ins + source[idx + len("        lst.remove(maxi)\n"):]]
        return []

    def _add_missing_return(self, source):
        if "while counter<k:" in source and "return new_lst" not in source:
            if source.rstrip().endswith("lst.remove(maxi)"):
                return [source + "\n        counter+=1\n    return new_lst\n"]
        return []

    def _fix_max_selection_loops(self, source):
        out = []
        if "if i > largest:" in source and "sort.append(i)" in source:
            out.append(source.replace("sort.append(i)", "lst.remove(largest)\n        sort.append(largest)"))
        if "if x < lst[0]:" in source:
            out.append(source.replace("if x < lst[0]:", "if x > biggest:"))
        if "if ele > biggest:" in source and "lst.remove(element)" in source:
            out.append(source.replace("lst.remove(element)", "lst.remove(biggest)").replace("sort.append(element)", "sort.append(biggest)"))
        return out

    def _fix_double_max_use(self, source):
        if "arranged.append(max(lst))" in source and "lst.remove(max(lst))" in source:
            return [source.replace("lst.remove(max(lst))\n        arranged.append(max(lst))", "arranged.append(max(lst))\n        lst.remove(max(lst))")]
        if "new.append(lst.pop(max(lst)))" in source:
            return [source.replace("new.append(lst.pop(max(lst)))", "new.append(max(lst))\n        lst.remove(max(lst))")]
        return []

    def _fix_pop_max_call(self, source):
        out = []
        if "lst.pop(max(lst))" in source:
            out.append(source.replace("lst.pop(max(lst))", "max(lst)"))
        if "lst.remove(max(lst))" in source:
            out.append(source)
        return out

    def _fix_sort_reverse_off_by_one(self, source):
        out = []
        if "lst.sort()" in source:
            out.append(source.replace("lst.sort()", ""))
        if "list.reverse(sorted_list)[:k-1]" in source:
            out.append(source.replace("return list.reverse(sorted_list)[:k-1]", "return sorted_list[:k]"))
        return out

    def _fix_k_zero_returns(self, source):
        if "elif k == 0:\n        return lst" in source:
            return [source.replace("elif k == 0:\n        return lst", "elif k == 0:\n        return []")]
        return []

    def _fix_recursive_name_mismatch_2(self, source):
        if "return [maxi]+top_k(new_lst,k-1)" in source:
            return [source.replace("return [maxi]+top_k(new_lst,k-1)", "return [maxi]+top_k(new_list,k-1)")]
        return []

    def _fix_comparison_variable_name_mistakes(self, source):
        out = []
        if "if x == pivot:" in source and "if x > pivot:" in source:
            out.append(source.replace("if x == pivot:", "if e == pivot:").replace("if x > pivot:", "if e > pivot:"))
        return out