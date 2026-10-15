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


def _name_of(target):
    return isinstance(target, ast.Name)


def _is_empty_list(node):
    return isinstance(node, ast.List) and len(node.elts) == 0


def _is_list_returning_append_call(stmt, list_name):
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Attribute)
        and isinstance(stmt.value.func.value, ast.Name)
        and stmt.value.func.value.id == list_name
        and stmt.value.func.attr == "append"
        and len(stmt.value.args) == 1
    )


class Fixer:
    def rules(self):
        return [
            Rule("membership_against_input_instead_of_output", self._membership_input_to_output, ("wrong",)),
            Rule("membership_against_undefined_seen", self._membership_seen_to_output, ("wrong", "err:NameError")),
            Rule("reversed_membership_condition", self._reverse_membership_condition, ("wrong",)),
            Rule("insert_at_front_instead_of_append", self._insert0_to_append, ("wrong",)),
            Rule("append_brackets_or_method", self._append_brackets_to_call, ("wrong", "err:TypeError")),
            Rule("return_loop_variable_instead_of_container", self._bad_return_loopvar, ("wrong",)),
            Rule("missing_return_final_output", self._add_missing_return, ("wrong",)),
            Rule("count_against_input_instead_of_output", self._count_input_to_output, ("wrong",)),
            Rule("pop_method_not_called", self._call_pop_method, ("wrong", "err:TypeError")),
            Rule("reverse_assigned_to_none", self._fix_reverse_assignment, ("wrong", "err:AttributeError")),
            Rule("sorts_input_for_dedup", self._remove_sort_call, ("wrong",)),
            Rule("wrong_return_set", self._set_to_list, ("wrong",)),
            Rule("off_by_one_range_upper_bound", self._fix_range_upper_bound, ("wrong", "err:IndexError")),
            Rule("missing_list_copy_call", self._call_copy, ("wrong", "err:AttributeError")),
            Rule("return_none_on_empty_list", self._empty_list_none_to_empty, ("wrong",)),
            Rule("return_input_slice_only_first_duplicate", self._return_early_slice, ("wrong",)),
            Rule("increment_missing_in_while", self._add_while_increment, ("timeout", "wrong")),
            Rule("remove_instead_of_append", self._remove_to_append, ("wrong", "err:TypeError")),
            Rule("pop_index_brackets", self._pop_brackets_to_call, ("wrong", "err:TypeError")),
            Rule("comparison_with_input_count", self._fix_count_compare, ("wrong",)),
        ]

    def _membership_input_to_output(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"lst", "values", "result", "new_lst", "newlist", "output", "store", "new", "a", "extra", "seq", "result"}:
                    if _name_of(node.left):
                        out.append(_splice(source, node.comparators[0], node.left.id))
        return out

    def _membership_seen_to_output(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "seen":
                    if _name_of(node.left):
                        out.append(_splice(source, node.comparators[0], "output"))
        return out

    def _reverse_membership_condition(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                if _name_of(node.left) and len(node.comparators) == 1 and _name_of(node.comparators[0]):
                    if node.comparators[0].id in {"output", "new_lst", "newlist", "store"}:
                        out.append(_splice(source, node, f"{node.left.id} not in {node.comparators[0].id}"))
        return out

    def _insert0_to_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.attr == "insert" and len(node.args) >= 1:
                    if isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                        s, e = _span(source, node)
                        out.append(source[:s] + f"{node.func.value.id}.append(" + source[_span(source, node.args[1])[0]:_span(source, node.args[1])[1]] + ")" + source[e:])
        return out

    def _append_brackets_to_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "append":
                parent = node
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Attribute) and node.value.attr == "append":
                    s, e = _span(source, node)
                    inner = source[_span(source, node.slice)[0]:_span(source, node.slice)[1]]
                    out.append(source[:s] + source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]] + ".append(" + inner + ")" + source[e:])
        return out

    def _bad_return_loopvar(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                for fn in ast.walk(tree):
                    if isinstance(fn, ast.FunctionDef) and any(isinstance(s, ast.For) for s in fn.body):
                        out.append(_splice(source, node.value, "output"))
                        return out
        return out

    def _add_missing_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            if not any(isinstance(s, ast.Return) for s in fn.body):
                last = fn.body[-1]
                s, e = _span(source, last)
                out.append(source[:e] + "\n    return output" + source[e:])
                return out
        return out

    def _count_input_to_output(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "count":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "lst":
                    s, e = _span(source, node.func.value)
                    out.append(source[:s] + "newlist" + source[e:])
        return out

    def _call_pop_method(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "pop":
                parent = node
                s, e = _span(source, node)
                out.append(source[:s] + source[s:e] + "()" + source[e:])
        return out

    def _fix_reverse_assignment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and node.value.attr == "reverse":
                s, e = _span(source, node.value)
                out.append(source[:s] + source[_span(source, node.targets[0])[0]:_span(source, node.targets[0])[1]] + ".reverse()" + source[e:])
        return out

    def _remove_sort_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                if node.value.func.attr == "sort":
                    s, e = _span(source, node)
                    out.append(source[:s] + "" + source[e:])
        return out

    def _set_to_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "set":
                arg = node.value.args[0]
                s, e = _span(source, node.value)
                out.append(source[:s] + source[_span(source, arg)[0]:_span(source, arg)[1]] + source[e:])
        return out

    def _fix_range_upper_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 2:
                if isinstance(node.args[1], ast.BinOp) and isinstance(node.args[1].op, ast.Add):
                    continue
                s, e = _span(source, node.args[1])
                out.append(source[:s] + f"{source[_span(source, node.args[1])[0]:_span(source, node.args[1])[1]]} - 1" + source[e:])
        return out

    def _call_copy(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and node.value.attr == "copy":
                s, e = _span(source, node.value)
                out.append(source[:s] + source[s:e] + "()" + source[e:])
        return out

    def _empty_list_none_to_empty(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
                out.append(_splice(source, node.value, "[]"))
        return out

    def _return_early_slice(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id == "lst":
                    continue
        return out

    def _add_while_increment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                body_src = source[_span(source, node.body[-1])[1]:_span(source, node)[1]]
                if "i += 1" not in body_src and "i=i+1" not in body_src:
                    insert_at = _span(source, node.body[-1])[1]
                    out.append(source[:insert_at] + "\n        i += 1" + source[insert_at:])
        return out

    def _remove_to_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if _name_of(node.target):
                    s, e = _span(source, node)
                    out.append(source[:s] + f"{node.target.id}.append(" + source[_span(source, node.value)[0]:_span(source, node.value)[1]] + ")" + source[e:])
        return out

    def _pop_brackets_to_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "pop":
                s, e = _span(source, node)
                out.append(source[:s] + source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]] + ".pop(" + source[_span(source, node.slice)[0]:_span(source, node.slice)[1]] + ")" + source[e:])
        return out

    def _fix_count_compare(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Attribute) and node.left.func.attr == "count":
                    s, e = _span(source, node.ops[0])
                    out.append(source[:s] + "==" + source[e:])
        return out