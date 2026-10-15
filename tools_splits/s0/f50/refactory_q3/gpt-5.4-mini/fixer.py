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
            Rule(name="use_function_parameter_in_loop", apply=self._use_param_in_for, symptoms=("wrong", "err:NameError")),
            Rule(name="use_output_list_for_membership", apply=self._use_output_for_membership, symptoms=("wrong", "err:NameError")),
            Rule(name="append_instead_of_extend_scalar", apply=self._extend_to_append, symptoms=("wrong", "err:TypeError")),
            Rule(name="insert_zero_to_append", apply=self._insert_to_append, symptoms=("wrong", "err:TypeError")),
            Rule(name="return_list_not_reverse_result", apply=self._fix_reverse_return, symptoms=("wrong",)),
            Rule(name="return_after_loop_not_inside", apply=self._dedent_early_return, symptoms=("wrong",)),
            Rule(name="fix_ordered_dict_return_list", apply=self._wrap_ordereddict_list, symptoms=("wrong",)),
            Rule(name="replace_set_with_ordered_dict", apply=self._set_to_ordereddict, symptoms=("wrong",)),
            Rule(name="replace_not_equal_list_with_membership", apply=self._neq_list_to_not_in, symptoms=("wrong",)),
            Rule(name="fix_empty_check_return_none", apply=self._empty_return_none, symptoms=("wrong",)),
            Rule(name="fix_copy_slicing_left_side", apply=self._copy_slice_left, symptoms=("wrong",)),
            Rule(name="fix_variable_name_seen_output", apply=self._seen_to_output, symptoms=("wrong", "err:NameError")),
            Rule(name="fix_function_call_paren_index", apply=self._call_zero_to_index_zero, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_pop_on_enumeration", apply=self._pop_index_to_value, symptoms=("wrong", "err:TypeError")),
            Rule(name="remove_sort_before_dedup", apply=self._remove_sort, symptoms=("wrong",)),
            Rule(name="fix_count_compare_truth", apply=self._count_gt_one_to_not_in, symptoms=("wrong",)),
            Rule(name="fix_list_append_assignment", apply=self._fix_append_assignment, symptoms=("wrong", "err:AttributeError", "err:TypeError")),
            Rule(name="fix_count_loop_return_and_offbyone", apply=self._fix_count_loop_patterns, symptoms=("wrong",)),
            Rule(name="fix_reverse_method_calls", apply=self._fix_reverse_method_calls, symptoms=("wrong", "err:AttributeError")),
        ]

    def _use_param_in_for(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list" and isinstance(node.target, ast.Name):
                s, e = _span(source, node.iter)
                out.append(source[:s] + "lst" + source[e:])
        return out

    def _use_output_for_membership(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"lst", "list"}:
                    left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    s, e = _span(source, node.comparators[0])
                    out.append(source[:s] + "output" + source[e:] if left.strip() != "output" else source)
        return [x for x in out if x != source]

    def _extend_to_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend" and len(node.args) == 1:
                s, e = _span(source, node.func)
                out.append(source[:s] + source[s:e].replace("extend", "append") + source[e:])
        return out

    def _insert_to_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "insert" and len(node.args) >= 2:
                s, e = _span(source, node.func)
                out.append(source[:s] + source[s:e].replace("insert", "append") + source[e:])
        return out

    def _fix_reverse_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                s, e = _span(source, node.value)
                out.append(source[:s] + source[s:e].replace(".reverse()", "") + source[e:])
        return out

    def _dedent_early_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                parent = getattr(node, "parent", None)
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(getattr(node, "parent", None), ast.For):
                line = source.splitlines(keepends=True)[node.lineno - 1]
                indent = len(line) - len(line.lstrip())
                if indent >= 4:
                    s = sum(len(l) for l in source.splitlines(keepends=True)[:node.lineno - 1]) + node.col_offset - 4
                    e = s + 4
                    out.append(source[:s] + source[e:] + "    ")
        return []

    def _wrap_ordereddict_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fromkeys":
                parent = None
                if isinstance(getattr(node, "parent", None), ast.Call):
                    parent = node.parent
                s, e = _span(source, node)
                out.append(source[:s] + "list(" + source[s:e] + ")" + source[e:])
        return out

    def _set_to_ordereddict(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "set" and len(node.args) == 1:
                s, e = _span(source, node)
                out.append(source[:s] + "OrderedDict.fromkeys(" + source[_span(source, node.args[0])[0]:_span(source, node.args[0])[1]] + ")" + source[e:])
        return out

    def _neq_list_to_not_in(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
                s, e = _span(source, node)
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                out.append(source[:s] + f"{left} not in {right}" + source[e:])
        return out

    def _empty_return_none(self, source):
        return [source.replace("return None", "return lst")] if "return None" in source and "def remove_extras(" in source else []

    def _copy_slice_left(self, source):
        if "left = lst[" in source and "copy.index(i)" in source:
            return [source.replace("left = lst[:copy.index(i)+1]", "left = copy[:copy.index(i)+1]")]
        return []

    def _seen_to_output(self, source):
        out = source
        changed = False
        for bad in ["seen", "newlist", "new_list", "new", "output"]:
            pass
        if "seen" in out and "not in seen" in out:
            out = out.replace("seen", "output")
            changed = True
        if "newlist" in out and "not in newlist" in out:
            out = out.replace("newlist", "output")
            changed = True
        if "new_list" in out and "not in new_list" in out:
            out = out.replace("new_list", "output")
            changed = True
        return [out] if changed else []

    def _call_zero_to_index_zero(self, source):
        return [source.replace("lst(0)", "[]")] if "lst(0)" in source else []

    def _pop_index_to_value(self, source):
        if ".pop(i)" in source:
            return [source.replace(".pop(i)", ".pop()")]
        return []

    def _remove_sort(self, source):
        return [source.replace("lst.sort()\n", "")] if "lst.sort()" in source else []

    def _count_gt_one_to_not_in(self, source):
        if "count(" in source and "> 1" in source:
            return [source.replace("if lst.count(i) > 1:", "if i not in new_list:").replace("if lst.count(x) > 1:", "if x not in new:")]
        return []

    def _fix_append_assignment(self, source):
        out = source
        changed = False
        if ".append(" in out and "=" in out:
            out = out.replace("removed = removed.append(e)", "removed.append(e)")
            out = out.replace("new_lst.append(i)\n        if new_lst.count(i) > 1:\n            new_lst.pop", "if i not in new_lst:\n            new_lst.append(i)")
            changed = True
        return [out] if changed else []

    def _fix_count_loop_patterns(self, source):
        if "return my_lst" in source and "return my_lst" in source:
            return [source.replace("        return my_lst\n", "")]
        if "for i in lst and not result" in source:
            return [source.replace("for i in lst and not result:", "for i in lst:").replace("result += result + i", "result += [i]")]
        return []

    def _fix_reverse_method_calls(self, source):
        out = source
        if "lst.reverse" in out:
            out = out.replace("lst.reverse", "lst.reverse()")
        if "return lst1.reverse()" in out:
            out = out.replace("return lst1.reverse()", "return lst1")
        return [out] if out != source else []