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


def _replace_node(source, old, new):
    return _splice(source, old, new)


def _find_func(tree):
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == "sort_age":
            return n
    return None


def _name_text(source, node):
    return source[_span(source, node)[0]:_span(source, node)[1]]


class Fixer:
    def rules(self):
        return [
            Rule(name="return_missing_or_wrong_name",
                 apply=self._return_missing_or_wrong_name,
                 symptoms=("wrong", "err:NameError", "err:UnboundLocalError")),
            Rule(name="wrong_remove_target_from_selection",
                 apply=self._wrong_remove_target_from_selection,
                 symptoms=("wrong", "err:ValueError")),
            Rule(name="missing_return_at_end_of_function",
                 apply=self._missing_return_at_end_of_function,
                 symptoms=("wrong",)),
            Rule(name="missing_loop_wrap_for_single_pass_selection",
                 apply=self._missing_loop_wrap_for_single_pass_selection,
                 symptoms=("wrong",)),
            Rule(name="insert_copy_when_aliasing_input",
                 apply=self._insert_copy_when_aliasing_input,
                 symptoms=("wrong",)),
            Rule(name="append_mutated_expression_should_append_item",
                 apply=self._append_mutated_expression_should_append_item,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="index_item_vs_index_value_confusion",
                 apply=self._index_item_vs_index_value_confusion,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="compare_age_instead_of_whole_tuple",
                 apply=self._compare_age_instead_of_whole_tuple,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="min_to_max_for_descending_sort",
                 apply=self._min_to_max_for_descending_sort,
                 symptoms=("wrong",)),
            Rule(name="ascending_to_descending_comparison",
                 apply=self._ascending_to_descending_comparison,
                 symptoms=("wrong",)),
            Rule(name="off_by_one_range_end",
                 apply=self._off_by_one_range_end,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="remove_unwanted_reverse_or_print",
                 apply=self._remove_unwanted_reverse_or_print,
                 symptoms=("wrong",)),
            Rule(name="bubble_sort_direction_flip",
                 apply=self._bubble_sort_direction_flip,
                 symptoms=("wrong",)),
            Rule(name="fix_self_swap_in_bubble_or_selection_sort",
                 apply=self._fix_self_swap_in_bubble_or_selection_sort,
                 symptoms=("wrong",)),
            Rule(name="fix_recursive_base_and_recursive_step",
                 apply=self._fix_recursive_base_and_recursive_step,
                 symptoms=("wrong",)),
        ]

    def _return_missing_or_wrong_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        func = _find_func(tree)
        if not func:
            return []
        outs = []
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id not in {"sort", "lst", "new", "result", "output", "new_lst", "people", "product", "arranged", "combine"}:
                    continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "append":
                    parent = node.value.func.value
                    if isinstance(parent, ast.Name) and parent.id in {"final", "sort", "new_lst", "res", "people"}:
                        continue
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    tgt = node.targets[0].id
                    if tgt in {"final", "sort"}:
                        new_text = _name_text(source, node.value)
                        outs.append(_replace_node(source, node, f"{tgt} = {new_text}"))
            if isinstance(node, ast.Return) and node.value is not None:
                if isinstance(node.value, ast.Name) and node.value.id in {"sort", "lst", "new", "result", "output", "new_lst", "people", "product", "arranged"}:
                    if node.value.id not in {"people", "sort", "new_lst", "result", "product"}:
                        outs.append(_replace_node(source, node, f"return people" if node.value.id == "final" else _name_text(source, node)))
        if not outs:
            for node in ast.walk(func):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "append":
                        val = _name_text(source, node.value.args[0]) if node.value.args else ""
                        outs.append(_replace_node(source, node, _name_text(source, node).replace("final.append(i)", "people.append(i)").replace("sort.append(oldest)", "people.append(oldest)")))
                        break
        return list(dict.fromkeys(outs))

    def _wrong_remove_target_from_selection(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove":
                if node.args and isinstance(node.args[0], ast.Name):
                    arg = node.args[0].id
                    if arg in {"i", "x", "item", "oldest", "largest", "smallest", "biggest"}:
                        continue
                if node.args and isinstance(node.args[0], ast.Name):
                    continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "remove":
                    recv = _name_text(source, call.func.value)
                    arg = _name_text(source, call.args[0]) if call.args else ""
                    if arg in {"i", "x", "item"} and recv in {"lst", "a"}:
                        outs.append(_replace_node(source, node, _name_text(source, node).replace(f"{recv}.remove({arg})", f"{recv}.remove(oldest)").replace("lst.remove(i)", "lst.remove(i)")))
                    if arg == "i" and recv == "lst":
                        outs.append(_replace_node(source, node, _name_text(source, node).replace("lst.remove(i)", "lst.remove(oldest)")))
        return list(dict.fromkeys(outs))

    def _missing_return_at_end_of_function(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        func = _find_func(tree)
        if not func or not func.body:
            return []
        last = func.body[-1]
        if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
            if isinstance(last.value.func, ast.Name) and last.value.func.id == "print":
                return [_splice(source, last, "return " + _name_text(source, last.value.args[0]))] if last.value.args else []
        if isinstance(last, ast.Return):
            return []
        if any(isinstance(n, ast.Name) and n.id in {"final", "sort", "sortt", "people", "new_lst", "result", "output"} for n in ast.walk(func)):
            for n in ast.walk(func):
                if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
                    if isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "append":
                        pass
            body_text = source[_span(source, func.body[-1])[0]:_span(source, func.body[-1])[1]]
            if "return" not in body_text:
                if isinstance(last, ast.Expr):
                    return [_splice(source, last, body_text + "\n    return result")]
        return []

    def _missing_loop_wrap_for_single_pass_selection(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is not None:
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.BinOp):
                    continue
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp):
                txt = _name_text(source, node.value)
                if "+" in txt:
                    outs.append(_replace_node(source, node, "return new_lst"))
        return outs

    def _insert_copy_when_aliasing_input(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Name) and node.value.id == "lst" and node.targets[0].id in {"a", "l"}:
                    outs.append(_replace_node(source, node, f"{node.targets[0].id} = lst.copy()"))
        return outs

    def _append_mutated_expression_should_append_item(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if isinstance(node.value, ast.Name) and node.target.id in {"new_lst", "result", "sort"}:
                    outs.append(_replace_node(source, node, f"{node.target.id}.append({_name_text(source, node.value)})"))
        return outs

    def _index_item_vs_index_value_confusion(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Name) and left.id in {"smallest", "largest", "oldest", "biggest"}:
                    outs.append(_replace_node(source, node, f"{_name_text(source, left)}[1] < {_name_text(source, right)}[1]"))
        return list(dict.fromkeys(outs))

    def _compare_age_instead_of_whole_tuple(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                txt = _name_text(source, node)
                if ">" in txt and "[1]" not in txt and any(isinstance(c, ast.Name) for c in [node.left] + node.comparators):
                    left = _name_text(source, node.left)
                    right = _name_text(source, node.comparators[0])
                    outs.append(_replace_node(source, node, f"{left}[1] > {right}[1]"))
        return outs

    def _min_to_max_for_descending_sort(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "min":
                outs.append(_replace_node(source, node, source[_span(source, node.func)[0]:_span(source, node.func)[1]].replace("min", "max")))
        return outs

    def _ascending_to_descending_comparison(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left = _name_text(source, node.left)
                right = _name_text(source, node.comparators[0])
                if "[1]" in left or "[1]" in right:
                    outs.append(_replace_node(source, node, f"{left} > {right}"))
        return outs

    def _off_by_one_range_end(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
                argtxt = _name_text(source, node.args[0])
                if argtxt.endswith("-1"):
                    outs.append(_replace_node(source, node, f"range({argtxt[:-2]})"))
        return outs

    def _remove_unwanted_reverse_or_print(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
                    outs.append(_replace_node(source, node, ""))
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                    outs.append(_replace_node(source, node, ""))
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                    outs.append(_replace_node(source, node, "return lst"))
        return outs

    def _bubble_sort_direction_flip(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                txt = _name_text(source, node)
                if "[1]" in txt:
                    outs.append(_replace_node(source, node, txt.replace(">", "<")))
        return outs

    def _fix_self_swap_in_bubble_or_selection_sort(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 2:
                t1 = _name_text(source, node.targets[0])
                t2 = _name_text(source, node.targets[1])
                v1 = _name_text(source, node.value)
                if t1 == t2 and "[" in t1:
                    outs.append(_replace_node(source, node, f"{t1}, {t2} = {v1}, {t1}"))
        return outs

    def _fix_recursive_base_and_recursive_step(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        outs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = _name_text(source, node)
                if "sort_age(lst[1:])" in txt:
                    outs.append(_replace_node(source, node, txt.replace("sort_age(lst[1:])", "sort_age(lst[1:])")))
        return outs