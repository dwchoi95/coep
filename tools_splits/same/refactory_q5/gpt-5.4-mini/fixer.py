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


def _name_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="append_variable_instead_of_constant_or_value",
                symptoms=("wrong",),
                apply=self._append_variable_instead_of_constant_or_value,
            ),
            Rule(
                name="return_list_instead_of_last_mutated_input",
                symptoms=("wrong",),
                apply=self._return_list_instead_of_last_mutated_input,
            ),
            Rule(
                name="off_by_one_slice_k_plus_one",
                symptoms=("wrong",),
                apply=self._off_by_one_slice_k_plus_one,
            ),
            Rule(
                name="off_by_one_slice_k_minus_one",
                symptoms=("wrong",),
                apply=self._off_by_one_slice_k_minus_one,
            ),
            Rule(
                name="append_after_remove_max",
                symptoms=("wrong",),
                apply=self._append_after_remove_max,
            ),
            Rule(
                name="remove_max_then_append_max",
                symptoms=("wrong",),
                apply=self._remove_max_then_append_max,
            ),
            Rule(
                name="forget_to_return_result",
                symptoms=("wrong",),
                apply=self._forget_to_return_result,
            ),
            Rule(
                name="wrong_limit_comparison",
                symptoms=("wrong",),
                apply=self._wrong_limit_comparison,
            ),
            Rule(
                name="strictly_less_to_less_equal_bounds",
                symptoms=("wrong",),
                apply=self._strictly_less_to_less_equal_bounds,
            ),
            Rule(
                name="pop_on_value_instead_of_index",
                symptoms=("err:TypeError", "wrong"),
                apply=self._pop_on_value_instead_of_index,
            ),
            Rule(
                name="remove_result_append_result",
                symptoms=("wrong",),
                apply=self._remove_result_append_result,
            ),
            Rule(
                name="nested_append_inside_comparison_loop",
                symptoms=("wrong",),
                apply=self._nested_append_inside_comparison_loop,
            ),
            Rule(
                name="missing_increment_in_counting_loop",
                symptoms=("timeout", "wrong"),
                apply=self._missing_increment_in_counting_loop,
            ),
        ]

    def _append_variable_instead_of_constant_or_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if len(node.args) != 1:
                    continue
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    if _name_text(source, arg) != _name_text(source, node.func.value):
                        out.append(_splice(source, arg, _name_text(source, node.func.value)))
                elif isinstance(arg, ast.Constant):
                    if isinstance(node.func.value, ast.Name):
                        out.append(_splice(source, arg, _name_text(source, node.func.value)))
        return out

    def _return_list_instead_of_last_mutated_input(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                if isinstance(node.value.value, ast.Name) and node.value.value.id in {"lst", "list"}:
                    out.append(_splice(source, node.value.value, "result" if "result" in source else "sort"))
        return out

    def _off_by_one_slice_k_plus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Slice) and isinstance(node.upper, ast.BinOp) and isinstance(node.upper.op, ast.Add):
                if isinstance(node.upper.right, ast.Constant) and node.upper.right.value == 1:
                    out.append(_splice(source, node.upper, _name_text(source, node.upper.left)))
        return out

    def _off_by_one_slice_k_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Slice) and isinstance(node.upper, ast.BinOp) and isinstance(node.upper.op, ast.Sub):
                if isinstance(node.upper.right, ast.Constant) and node.upper.right.value == 1:
                    out.append(_splice(source, node.upper, _name_text(source, node.upper.left)))
        return out

    def _append_after_remove_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                    if len(call.args) == 1 and isinstance(call.args[0], ast.Call):
                        inner = call.args[0]
                        if isinstance(inner.func, ast.Name) and inner.func.id == "max":
                            argtxt = _name_text(source, call.args[0])
                            out.append(_splice(source, call.args[0], argtxt))
        return out

    def _remove_max_then_append_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "remove":
                    if len(call.args) == 1 and isinstance(call.args[0], ast.Call):
                        inner = call.args[0]
                        if isinstance(inner.func, ast.Name) and inner.func.id == "max":
                            out.append(_splice(source, call.args[0], _name_text(source, call.args[0])))
        return out

    def _forget_to_return_result(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "top_k"]:
            if not func.body:
                continue
            last = func.body[-1]
            if not isinstance(last, ast.Return):
                indent = " " * (last.col_offset if hasattr(last, "col_offset") else 4)
                insert = f"\n{indent}return new_lst"
                s, e = _span(source, last)
                out.append(source[:e] + insert + source[e:])
        return out

    def _wrong_limit_comparison(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, ast.LtE):
                    out.append(_splice(source, node, f"{_name_text(source, node.left)} < {_name_text(source, node.comparators[0])}"))
                elif isinstance(op, ast.GtE):
                    out.append(_splice(source, node, f"{_name_text(source, node.left)} > {_name_text(source, node.comparators[0])}"))
        return out

    def _strictly_less_to_less_equal_bounds(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                out.append(_splice(source, node, f"{_name_text(source, node.left)} <= {_name_text(source, node.comparators[0])}"))
        return out

    def _pop_on_value_instead_of_index(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                    arg = node.args[0]
                    if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "index" for n in ast.walk(tree)):
                        out.append(_splice(source, arg, f"{_name_text(source, node.func.value)}.index({_name_text(source, arg)})"))
        return out

    def _remove_result_append_result(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                    inner = node.args[0]
                    if isinstance(inner.func, ast.Attribute) and inner.func.attr == "remove":
                        out.append(_splice(source, node, f"{_name_text(source, node.func.value)}.append({_name_text(source, inner.func.value)})"))
        return out

    def _nested_append_inside_comparison_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.If) and child.body:
                        for stmt in child.body:
                            if isinstance(stmt, ast.Assign):
                                continue
                            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                                call = stmt.value
                                if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                                    out.append(_splice(source, stmt, ""))
        return out

    def _missing_increment_in_counting_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                text = ast.get_source_segment(source, node)
                if text and "counter" in text and "+= 1" not in text and "counter += 1" not in text:
                    insert = "\n" + (" " * (node.body[-1].col_offset if node.body else 4)) + "counter += 1"
                    s, e = _span(source, node.body[-1])
                    out.append(source[:e] + insert + source[e:])
        return out