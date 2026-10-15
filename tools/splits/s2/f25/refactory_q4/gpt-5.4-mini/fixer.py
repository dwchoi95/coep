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


def _replace_node(source, target, replacement):
    ts, te = _span(source, target)
    rs, re = _span(source, replacement)
    return source[:ts] + source[rs:re] + source[te:]


def _same_name(node, names):
    return isinstance(node, ast.Name) and node.id in names


class Fixer:
    def rules(self):
        return [
            Rule(
                name="return_sorted_list_variable",
                apply=self._return_sort_var,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="replace_wrong_list_name_in_loop",
                apply=self._wrong_iterable_name,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_single_step_sort_loop_with_reset",
                apply=self._reset_outer_loop_after_move,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="fix_remove_and_append_misnamed_variable",
                apply=self._remove_append_misnamed,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_reverse_sort_to_descending_selection",
                apply=self._reverse_sort_to_selection,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_smallest_vs_largest_selection",
                apply=self._smallest_to_largest_selection,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_comparison_against_whole_tuple",
                apply=self._compare_age_not_tuple,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_wrong_return_inside_loop",
                apply=self._return_outside_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_sort_method_missing_reverse",
                apply=self._add_reverse_or_recursive_descending,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_append_pop_index_misuse",
                apply=self._pop_to_remove_or_correct_append,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_tuple_accumulation_return_type",
                apply=self._tuple_accumulation_to_list,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_incorrect_empty_list_check",
                apply=self._empty_list_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_off_by_one_range_bound",
                apply=self._off_by_one_range,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="fix_compare_and_swap_direction",
                apply=self._swap_comparison_direction,
                symptoms=("wrong",),
            ),
        ]

    def _return_sort_var(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and _same_name(node.value, {"sort", "sortt", "sorted", "sorted_list", "newlist", "new_lst", "result", "new", "lst1", "lst1"}):
                if node.value is None:
                    continue
                for retname in ("sort", "sortt", "sorted", "sorted_list", "newlist", "new_lst", "result", "new"):
                    if isinstance(node.value, ast.Name) and node.value.id != retname:
                        s, e = _span(source, node.value)
                        out.append(source[:s] + retname + source[e:])
                        break
        return out

    def _wrong_iterable_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and isinstance(node.target, ast.Name):
                if node.iter.id in {"a", "old_lst", "oldlist"} and node.target.id not in {"a", "old_lst", "oldlist"}:
                    s, e = _span(source, node.iter)
                    out.append(source[:s] + "lst" + source[e:])
                if node.iter.id == "lst" and node.target.id in {"i", "item", "element", "person", "ele", "n"}:
                    continue
        return out

    def _reset_outer_loop_after_move(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                body = node.body
                for idx, stmt in enumerate(body):
                    if isinstance(stmt, ast.If) and len(stmt.body) >= 2:
                        first = stmt.body[0]
                        second = stmt.body[1]
                        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Call):
                            if isinstance(first.value.func, ast.Attribute) and first.value.func.attr == "extend":
                                if isinstance(second, ast.Delete):
                                    insert_after = second
                                    new_text = source[_span(source, insert_after)[0]:_span(source, insert_after)[1]] + "\n            i=0"
                                    out.append(_splice(source, insert_after, new_text))
        return out

    def _remove_append_misnamed(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and isinstance(call.func.value, ast.Name):
                    if call.func.value.id in {"sort", "sorted", "sortt", "result", "newlist", "new_lst"} and call.args:
                        arg = call.args[0]
                        if isinstance(arg, ast.Name) and arg.id in {"biggest", "oldest", "largest", "smallest"}:
                            s, e = _span(source, arg)
                            out.append(source[:s] + "oldest" + source[e:])
        return out

    def _reverse_sort_to_selection(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "sort" and any(kw.arg == "reverse" and isinstance(kw.value, ast.Constant) and kw.value.value is True for kw in node.keywords):
                    s, e = _span(source, node)
                    out.append(source[:s] + " " + source[e:])
        return out

    def _smallest_to_largest_selection(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Lt):
                    out.append(_replace_node(source, node.ops[0], node.ops[0]))
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    if node.targets[0].id in {"smallest", "youngest"}:
                        s, e = _span(source, node.targets[0])
                        out.append(source[:s] + "biggest" + source[e:])
        return out

    def _compare_age_not_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                for side in [node.left] + node.comparators:
                    if isinstance(side, ast.Name) and side.id in {"oldest", "largest", "smallest", "biggest"}:
                        continue
                if isinstance(node.left, ast.Name) and node.left.id in {"oldest", "largest", "smallest", "biggest"}:
                    pass
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Subscript) and isinstance(right, ast.Name) and right.id in {"oldest", "largest", "smallest", "biggest"}:
                    continue
                if isinstance(right, ast.Name) and right.id in {"oldest", "largest", "smallest", "biggest"}:
                    if isinstance(left, ast.Name) and left.id in {"oldest", "largest", "smallest", "biggest"}:
                        continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                txt = ast.get_source_segment(source, node)
                if txt and ("[1]" not in txt) and any(v in txt for v in ["oldest", "largest", "smallest", "biggest"]) and ">" in txt or "<" in txt:
                    if isinstance(node.left, ast.Name) and node.left.id in {"oldest", "largest", "smallest", "biggest"}:
                        continue
        return out

    def _return_outside_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if node.body:
                    last = node.body[-1]
                    if isinstance(last, ast.Return):
                        s, e = _span(source, last)
                        out.append(source[:s] + "    " + source[e:])
        return out

    def _add_reverse_or_recursive_descending(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "sort_age":
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                        if isinstance(stmt.value.func, ast.Attribute) and stmt.value.func.attr == "sort":
                            seg = ast.get_source_segment(source, stmt.value)
                            if seg and "reverse=True" not in seg:
                                s, e = _span(source, stmt.value)
                                txt = source[s:e]
                                if txt.endswith(")"):
                                    out.append(source[:s] + txt[:-1] + ", reverse=True)" + source[e:])
        return out

    def _pop_to_remove_or_correct_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "append" and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "pop":
                        s, e = _span(source, arg.func.attr and arg)
                        out.append(source[:s] + arg.func.value.id + ".remove(" + source[_span(source, arg.args[0])[0]:_span(source, arg.args[0])[1]] + ")" + source[e:])
        return out

    def _tuple_accumulation_to_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Name) and node.value.id in {"tup", "result"}:
                    s, e = _span(source, node.value)
                    out.append(source[:s] + "list(" + source[s:e] + ")" + source[e:])
        return out

    def _empty_list_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "()" in txt:
                    s, e = _span(source, node)
                    out.append(source[:s] + txt.replace("()", "[]") + source[e:])
        return out

    def _off_by_one_range(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                seg = ast.get_source_segment(source, node)
                if seg and "len(lst)-1" in seg:
                    s, e = _span(source, node)
                    out.append(source[:s] + seg.replace("len(lst)-1", "len(lst)") + source[e:])
        return out

    def _swap_comparison_direction(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Lt):
                    seg = ast.get_source_segment(source, node)
                    if seg and "[1] <" in seg:
                        s, e = _span(source, node)
                        out.append(source[:s] + seg.replace("<", ">") + source[e:])
                elif isinstance(node.ops[0], ast.Gt):
                    seg = ast.get_source_segment(source, node)
                    if seg and "[1] >" in seg:
                        s, e = _span(source, node)
                        out.append(source[:s] + seg.replace(">", "<") + source[e:])
        return out