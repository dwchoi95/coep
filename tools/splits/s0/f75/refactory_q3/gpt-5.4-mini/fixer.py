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


def _expr_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


class Fixer:
    def rules(self):
        return [
            Rule("wrong_return_name", self._wrong_return_name, ("wrong",)),
            Rule("wrong_list_target_in_membership", self._wrong_list_target_in_membership, ("wrong",)),
            Rule("wrong_output_variable", self._wrong_output_variable, ("wrong",)),
            Rule("wrong_append_target_name", self._wrong_append_target_name, ("wrong",)),
            Rule("wrong_loop_iterable_name", self._wrong_loop_iterable_name, ("wrong",)),
            Rule("wrong_loop_var_name", self._wrong_loop_var_name, ("wrong",)),
            Rule("wrong_operand_name", self._wrong_operand_name, ("wrong",)),
            Rule("wrong_function_name_multiple", self._wrong_function_name_multiple, ("wrong",)),
            Rule("ordered_dict_missing_import", self._ordered_dict_missing_import, ("wrong",)),
            Rule("set_to_ordered_dict", self._set_to_ordered_dict, ("wrong",)),
            Rule("list_to_list_of_ordereddict", self._list_to_list_of_ordereddict, ("wrong",)),
            Rule("tuple_accumulator_to_list", self._tuple_accumulator_to_list, ("wrong",)),
            Rule("tuple_concat_missing_comma", self._tuple_concat_missing_comma, ("wrong",)),
            Rule("insert_zero_to_append", self._insert_zero_to_append, ("wrong",)),
            Rule("append_call_instead_of_method", self._append_call_instead_of_method, ("wrong",)),
            Rule("extend_to_append_for_scalars", self._extend_to_append_for_scalars, ("wrong",)),
            Rule("append_result_of_append", self._append_result_of_append, ("wrong",)),
            Rule("sort_not_needed_remove_extras", self._sort_not_needed_remove_extras, ("wrong",)),
            Rule("sort_reverse_name", self._sort_reverse_name, ("wrong",)),
            Rule("off_by_one_range_end", self._off_by_one_range_end, ("wrong",)),
            Rule("while_missing_else_increment", self._while_missing_else_increment, ("wrong",)),
            Rule("skip_return_none_empty", self._skip_return_none_empty, ("wrong",)),
            Rule("loop_over_function_name", self._loop_over_function_name, ("wrong",)),
            Rule("membership_against_input_list", self._membership_against_input_list, ("wrong",)),
            Rule("comparison_instead_of_membership", self._comparison_instead_of_membership, ("wrong",)),
        ]

    def _wrong_return_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        func = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "remove_extras"), None)
        if not func:
            return []
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id != "output":
                text = _expr_text(source, node.value)
                if text in {"lst", "x", "i", "new_list", "newlst", "new_list ", "newseq", "new_list\n"}:
                    out.append(_splice(source, node.value, "output"))
        return out

    def _wrong_list_target_in_membership(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"lst", "list", "values"}:
                    out.append(_splice(source, node.comparators[0], "new_list"))
                if isinstance(node.left, ast.Name) and node.left.id in {"lst", "list"}:
                    out.append(_splice(source, node.left, "i"))
        return out

    def _wrong_output_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "output":
                        continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "new_list":
                    out.append(_splice(source, node, "new_lst"))
        return list(dict.fromkeys(out))

    def _wrong_append_target_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "append":
                if isinstance(node.value, ast.Name) and node.value.id in {"new_list", "newlst", "newseq", "new_list "}:
                    out.append(_splice(source, node.value, "new_lst"))
        return out

    def _wrong_loop_iterable_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Name) and node.iter.id in {"list", "new_lst"}:
                    out.append(_splice(source, node.iter, "lst"))
        return out

    def _wrong_loop_var_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.target, ast.Name) and node.target.id in {"list", "new_lst", "new_lst "}:
                    out.append(_splice(source, node.target, "i"))
        return out

    def _wrong_operand_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"n", "x", "values", "value", "element"}:
                out.append(_splice(source, node, "i" if node.id != "values" else "lst"))
        return out

    def _wrong_function_name_multiple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "remove_mutiple":
                out.append(_splice(source, node, "remove_multiple"))
        return out

    def _ordered_dict_missing_import(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        if "OrderedDict" not in source or "from collections import OrderedDict" in source:
            return []
        first = tree.body[0]
        if isinstance(first, ast.FunctionDef):
            return ["from collections import OrderedDict\n\n" + source]
        return []

    def _set_to_ordered_dict(self, source):
        if "return list(set(lst))" not in source:
            return []
        return [source.replace("return list(set(lst))", "from collections import OrderedDict\n\n    return list(OrderedDict.fromkeys(lst))", 1)]

    def _list_to_list_of_ordereddict(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "list":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                    inner = node.args[0]
                    if isinstance(inner.func, ast.Attribute) and inner.func.attr == "fromkeys":
                        if "from collections import OrderedDict" not in source:
                            out.append("from collections import OrderedDict\n\n" + source)
        return out

    def _tuple_accumulator_to_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Tuple):
                    out.append(_splice(source, node.value, "[]"))
        return out

    def _tuple_concat_missing_comma(self, source):
        if "(x)" not in source and "(i)" not in source:
            return []
        return [source.replace("(x)", "(x,)").replace("(i)", "(i,)")]

    def _insert_zero_to_append(self, source):
        return []

    def _append_call_instead_of_method(self, source):
        if ".append(" not in source:
            return []
        return []

    def _extend_to_append_for_scalars(self, source):
        if ".extend(" in source:
            return [source.replace(".extend(", ".append(")]
        return []

    def _append_result_of_append(self, source):
        if ".append(" in source and "return" in source:
            return [source.replace("= new_list.append(", "= new_list.append(")]
        return []

    def _sort_not_needed_remove_extras(self, source):
        if ".sort()" not in source:
            return []
        return [source.replace("lst.sort()\n", "", 1)]

    def _sort_reverse_name(self, source):
        return []

    def _off_by_one_range_end(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Add):
                    right = node.args[0].right
                    if isinstance(right, ast.Constant) and right.value == 1:
                        out.append(_splice(source, node.args[0], _expr_text(source, node.args[0].left)))
        return out

    def _while_missing_else_increment(self, source):
        return []

    def _skip_return_none_empty(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
                out.append(_splice(source, node.value, "[]"))
        return out

    def _loop_over_function_name(self, source):
        return [source.replace("for item in list:", "for item in lst:")] if "for item in list:" in source else []

    def _membership_against_input_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "lst":
                    out.append(_splice(source, node.comparators[0], "new_list"))
                if isinstance(node.left, ast.Name) and node.left.id == "lst":
                    out.append(_splice(source, node.left, "i"))
        return out

    def _comparison_instead_of_membership(self, source):
        if " !=final" in source:
            return [source.replace("!=final", "not in final")]
        return []