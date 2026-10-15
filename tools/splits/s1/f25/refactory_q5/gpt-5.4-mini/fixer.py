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
            Rule(name="append_selected_largest_not_loop_variable",
                 apply=self._append_selected_largest_not_loop_variable,
                 symptoms=("wrong",)),
            Rule(name="return_sorted_accumulator_not_input",
                 apply=self._return_sorted_accumulator_not_input,
                 symptoms=("wrong",)),
            Rule(name="fix_recursive_new_list_name",
                 apply=self._fix_recursive_new_list_name,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_wrong_max_index_test_and_delete",
                 apply=self._fix_wrong_max_index_test_and_delete,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="defer_removal_until_after_scan",
                 apply=self._defer_removal_until_after_scan,
                 symptoms=("wrong", "timeout")),
            Rule(name="fix_negative_range_stop",
                 apply=self._fix_negative_range_stop,
                 symptoms=("wrong", "timeout")),
            Rule(name="fix_result_from_exhausted_list",
                 apply=self._fix_result_from_exhausted_list,
                 symptoms=("wrong",)),
        ]

    def _append_selected_largest_not_loop_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for node in ast.walk(func):
                if isinstance(node, ast.For) and len(node.body) >= 2:
                    last = node.body[-2:]
                    if isinstance(last[0], ast.Expr) and isinstance(last[0].value, ast.Call):
                        call = last[0].value
                        if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                            if isinstance(last[1], ast.Expr) and isinstance(last[1].value, ast.Call):
                                rcall = last[1].value
                                if isinstance(rcall.func, ast.Attribute) and rcall.func.attr == "remove":
                                    arg = call.args[0] if call.args else None
                                    rarg = rcall.args[0] if rcall.args else None
                                    if isinstance(arg, ast.Name) and isinstance(rarg, ast.Name) and arg.id == rarg.id:
                                        if isinstance(node.target, ast.Name) and arg.id == node.target.id:
                                            s1, e1 = _span(source, call.args[0])
                                            s2, e2 = _span(source, rcall.args[0])
                                            repl1 = source[s1:e1].replace(arg.id, "largest")
                                            repl2 = source[s2:e2].replace(arg.id, "largest")
                                            new_source = source[:s1] + repl1 + source[e1:s2] + repl2 + source[e2:]
                                            out.append(new_source)
        return out

    def _return_sorted_accumulator_not_input(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                val = node.value
                if isinstance(val.value, ast.Name) and val.value.id in {"lst", "list", "input_list"}:
                    for prev in ast.walk(tree):
                        if isinstance(prev, ast.Assign):
                            if any(isinstance(t, ast.Name) and t.id != val.value.id for t in prev.targets):
                                if isinstance(prev.value, ast.Name):
                                    s, e = _span(source, val.value)
                                    out.append(source[:s] + prev.targets[0].id + source[e:])
        return out

    def _fix_recursive_new_list_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "top_k":
                if len(node.args) >= 1 and isinstance(node.args[0], ast.Name):
                    if node.args[0].id == "new_lst":
                        s, e = _span(source, node.args[0])
                        out.append(source[:s] + "new_list" + source[e:])
        return out

    def _fix_wrong_max_index_test_and_delete(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Name) and node.left.id == "i":
                    right = node.comparators[0]
                    if isinstance(right, ast.Call) and isinstance(right.func, ast.Name) and right.func.id == "max":
                        left_s, left_e = _span(source, node.left)
                        right_s, right_e = _span(source, right)
                        new_cmp = source[left_s:left_e] + " == " + source[right_s:right_e]
                        out.append(_splice(source, node, new_cmp))
        return out

    def _defer_removal_until_after_scan(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and len(node.body) >= 2:
                first, second = node.body[0], node.body[1]
                if isinstance(first, ast.Assign) and isinstance(second, ast.Expr):
                    if isinstance(second.value, ast.Call) and isinstance(second.value.func, ast.Attribute):
                        if second.value.func.attr == "append":
                            if isinstance(first.targets[0], ast.Name):
                                if isinstance(second.value.args[0], ast.Name) and second.value.args[0].id == first.targets[0].id:
                                    s1, e1 = _span(source, first)
                                    s2, e2 = _span(source, second)
                                    new_source = source[:s1] + source[s2:e2] + "\n" + source[s1:e1] + source[e2:]
                                    out.append(new_source)
        return out

    def _fix_negative_range_stop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 2:
                    a1, a2 = node.args
                    if isinstance(a1, ast.UnaryOp) and isinstance(a1.op, ast.USub) and isinstance(a2, ast.UnaryOp) and isinstance(a2.op, ast.USub):
                        s, e = _span(source, a2)
                        out.append(source[:s] + "0" + source[e:])
        return out

    def _fix_result_from_exhausted_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                tgt = node.targets[0]
                if isinstance(tgt, ast.Name) and tgt.id == "output":
                    if isinstance(node.value, ast.ListComp):
                        s, e = _span(source, node.value)
                        out.append(source[:s] + "sort[:k]" + source[e:])
        return out