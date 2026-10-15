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
            Rule(name="loop_target_confusion", apply=self._loop_target_confusion, symptoms=("wrong", "err:NameError")),
            Rule(name="iterable_name_confusion", apply=self._iterable_name_confusion, symptoms=("wrong", "err:NameError")),
            Rule(name="wrong_membership_container", apply=self._wrong_membership_container, symptoms=("wrong",)),
            Rule(name="wrong_membership_target", apply=self._wrong_membership_target, symptoms=("wrong",)),
            Rule(name="count_against_input_instead_of_output", apply=self._count_against_input_instead_of_output, symptoms=("wrong",)),
            Rule(name="append_call_to_list_literal", apply=self._append_call_to_list_literal, symptoms=("wrong", "err:TypeError")),
            Rule(name="extend_of_singleton_or_scalar", apply=self._extend_of_singleton_or_scalar, symptoms=("wrong", "err:TypeError")),
            Rule(name="append_result_of_append", apply=self._append_result_of_append, symptoms=("wrong", "err:AttributeError")),
            Rule(name="return_wrong_variable", apply=self._return_wrong_variable, symptoms=("wrong",)),
            Rule(name="return_none_on_empty", apply=self._return_none_on_empty, symptoms=("wrong",)),
            Rule(name="append_instead_of_insert_zero", apply=self._append_instead_of_insert_zero, symptoms=("wrong",)),
            Rule(name="list_method_used_as_subscription", apply=self._list_method_used_as_subscription, symptoms=("wrong", "err:TypeError")),
            Rule(name="identity_to_list_index", apply=self._identity_to_list_index, symptoms=("wrong", "err:TypeError")),
            Rule(name="set_cast_to_ordered_scan", apply=self._set_cast_to_ordered_scan, symptoms=("wrong",)),
            Rule(name="reverse_method_called_without_parens", apply=self._reverse_method_called_without_parens, symptoms=("wrong", "err:AttributeError")),
            Rule(name="replace_whole_return_set", apply=self._replace_whole_return_set, symptoms=("wrong",)),
            Rule(name="off_by_one_range_end", apply=self._off_by_one_range_end, symptoms=("wrong",)),
        ]

    def _loop_target_confusion(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                if node.iter and isinstance(node.iter, ast.Name) and node.target.id == node.iter.id:
                    for n in ast.walk(tree):
                        if isinstance(n, ast.Name) and n.id == node.target.id and n is not node.target:
                            out.append(_splice(source, n, "i"))
                            break
        return out

    def _iterable_name_confusion(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
                out.append(_splice(source, node.iter, "lst"))
        return out

    def _wrong_membership_container(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                left = node.left
                right = node.comparators[0]
                if isinstance(right, ast.Name) and right.id in {"lst", "values"}:
                    out.append(_splice(source, right, "new_lst" if right.id == "lst" else "output"))
        return out

    def _wrong_membership_target(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                    if right.id in {"lst", "values"} and left.id in {"lst", "values"}:
                        out.append(_splice(source, left, "i" if left.id != "value" else "value"))
        return out

    def _count_against_input_instead_of_output(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Attribute):
                    if isinstance(node.left.func.value, ast.Name) and node.left.func.value.id in {"lst", "list"}:
                        if node.left.func.attr == "count":
                            left = node.left.func.value.id
                            out.append(_splice(source, node.left.func.value, "new_lst"))
                            return out
        return out

    def _append_call_to_list_literal(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                    out.append(_splice(source, node, f"{source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]]}.append({node.args[0].id})"))
        return out

    def _extend_of_singleton_or_scalar(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if isinstance(node.value, ast.Name) and node.value.id in {"i", "ele", "item", "x", "val", "element"}:
                    out.append(_splice(source, node.value, f"[{node.value.id}]"))
        return out

    def _append_result_of_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "append":
                    out.append(_splice(source, node.value, "None"))
        return out

    def _return_wrong_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id in {"lst", "i", "item", "result", "new_listt", "neW_lst"}:
                    out.append(_splice(source, node.value, "new_lst" if node.value.id != "result" else "result"))
        return out

    def _return_none_on_empty(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
                out.append(_splice(source, node.value, "[]"))
        return out

    def _append_instead_of_insert_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "insert":
                if len(node.args) >= 2:
                    s, e = _span(source, node)
                    out.append(source[:s] + f"{source[_span(source,node.func.value)[0]:_span(source,node.func.value)[1]]}.append({source[_span(source,node.args[1])[0]:_span(source,node.args[1])[1]]})" + source[e:])
        return out

    def _list_method_used_as_subscription(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in {"result", "new_list", "newlst"}:
                if isinstance(node.slice, ast.Call) and isinstance(node.slice.func, ast.Attribute) and node.slice.func.attr == "append":
                    out.append(_splice(source, node.slice.func, node.slice.func.attr))
        return out

    def _identity_to_list_index(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Name) and node.slice.id in {"i", "j"}:
                out.append(_splice(source, node.slice, "i"))
        return out

    def _set_cast_to_ordered_scan(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "list":
                    if len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Call):
                        if isinstance(node.value.args[0].func, ast.Name) and node.value.args[0].func.id == "set":
                            out.append(_splice(source, node.value, "[i for i in lst if i not in output]"))
        return out

    def _reverse_method_called_without_parens(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "reverse":
                out.append(_splice(source, node, f"{source[_span(source,node.value)[0]:_span(source,node.value)[1]]}.reverse()"))
        return out

    def _replace_whole_return_set(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "set":
                    out.append(_splice(source, node.value, "output"))
        return out

    def _off_by_one_range_end(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 2:
                a0, a1 = node.args
                if isinstance(a1, ast.BinOp) and isinstance(a1.op, ast.Add):
                    out.append(_splice(source, a1, source[_span(source, a1.left)[0]:_span(source, a1.left)[1]]))
        return out