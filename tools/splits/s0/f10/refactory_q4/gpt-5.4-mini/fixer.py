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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_return_name_for_accumulator",
                apply=self._fix_return_name_for_accumulator,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_wrong_list_removed_variable",
                apply=self._fix_wrong_list_removed_variable,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="fix_append_removed_element_when_variable_is_wrong",
                apply=self._fix_append_removed_element_when_variable_is_wrong,
                symptoms=("wrong",),
            ),
            Rule(
                name="remove_premature_return_in_loop_sort",
                apply=self._remove_premature_return_in_loop_sort,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_compare_people_by_age_not_tuple",
                apply=self._fix_compare_people_by_age_not_tuple,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_smallest_instead_of_largest_comparison",
                apply=self._fix_smallest_instead_of_largest_comparison,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_returns_list_tail_not_max_holder",
                apply=self._fix_returns_list_tail_not_max_holder,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_return_accumulator_not_input",
                apply=self._fix_return_accumulator_not_input,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_append_scalar_instead_of_tuple",
                apply=self._fix_append_scalar_instead_of_tuple,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_reverse_order_bubble_sort_comparison",
                apply=self._fix_reverse_order_bubble_sort_comparison,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_bubble_sort_inner_bounds_and_swap",
                apply=self._fix_bubble_sort_inner_bounds_and_swap,
                symptoms=("wrong", "err:IndexError", "err:TypeError"),
            ),
            Rule(
                name="fix_recursion_missing_base_case_and_tail",
                apply=self._fix_recursion_missing_base_case_and_tail,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_sort_by_age_builtin_key_strategy",
                apply=self._fix_sort_by_age_builtin_key_strategy,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_max_holder_list_indexing",
                apply=self._fix_max_holder_list_indexing,
                symptoms=("wrong",),
            ),
        ]

    def _fix_return_name_for_accumulator(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sort_age"]:
            assigns = {}
            for n in func.body:
                if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                    assigns[n.targets[0].id] = n.targets[0]
            for n in ast.walk(func):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Name):
                    ret = n.value.id
                    if ret not in assigns:
                        for cand in ("sortt", "new", "arranged", "result", "store", "newlst", "new_list"):
                            if cand in assigns:
                                out.append(_replace_node(source, n.value, cand))
                                return out
        return out

    def _fix_wrong_list_removed_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "remove" and len(n.args) == 1:
                arg = n.args[0]
                if isinstance(arg, ast.Name) and arg.id in {"oldest", "largest", "maximum", "smallest", "curr", "i"}:
                    out.append(_replace_node(source, arg, arg.id if arg.id != "smallest" else "smallest"))
                elif isinstance(arg, ast.Name):
                    if arg.id == "smallest":
                        out.append(_replace_node(source, arg, "minimum"))
                    elif arg.id == "maximum":
                        out.append(_replace_node(source, arg, "max_age"))
        return out

    def _fix_append_removed_element_when_variable_is_wrong(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append" and len(n.args) == 1:
                arg = n.args[0]
                if isinstance(arg, ast.Name) and arg.id in {"i", "x"}:
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.For) and parent.target and isinstance(parent.target, ast.Name) and parent.target.id == arg.id:
                            out.append(_replace_node(source, arg, parent.target.id))
                            return out
        return out

    def _remove_premature_return_in_loop_sort(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Return):
                p = getattr(n, "parent", None)
        for func in [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)]:
            for stmt in func.body:
                if isinstance(stmt, ast.While):
                    for inner in stmt.body:
                        if isinstance(inner, ast.Return):
                            s, e = _span(source, inner)
                            out.append(source[:s] + source[e + len(source[e:]) - len(source[e:]):])
                            return [source[:s] + source[e:]]
        return out

    def _fix_compare_people_by_age_not_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                if isinstance(node.left, ast.Name) and any(isinstance(c, ast.Name) for c in node.comparators):
                    left = node.left
                    right = node.comparators[0]
                    if isinstance(right, ast.Name):
                        ls, le = _span(source, left)
                        rs, re = _span(source, right)
                        out.append(_splice(source, node, source[ls:le] + "[1] > " + source[rs:re] + "[1]"))
                        return out
        return out

    def _fix_smallest_instead_of_largest_comparison(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Subscript) and isinstance(right, ast.Name):
                    out.append(_replace_node(source, node, source[_span(source, left)[0]:_span(source, left)[1]] + " > " + source[_span(source, right)[0]:_span(source, right)[1]]))
                    return out
        return out

    def _fix_returns_list_tail_not_max_holder(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"lst", "sort1"}:
                for func in [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)]:
                    if func.lineno <= node.lineno <= func.end_lineno:
                        for stmt in func.body:
                            if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name):
                                out.append(_replace_node(source, node.value, stmt.targets[0].id))
                                return out
        return out

    def _fix_return_accumulator_not_input(self, source):
        return self._fix_returns_list_tail_not_max_holder(source)

    def _fix_append_scalar_instead_of_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if isinstance(node.value, ast.Tuple) and len(node.value.elts) == 1:
                    out.append(_replace_node(source, node.value, "[" + source[_span(source, node.value.elts[0])[0]:_span(source, node.value.elts[0])[1]] + "]"))
                    return out
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                pass
        return out

    def _fix_reverse_order_bubble_sort_comparison(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                    out.append(_replace_node(source, node, source[_span(source, left)[0]:_span(source, left)[1]] + " > " + source[_span(source, right)[0]:_span(source, right)[1]]))
                    return out
        return out

    def _fix_bubble_sort_inner_bounds_and_swap(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                    out.append(_replace_node(source, node, "range(len(lst)-1)"))
                    return out
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                    out.append(_replace_node(source, node, "range(len(lst)-1)"))
                    return out
        return out

    def _fix_recursion_missing_base_case_and_tail(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for func in [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef)]:
            for stmt in func.body:
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, ast.Add):
                    out.append(_replace_node(source, stmt.value.right, "sort_age(lst[1:])"))
                    return out
        return out

    def _fix_sort_by_age_builtin_key_strategy(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
                out.append(_replace_node(source, node, ""))
                return out
        return out

    def _fix_max_holder_list_indexing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in {"smallest", "largest", "maximum"} and isinstance(node.value, ast.Subscript):
                    out.append(_replace_node(source, node.value, source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]] + "[0]"))
                    return out
        return out