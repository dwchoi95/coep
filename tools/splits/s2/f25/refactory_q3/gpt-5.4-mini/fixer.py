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


def _name_of(func):
    return getattr(func, "__name__", "rule")


class Fixer:
    def rules(self):
        return [
            Rule(name="compare_against_output_not_input", apply=self._compare_against_output_not_input, symptoms=("wrong",)),
            Rule(name="compare_against_lst_not_output", apply=self._compare_against_lst_not_output, symptoms=("wrong",)),
            Rule(name="wrong_target_container_in_membership", apply=self._wrong_target_container_in_membership, symptoms=("wrong",)),
            Rule(name="wrong_initial_container_type", apply=self._wrong_initial_container_type, symptoms=("wrong", "err:TypeError")),
            Rule(name="append_brackets_and_call_fixes", apply=self._append_brackets_and_call_fixes, symptoms=("wrong", "err:TypeError")),
            Rule(name="wrong_return_original_list", apply=self._wrong_return_original_list, symptoms=("wrong",)),
            Rule(name="wrong_return_none_or_missing_return", apply=self._wrong_return_none_or_missing_return, symptoms=("wrong",)),
            Rule(name="membership_loop_over_list_name", apply=self._membership_loop_over_list_name, symptoms=("wrong",)),
            Rule(name="count_condition_to_seen_membership", apply=self._count_condition_to_seen_membership, symptoms=("wrong",)),
            Rule(name="remove_set_for_order_preservation", apply=self._remove_set_for_order_preservation, symptoms=("wrong",)),
            Rule(name="return_inside_loop_premature", apply=self._return_inside_loop_premature, symptoms=("wrong",)),
            Rule(name="self_referential_concat_to_append", apply=self._self_referential_concat_to_append, symptoms=("wrong", "err:TypeError")),
            Rule(name="remove_inplace_list_mutation_in_loop", apply=self._remove_inplace_list_mutation_in_loop, symptoms=("wrong", "timeout")),
            Rule(name="fix_reverse_call_and_reverse_method", apply=self._fix_reverse_call_and_reverse_method, symptoms=("wrong", "err:AttributeError")),
            Rule(name="fix_indexing_and_off_by_one_loops", apply=self._fix_indexing_and_off_by_one_loops, symptoms=("wrong", "err:IndexError")),
            Rule(name="reset_flag_inside_outer_loop", apply=self._reset_flag_inside_outer_loop, symptoms=("wrong",)),
            Rule(name="fix_list_append_and_extend_misuse", apply=self._fix_list_append_and_extend_misuse, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_tuple_accumulator_to_list", apply=self._fix_tuple_accumulator_to_list, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_for_over_list_object", apply=self._fix_for_over_list_object, symptoms=("wrong",)),
            Rule(name="fix_reverse_dedup_to_forward_seen", apply=self._fix_reverse_dedup_to_forward_seen, symptoms=("wrong",)),
            Rule(name="fix_pop_and_remove_misuse", apply=self._fix_pop_and_remove_misuse, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_function_return_expression_name", apply=self._fix_function_return_expression_name, symptoms=("wrong",)),
        ]

    def _compare_against_output_not_input(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.left, ast.Name) and node.left.id in {"lst", "list", "lst0"}:
                    if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"new_lst", "newlist", "new_list", "result", "output", "keep", "t", "o", "seq", "new"}:
                        continue
                    left_s, left_e = _span(source, node.left)
                    comp_s, comp_e = _span(source, node.comparators[0])
                    out.append(source[:left_s] + source[comp_s:comp_e] + " not in " + source[left_e:comp_s] + source[left_s:left_e] + source[comp_e:])
        return out

    def _compare_against_lst_not_output(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        targets = {"lst", "list"}
        outputs = {"new_lst", "newlist", "new_list", "result", "output", "keep", "t", "o", "seq", "new"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in targets:
                    if isinstance(node.left, ast.Name) and node.left.id in outputs:
                        ls, le = _span(source, node.left)
                        rs, re = _span(source, node.comparators[0])
                        out.append(source[:ls] + source[rs:re] + " not in " + source[le:rs] + source[ls:le] + source[re:])
        return out

    def _wrong_target_container_in_membership(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        seen_names = {"new_lst", "newlist", "new_list", "result", "output", "keep", "t", "o", "seq", "new", "lst1", "extra", "sub_list", "new_list"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"lst", "list"}:
                    if isinstance(node.left, ast.Name) and node.left.id in seen_names:
                        ls, le = _span(source, node.left)
                        rs, re = _span(source, node.comparators[0])
                        out.append(source[:ls] + source[rs:re] + " not in " + source[le:rs] + source[ls:le] + source[re:])
        return out

    def _wrong_initial_container_type(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Tuple):
                    txt = ast.get_source_segment(source, node.value)
                    if txt is not None:
                        out.append(_replace_node(source, node.value, "[]"))
                elif isinstance(node.value, ast.Subscript):
                    txt = ast.get_source_segment(source, node.value)
                    if txt and txt.endswith("[0]"):
                        out.append(_replace_node(source, node.value, "[]"))
                elif isinstance(node.value, ast.Attribute) and isinstance(node.value.attr, str) and node.value.attr == "reverse":
                    out.append(_replace_node(source, node.value, "[]"))
        return out

    def _append_brackets_and_call_fixes(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "append":
                    if len(node.value.args) == 1:
                        arg = node.value.args[0]
                        out.append(_replace_node(source, node.value, f"{ast.get_source_segment(source, node.value.func.value)}.append({ast.get_source_segment(source, arg)})"))
            if isinstance(node, ast.Attribute) and node.attr == "append":
                parent = getattr(node, "parent", None)
        return out

    def _wrong_return_original_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "lst":
                out.append(_replace_node(source, node.value, "new_lst"))
        return out

    def _wrong_return_none_or_missing_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(tree))
        if not has_return:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return_stmt = "\n    return output"
                    out.append(source[:_span(source, node)[1]] + return_stmt + source[_span(source, node)[1]:])
                    break
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                out.append(_replace_node(source, node, "return output"))
        return out

    def _membership_loop_over_list_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id in {"list", "lst1", "new_lst"}:
                out.append(_replace_node(source, node.iter, "lst"))
        return out

    def _count_condition_to_seen_membership(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left and right and ".count(" in left and right == "0":
                    out.append(_replace_node(source, node, left.replace(".count(", ".__contains__(").replace(")==0", ")==False")))
        return out

    def _remove_set_for_order_preservation(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "set" and len(node.args) == 1:
                arg = ast.get_source_segment(source, node.args[0])
                if arg:
                    out.append(_replace_node(source, node, "output"))
        return out

    def _return_inside_loop_premature(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                parents = []
                cur = getattr(node, "parent", None)
                while cur is not None:
                    parents.append(cur)
                    cur = getattr(cur, "parent", None)
                if any(isinstance(p, (ast.For, ast.While)) for p in parents):
                    out.append(_replace_node(source, node, "continue"))
        return out

    def _self_referential_concat_to_append(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                rhs = ast.get_source_segment(source, node.value.right)
                lhs = ast.get_source_segment(source, node.value.left)
                if rhs and lhs and lhs.strip() in {"result", "new_lst", "new_list", "output", "new"}:
                    out.append(_replace_node(source, node.value, f"{lhs} + [{rhs}]"))
        return out

    def _remove_inplace_list_mutation_in_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove":
                val = ast.get_source_segment(source, node.func.value)
                if val in {"lst", "values"}:
                    out.append(_replace_node(source, node, "output.remove(" + ast.get_source_segment(source, node.args[0]) + ")"))
        return out

    def _fix_reverse_call_and_reverse_method(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "reverse" and isinstance(getattr(node, "ctx", None), ast.Load):
                out.append(_replace_node(source, node, f"{ast.get_source_segment(source, node.value)}.reverse()"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "reverse":
                pass
        return out

    def _fix_indexing_and_off_by_one_loops(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                if len(node.iter.args) == 1:
                    arg = ast.get_source_segment(source, node.iter.args[0])
                    if arg and "-1" in arg.replace(" ", ""):
                        out.append(_replace_node(source, node.iter.args[0], arg.replace("-1", "")))
        return out

    def _reset_flag_inside_outer_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "check":
                parents = []
                cur = getattr(node, "parent", None)
                while cur is not None:
                    parents.append(cur)
                    cur = getattr(cur, "parent", None)
                if any(isinstance(p, ast.For) for p in parents):
                    out.append(_replace_node(source, node.value, "True"))
        return out

    def _fix_list_append_and_extend_misuse(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if len(node.args) == 1 and isinstance(node.func.value, ast.Name):
                    out.append(_replace_node(source, node, f"{ast.get_source_segment(source, node.func.value)}.append({ast.get_source_segment(source, node.args[0])})"))
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.right)
                if right and right.endswith(".append(elem)"):
                    out.append(_replace_node(source, node, f"{left} + [{right.split('(')[1].rstrip(')')}]"))
        return out

    def _fix_tuple_accumulator_to_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.value, ast.Tuple):
                out.append(_replace_node(source, node.value, "[" + ", ".join(ast.get_source_segment(source, e) for e in node.value.elts) + "]"))
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
                out.append(_replace_node(source, node.value, "[]"))
        return out

    def _fix_for_over_list_object(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id in {"list", "lst1", "new_list"}:
                out.append(_replace_node(source, node.iter, "lst"))
        return out

    def _fix_reverse_dedup_to_forward_seen(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "sort":
                out.append(_replace_node(source, node, ""))
        return out

    def _fix_pop_and_remove_misuse(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "pop":
                if isinstance(node.ctx, ast.Load):
                    out.append(_replace_node(source, node, f"{ast.get_source_segment(source, node.value)}.pop()"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop" and len(node.args) == 1:
                arg = ast.get_source_segment(source, node.args[0])
                if arg and not arg.isdigit():
                    out.append(_replace_node(source, node, f"{ast.get_source_segment(source, node.func.value)}.pop({arg})"))
        return out

    def _fix_function_return_expression_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"new_list", "newlst", "newlist", "result", "output"}:
                out.append(_replace_node(source, node.value, node.value.id.replace("new_list", "new_list")))
        return out