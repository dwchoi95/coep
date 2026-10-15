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


def _replace_node(source, tree, old, new_text):
    return _splice(source, old, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(name="wrong_return_variable_or_missing_return", apply=self._fix_returns, symptoms=("wrong", "err:NameError", "err:UnboundLocalError")),
            Rule(name="list_remove_should_use_selected_element", apply=self._fix_remove_selected, symptoms=("wrong", "err:ValueError", "err:TypeError")),
            Rule(name="append_wrong_loop_variable", apply=self._fix_append_loop_var, symptoms=("wrong",)),
            Rule(name="assignment_instead_of_update_target", apply=self._fix_assignment_target, symptoms=("wrong",)),
            Rule(name="compare_to_name_not_selected_item", apply=self._fix_compare_name, symptoms=("wrong", "err:NameError")),
            Rule(name="recursive_missing_base_case_empty", apply=self._fix_base_case, symptoms=("wrong",)),
            Rule(name="reverse_should_be_called_not_returned", apply=self._fix_reverse_call, symptoms=("wrong",)),
            Rule(name="tuple_append_or_concat_mistake", apply=self._fix_tuple_concat, symptoms=("wrong", "err:TypeError")),
            Rule(name="index_off_by_one_in_loop", apply=self._fix_off_by_one, symptoms=("wrong", "err:IndexError")),
            Rule(name="bubble_sort_direction_flip", apply=self._fix_bubble_compare, symptoms=("wrong",)),
            Rule(name="selection_sort_swap_and_target", apply=self._fix_selection_swap, symptoms=("wrong",)),
        ]

    def _fix_returns(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = ast.get_source_segment(source, node)
                if txt and "return sort" in txt and "sortt" in source:
                    out.append(source.replace("return sort", "return sortt", 1))
                if txt and "return final" in txt and "final" in source and "sort =" in source:
                    out.append(source.replace("return final", "return sort", 1))
                if txt and "return sort_list.reverse()" in txt:
                    out.append(source.replace("return sort_list.reverse()", "sort_list.reverse()\n    return sort_list", 1))
                if txt and "return new.reverse()" in txt:
                    out.append(source.replace("return new.reverse()", "return new", 1))
                if txt and "return list.reverse(lst)" in txt:
                    out.append(source.replace("return list.reverse(lst)", "return lst[::-1]", 1))
                if txt and "pass" in source and "return" not in source.split(txt)[0].splitlines()[-1]:
                    pass
        return list(dict.fromkeys(out))

    def _fix_remove_selected(self, source):
        if "lst.remove(i)" in source and "append(i)" in source:
            return [source.replace("lst.remove(i)", "lst.remove(curr)" if "curr" in source else "lst.remove(oldest)" if "oldest" in source else "lst.remove(smallest)").replace("append(i)", "append(curr)" if "curr" in source else "append(oldest)" if "oldest" in source else "append(smallest)")]
        if "lst.remove(biggest)" in source and "biggest = i[1]" in source:
            return [source.replace("lst.remove(biggest)", "lst.remove(i)").replace("sort.append(biggest)", "sort.append(i)")]
        if "lst.remove(tpl)" in source and "j = tpl" in source:
            return [source.replace("j = tpl", "tpl = j")]
        if "a.remove(oldest)" in source and "lst.remove(oldest)" not in source:
            return [source.replace("a.remove(oldest)", "lst.remove(oldest)")]
        if "lst.remove(smallest)" in source and "smallest = i[1]" in source:
            return [source.replace("lst.remove(smallest)", "lst.remove(next(x for x in lst if x[1] == smallest))").replace("new.append(smallest)", "new.append(next(x for x in lst if x[1] == smallest))")]
        return []

    def _fix_append_loop_var(self, source):
        reps = []
        if "sort.append(i)" in source and "lst.remove(i)" in source:
            reps.append(source.replace("lst.remove(i)\n        sort.append(i)", "lst.remove(oldest)\n        sort.append(oldest)"))
        if "final.append(i)" in source and "lst.remove(i)" in source:
            reps.append(source.replace("lst.remove(i)\n        final.append(i)", "lst.remove(i)\n        final.append(i)"))
        if "list1.append(biggest)" in source and "biggest = i[1]" in source:
            reps.append(source.replace("list1.append(biggest)", "list1.append(i)"))
        if "new_list = new_list.append(count)" in source:
            reps.append(source.replace("new_list=new_list.append(count)", "new_list=new_list+[count]"))
        if "newlst += current" in source:
            reps.append(source.replace("newlst += current", "newlst += (current,)"))
        return reps

    def _fix_assignment_target(self, source):
        out = []
        if "person = oldest" in source:
            out.append(source.replace("person = oldest", "oldest = person"))
        if "j = tpl" in source:
            out.append(source.replace("j = tpl", "tpl = j"))
        if "if i[1] > oldest[1]:\n                person = oldest" in source:
            out.append(source.replace("person = oldest", "oldest = person"))
        if "if i[1] < minimum[1]:\n                    minimum = x" in source:
            out.append(source.replace("minimum = x", "minimum = i"))
        return out

    def _fix_compare_name(self, source):
        out = []
        if "element[1] > smallest[1]" in source and "smallest=" in source:
            out.append(source.replace("smallest[1]", "biggest[1]").replace("biggest = element", "smallest = element"))
        if "if i[1] < smallsest[1]" in source:
            out.append(source.replace("smallsest", "smallest"))
        if "if element > smallest" in source:
            out.append(source.replace("element > smallest", "element[1] > smallest[1]"))
        return out

    def _fix_base_case(self, source):
        out = []
        if "if len(lst) == 1:" in source:
            out.append(source.replace("if len(lst) == 1:", "if len(lst) <= 1:"))
        if "if lst==[]:\n        return new" in source:
            out.append(source.replace("if lst == []:\n        return new", "if lst == []:\n        return []"))
        return out

    def _fix_reverse_call(self, source):
        if ".reverse()" in source:
            return [source.replace("return sort_list.reverse()", "sort_list.reverse()\n    return sort_list").replace("return new.reverse()", "return new")]
        if "reverse" in source and "return new.reverse()" in source:
            return [source.replace("return new.reverse()", "new.reverse()\n    return new")]
        return []

    def _fix_tuple_concat(self, source):
        out = []
        if "result += current" in source:
            out.append(source.replace("result += current", "result += (current,)"))
        if "list1 += current" in source:
            out.append(source.replace("list1 += current", "list1 += (current,)"))
        if "result = (x,) + result" in source and "return result" in source:
            out.append(source)
        return out

    def _fix_off_by_one(self, source):
        out = []
        if "range(1,len(lst)+1)" in source:
            out.append(source.replace("range(1,len(lst)+1)", "range(1,len(lst))"))
        if "for i in range(len(lst)):\n        if lst[i][1]> lst[i+1][1]:" in source:
            out.append(source.replace("for i in range(len(lst)):\n        if lst[i][1]> lst[i+1][1]:", "for i in range(len(lst)-1):\n        if lst[i][1]> lst[i+1][1]:"))
        return out

    def _fix_bubble_compare(self, source):
        out = []
        if "if lst[i][1] < lst[i+1][1]:" in source and "lst[i], lst[i+1] = lst[i+1], lst[i]" in source:
            out.append(source.replace("if lst[i][1] < lst[i+1][1]:", "if lst[i][1] > lst[i+1][1]:"))
        if "if lst[j][1] < lst[j+1][1]:" in source and "lst[j][1], lst[j+1][1]" in source:
            out.append(source.replace("if lst[j][1] < lst[j+1][1]:", "if lst[j][1] > lst[j+1][1]:"))
        return out

    def _fix_selection_swap(self, source):
        out = []
        if "lst[i]= lst[a]\n                lst[a]= lst[i]" in source:
            out.append(source.replace("lst[i]= lst[a]\n                lst[a]= lst[i]", "lst[i], lst[a] = lst[a], lst[i]"))
        if "lst[i]=lst[j]\n                lst[j]= lst[i]" in source:
            out.append(source.replace("lst[i]= lst[a]\n                lst[a]= lst[i]", "lst[i], lst[a] = lst[a], lst[i]"))
        if "lst[i],lst[j] = lst[j],lst[j]" in source:
            out.append(source.replace("lst[i],lst[j] = lst[j],lst[j]", "lst[i],lst[j] = lst[j],lst[i]"))
        return out