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


def _get_source_segment(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _replace_node(source, target, new_text):
    return _splice(source, target, new_text)


def _find_enclosing_function(tree, node):
    stack = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, n):
            stack.append(n)
            self.generic_visit(n)
            stack.pop()

        def visit_AsyncFunctionDef(self, n):
            stack.append(n)
            self.generic_visit(n)
            stack.pop()

    Visitor().visit(tree)
    return None


class Fixer:
    def rules(self):
        return [
            Rule("append_into_new_list_instead_of_undefined", self._fix_undefined_append_target, ("wrong", "err:NameError")),
            Rule("for_loop_range_inclusive_to_exclusive", self._fix_range_off_by_one, ("wrong", "timeout")),
            Rule("while_length_off_by_one", self._fix_while_length_bound, ("wrong", "timeout")),
            Rule("return_top_k_slice_bound", self._fix_slice_k_plus_one, ("wrong",)),
            Rule("return_full_list_when_k_is_one", self._fix_k_equals_one_return, ("wrong",)),
            Rule("append_max_before_removal", self._fix_remove_then_append_max, ("wrong",)),
            Rule("use_comparison_variable_not_index", self._fix_index_vs_value_compare, ("wrong", "err:TypeError")),
            Rule("fix_single_assignment_swap", self._fix_parallel_swap, ("wrong",)),
            Rule("fix_pop_max_index", self._fix_pop_max_index, ("wrong", "err:TypeError")),
            Rule("fix_missing_counter_increment", self._fix_missing_counter_increment, ("wrong", "timeout")),
            Rule("fix_missing_return_statement", self._fix_missing_return, ("wrong",)),
            Rule("fix_append_index_instead_of_value", self._fix_append_index_value, ("wrong",)),
            Rule("fix_remove_before_append_in_max_loop", self._fix_remove_before_append, ("wrong",)),
            Rule("fix_list_method_call_brackets", self._fix_subscript_vs_call, ("wrong", "err:TypeError")),
            Rule("fix_comparison_direction_in_max_scan", self._fix_comp_direction, ("wrong",)),
        ]

    def _fix_undefined_append_target(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "top_k":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "append":
                        if isinstance(sub.func.value, ast.Name) and sub.func.value.id in {"new", "sort", "sort_k"}:
                            continue
                        if isinstance(sub.func.value, ast.Name):
                            txt = _get_source_segment(source, sub.func.value)
                            if txt in {"list"}:
                                continue
                        if isinstance(sub.func.value, ast.Name) and sub.func.value.id == "new":
                            continue
                        if isinstance(sub.func.value, ast.Name):
                            append_target = sub.func.value.id
                            for name in ("new_lst", "newlist", "result", "res", "sorted_lst", "sort", "sort_list", "new", "a"):
                                pass
                        if isinstance(sub.func.value, ast.Name) and sub.func.value.id not in {"new_lst", "newlist", "result", "res", "sorted_lst", "sort", "sort_list", "new", "a", "values", "output", "l", "tmp", "rs", "n", "maximum"}:
                            for cand in ast.walk(node):
                                if isinstance(cand, ast.Name) and cand.id not in {"append", "max", "min", "len", "range"}:
                                    pass
                        if isinstance(sub.func.value, ast.Name) and sub.func.value.id == "list":
                            out.append(_replace_node(source, sub.func.value, "new_lst"))
        return out

    def _fix_range_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                args = node.iter.args
                if len(args) == 1:
                    a = args[0]
                    if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Sub) and isinstance(a.right, ast.Constant) and a.right.value == 1:
                        out.append(_replace_node(source, a.right, "0"))
                    elif isinstance(a, ast.Constant) and isinstance(a.value, int) and a.value > 0:
                        pass
                elif len(args) == 2:
                    start, end = args
                    if isinstance(end, ast.BinOp) and isinstance(end.op, ast.Sub) and isinstance(end.right, ast.Constant) and end.right.value == 1:
                        out.append(_replace_node(source, end.right, "0"))
                if len(args) == 1 and isinstance(args[0], ast.Name):
                    pass
        return out

    def _fix_while_length_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                op = node.test.ops[0]
                if isinstance(op, ast.LtE):
                    out.append(_replace_node(source, op, "<"))
                elif isinstance(op, ast.GtE):
                    out.append(_replace_node(source, op, ">"))
        return out

    def _fix_slice_k_plus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.BinOp) and isinstance(node.slice.op, ast.Add):
                if isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 1:
                    out.append(_replace_node(source, node.slice, "k"))
        return out

    def _fix_k_equals_one_return(self, source):
        return []

    def _fix_remove_then_append_max(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "top_k":
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                            if isinstance(call.args[0], ast.Call) and isinstance(call.args[0].func, ast.Name) and call.args[0].func.id == "max":
                                continue
        return out

    def _fix_index_vs_value_compare(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Name) and left.id == "i" and isinstance(right, ast.Call) and isinstance(right.func, ast.Name) and right.func.id == "max":
                    out.append(_replace_node(source, left, "lst[i]"))
        return out

    def _fix_parallel_swap(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript):
                t = node.targets[0]
                if isinstance(node.value, ast.Subscript):
                    s1 = _get_source_segment(source, t)
                    s2 = _get_source_segment(source, node.value)
                    if s1 != s2:
                        out.append(_replace_node(source, node, f"{s1}, {s2} = {s2}, {s1}"))
        return out

    def _fix_pop_max_index(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "max":
                    inner = _get_source_segment(source, arg)
                    out.append(_replace_node(source, arg, f"{_get_source_segment(source, node.func.value)}.index({inner})"))
        return out

    def _fix_missing_counter_increment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                body = node.body
                if body:
                    last = body[-1]
                    if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
                        pass
        return out

    def _fix_missing_return(self, source):
        return []

    def _fix_append_index_value(self, source):
        return []

    def _fix_remove_before_append(self, source):
        return []

    def _fix_subscript_vs_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
                if node.value.attr == "remove":
                    out.append(_replace_node(source, node.value, _get_source_segment(source, node.value).replace(".remove", ".pop")))
        return out

    def _fix_comp_direction(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Lt):
                    out.append(_replace_node(source, node.ops[0], ">"))
                elif isinstance(node.ops[0], ast.Gt):
                    out.append(_replace_node(source, node.ops[0], "<"))
        return out