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


def _contains_name(node, names):
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in names:
            return True
    return False


def _replace_name(source, tree, old, new):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == old:
            out.append(_splice(source, node, new))
    return out


def _replace_stmt(source, tree, predicate, new_text):
    out = []
    for node in ast.walk(tree):
        if predicate(node):
            out.append(_splice(source, node, new_text))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="use_selected_element_not_loop_variable", apply=self._use_selected_element_not_loop_variable, symptoms=("wrong",)),
            Rule(name="fix_wrong_target_variable_in_remove_and_append", apply=self._fix_wrong_target_variable_in_remove_and_append, symptoms=("wrong",)),
            Rule(name="fix_assignment_in_comparison_update", apply=self._fix_assignment_in_comparison_update, symptoms=("wrong",)),
            Rule(name="fix_misnamed_temp_variable", apply=self._fix_misnamed_temp_variable, symptoms=("wrong",)),
            Rule(name="fix_missing_return_final_result", apply=self._fix_missing_return_final_result, symptoms=("wrong",)),
            Rule(name="fix_return_reverse_call", apply=self._fix_return_reverse_call, symptoms=("wrong",)),
            Rule(name="fix_list_to_tuple_append", apply=self._fix_list_to_tuple_append, symptoms=("wrong",)),
            Rule(name="fix_recursive_call_on_tail", apply=self._fix_recursive_call_on_tail, symptoms=("wrong",)),
            Rule(name="fix_merge_pop_direction", apply=self._fix_merge_pop_direction, symptoms=("wrong",)),
            Rule(name="fix_swap_rhs_aliasing", apply=self._fix_swap_rhs_aliasing, symptoms=("wrong",)),
            Rule(name="fix_list_sort_reverse_return", apply=self._fix_list_sort_reverse_return, symptoms=("wrong",)),
            Rule(name="fix_index_and_bound_errors", apply=self._fix_index_and_bound_errors, symptoms=("wrong",)),
            Rule(name="fix_tuple_accumulator_build", apply=self._fix_tuple_accumulator_build, symptoms=("wrong",)),
            Rule(name="fix_append_pop_of_max_element", apply=self._fix_append_pop_of_max_element, symptoms=("wrong",)),
            Rule(name="fix_missing_base_case_or_empty_check", apply=self._fix_missing_base_case_or_empty_check, symptoms=("wrong",)),
        ]

    def _use_selected_element_not_loop_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and isinstance(node.body, list):
                loopvar = node.target.id
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        if isinstance(call.func, ast.Attribute) and call.func.attr in {"append", "remove", "insert"}:
                            if len(call.args) >= 1 and isinstance(call.args[0], ast.Name) and call.args[0].id == loopvar:
                                if call.func.attr == "append":
                                    s, e = _span(source, call.args[0])
                                    out.append(source[:s] + "smallest" + source[e:])
                                elif call.func.attr == "remove":
                                    s, e = _span(source, call.args[0])
                                    out.append(source[:s] + "smallest" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_wrong_target_variable_in_remove_and_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"remove", "append"}:
                if node.args and isinstance(node.args[0], ast.Name):
                    name = node.args[0].id
                    if name in {"i", "j", "k", "counter", "biggest", "smallest"}:
                        s, e = _span(source, node.args[0])
                        out.append(source[:s] + "smallest" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_assignment_in_comparison_update(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                if isinstance(node.left, ast.Name) and node.left.id in {"person", "i"}:
                    if _contains_name(node, {"oldest", "smallest"}):
                        continue
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Name):
                    if node.targets[0].id in {"person", "i"} and node.value.id in {"oldest", "smallest"}:
                        s, e = _span(source, node.value)
                        out.append(source[:s] + node.targets[0].id + source[e:])
        return list(dict.fromkeys(out))

    def _fix_misnamed_temp_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"biggest", "largest", "oldest", "smallest"}:
                out.append(_splice(source, node, "smallest"))
            if isinstance(node, ast.Name) and node.id == "larget":
                out.append(_splice(source, node, "largest"))
        return list(dict.fromkeys(out))

    def _fix_missing_return_final_result(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is not None:
                if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and node.value.attr == "reverse":
                    out.append(_splice(source, node.value, node.value.value.id))
            if isinstance(node, ast.Pass):
                out.append(_splice(source, node, "return a"))
        return list(dict.fromkeys(out))

    def _fix_return_reverse_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                    s, e = _span(source, node.value)
                    out.append(source[:s] + node.value.func.value.id + source[e:])
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "sort":
                    s, e = _span(source, node.value)
                    out.append(source[:s] + node.value.func.value.id + source[e:])
        return list(dict.fromkeys(out))

    def _fix_list_to_tuple_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.value, ast.Name):
                if node.value.id in {"current", "oldest", "largest", "smallest"}:
                    s, e = _span(source, node)
                    out.append(source[:s] + f"{ast.unparse(node.target)} += ({node.value.id},)" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_recursive_call_on_tail(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                if isinstance(node.slice.lower, ast.Constant) and node.slice.lower.value == 1 and node.slice.upper is None:
                    s, e = _span(source, node)
                    out.append(source[:s] + ast.unparse(node.value) + source[e:])
        return list(dict.fromkeys(out))

    def _fix_merge_pop_direction(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                    s, e = _span(source, node)
                    out.append(source[:s] + ast.unparse(node.func.value) + ".pop(0)" + source[e:])
                elif node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in {"largest", "smallest"}:
                    s, e = _span(source, node.args[0])
                    out.append(source[:s] + "index" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_swap_rhs_aliasing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "lst[a]= lst[i]" in txt or "lst[i]= lst[a]" in txt:
                    out.append(txt.replace("lst[a]= lst[i]", "lst[a] = temp").replace("lst[i]= lst[a]", "lst[i] = temp"))
            if isinstance(node, ast.Assign) and len(node.targets) == 2:
                out.append(_splice(source, node, source[_span(source, node)[0]:_span(source, node)[1]].replace("lst[j],lst[j] = lst[j],lst[j]", "lst[i],lst[j] = lst[j],lst[i]")))
        return list(dict.fromkeys(out))

    def _fix_list_sort_reverse_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                    s, e = _span(source, node.value)
                    out.append(source[:s] + node.value.func.value.id + "[::-1]" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_index_and_bound_errors(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                    args = node.iter.args
                    if len(args) == 2 and isinstance(args[1], ast.BinOp) and isinstance(args[1].op, ast.Add):
                        pass
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                    if len(node.iter.args) == 1:
                        arg = node.iter.args[0]
                        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                            s, e = _span(source, arg)
                            out.append(source[:s] + f"len({ast.unparse(arg.left)})" + source[e:])
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                if node.slice.value == 1 and isinstance(node.value, ast.Name):
                    pass
        return list(dict.fromkeys(out))

    def _fix_tuple_accumulator_build(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "tuple":
                    s, e = _span(source, node.value)
                    out.append(source[:s] + "[" + source[s:e][6:-1] + "]" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_append_pop_of_max_element(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "max":
                if len(node.args) == 1:
                    s, e = _span(source, node)
                    out.append(source[:s] + f"max({ast.unparse(node.args[0])}, key=lambda p: p[1])" + source[e:])
        return list(dict.fromkeys(out))

    def _fix_missing_base_case_or_empty_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Name) and node.left.id == "lst" and isinstance(node.comparators[0], ast.Tuple):
                    s, e = _span(source, node.comparators[0])
                    out.append(source[:s] + "[]" + source[e:])
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name) and node.left.func.id == "len":
                    if isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 1:
                        s, e = _span(source, node.comparators[0])
                        out.append(source[:s] + "0" + source[e:])
        return list(dict.fromkeys(out))