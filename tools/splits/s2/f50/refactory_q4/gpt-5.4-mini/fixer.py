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


def _replace_name(source, tree, old, new):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == old:
            out.append(_splice(source, node, new))
    return out


class Fixer:
    def rules(self):
        return [
            Rule("return_missing_sort_variable", self._return_missing_sort_variable, ("wrong",)),
            Rule("remove_loop_var_instead_of_selected_item", self._remove_loop_var_instead_of_selected_item, ("wrong",)),
            Rule("append_loop_var_instead_of_selected_item", self._append_loop_var_instead_of_selected_item, ("wrong",)),
            Rule("wrong_target_identifier", self._wrong_target_identifier, ("wrong",)),
            Rule("comparison_on_scalar_age_should_use_tuple", self._comparison_on_scalar_age_should_use_tuple, ("wrong",)),
            Rule("collect_selected_tuple_not_placeholder", self._collect_selected_tuple_not_placeholder, ("wrong",)),
            Rule("missing_return_after_loop", self._missing_return_after_loop, ("wrong",)),
            Rule("reverse_called_as_value", self._reverse_called_as_value, ("wrong",)),
            Rule("age_scalar_assignment_should_keep_tuple", self._age_scalar_assignment_should_keep_tuple, ("wrong",)),
            Rule("return_reverse_call_instead_of_method", self._return_reverse_call_instead_of_method, ("wrong",)),
            Rule("min_to_max_in_age_selection", self._min_to_max_in_age_selection, ("wrong",)),
            Rule("strictly_ascending_should_be_descending", self._strictly_ascending_should_be_descending, ("wrong",)),
            Rule("off_by_one_loop_to_include_last", self._off_by_one_loop_to_include_last, ("wrong",)),
            Rule("pop_argument_should_be_index_or_value", self._pop_argument_should_be_index_or_value, ("wrong",)),
            Rule("boolean_reverse_result_not_method_object", self._boolean_reverse_result_not_method_object, ("wrong",)),
            Rule("tuple_index_compare_not_whole_tuple", self._tuple_index_compare_not_whole_tuple, ("wrong",)),
        ]

    def _return_missing_sort_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "sort":
                out.append(_splice(source, node.value, "sortt"))
        return out

    def _remove_loop_var_instead_of_selected_item(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    out.append(_splice(source, arg, "oldest"))
                    out.append(_splice(source, arg, "largest"))
                    out.append(_splice(source, arg, "biggest"))
        return list(dict.fromkeys(out))

    def _append_loop_var_instead_of_selected_item(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name) and arg.id in {"i", "k", "j", "people"}:
                    out.append(_splice(source, arg, "oldest"))
                    out.append(_splice(source, arg, "largest"))
                    out.append(_splice(source, arg, "biggest"))
                    out.append(_splice(source, arg, "smallest"))
        return list(dict.fromkeys(out))

    def _wrong_target_identifier(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for old, new in [("a", "lst"), ("smallsest", "smallest"), ("smallest", "biggest"), ("biggesr", "biggest"), ("final", "people")]:
            out.extend(_replace_name(source, tree, old, new))
        return list(dict.fromkeys(out))

    def _comparison_on_scalar_age_should_use_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.left, ast.Subscript):
                left = node.left
                if isinstance(left.slice, ast.Constant) and left.slice.value == 1 and isinstance(node.comparators[0], ast.Name):
                    comp = node.comparators[0]
                    if comp.id in {"largest", "smallest", "biggest", "oldest"}:
                        ls, le = _span(source, left)
                        rs, re = _span(source, comp)
                        out.append(source[:ls] + source[ls:le] + " > " + source[rs:re] + "[1]" + source[re:])
                        out.append(source[:ls] + source[ls:le] + " < " + source[rs:re] + "[1]" + source[re:])
        return list(dict.fromkeys(out))

    def _collect_selected_tuple_not_placeholder(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Constant) and node.value.value == ():
                    out.append(_splice(source, node.value, "j"))
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Tuple) and len(node.value.elts) == 0:
                    out.append(_splice(source, node.value, "j"))
        return list(dict.fromkeys(out))

    def _missing_return_after_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "sort_age":
                if node.body and isinstance(node.body[-1], ast.Expr):
                    expr = node.body[-1]
                    if isinstance(expr.value, ast.Name) and expr.value.id in {"sort", "sortt", "newlist", "new_lst", "output", "rslt"}:
                        out.append(source[:_span(source, expr)[0]] + "return " + source[_span(source, expr)[0]:_span(source, expr)[1]] + source[_span(source, expr)[1]:])
        return out

    def _reverse_called_as_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute) and node.value.attr == "reverse":
                s, e = _span(source, node.value)
                out.append(source[:s] + source[s:e].replace(".reverse", "") + ".reverse()" + source[e:])
        return list(dict.fromkeys(out))

    def _age_scalar_assignment_should_keep_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Subscript):
                if isinstance(node.value.slice, ast.Constant) and node.value.slice.value == 1:
                    out.append(_splice(source, node.value, "lst[0]"))
        return out

    def _return_reverse_call_instead_of_method(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id.endswith("reverse"):
                out.append(_splice(source, node.value, node.value.id.replace("reverse", "") or "sort"))
        return list(dict.fromkeys(out))

    def _min_to_max_in_age_selection(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "min":
                out.append(_splice(source, node.func, "max"))
        return out

    def _strictly_ascending_should_be_descending(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, ast.Lt):
                    s, e = _span(source, op)
                    out.append(source[:s] + ">" + source[e:])
                elif isinstance(op, ast.Gt):
                    s, e = _span(source, op)
                    out.append(source[:s] + "<" + source[e:])
        return list(dict.fromkeys(out))

    def _off_by_one_loop_to_include_last(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                args = node.iter.args
                if len(args) == 1:
                    s, e = _span(source, node.iter)
                    out.append(source[:s] + source[s:e].replace("range(len(lst))", "range(len(lst)-1)") + source[e:])
                if len(args) >= 2:
                    for a in args:
                        if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Sub) and isinstance(a.right, ast.Constant) and a.right.value == 1:
                            s, e = _span(source, a.right)
                            out.append(source[:s] + "0" + source[e:])
        return list(dict.fromkeys(out))

    def _pop_argument_should_be_index_or_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.List):
                    out.append(_splice(source, arg, "i"))
                    out.append(_splice(source, arg, "count"))
        return list(dict.fromkeys(out))

    def _boolean_reverse_result_not_method_object(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute) and node.value.attr == "reverse":
                out.append(_splice(source, node.value, node.value.value.id + "[::-1]" if isinstance(node.value.value, ast.Name) else "lst[::-1]"))
        return list(dict.fromkeys(out))

    def _tuple_index_compare_not_whole_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Name) and left.id in {"largest", "smallest", "oldest"}:
                    out.append(_splice(source, left, f"{left.id}[1]"))
                if isinstance(right, ast.Name) and right.id in {"largest", "smallest", "oldest"}:
                    out.append(_splice(source, right, f"{right.id}[1]"))
        return list(dict.fromkeys(out))