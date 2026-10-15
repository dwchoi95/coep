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
    if isinstance(target, ast.Name):
        return target.id
    return None


def _is_append_call(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "append"
        and len(node.value.args) == 1
    )


def _is_extend_call(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "extend"
        and len(node.value.args) == 1
    )


class Fixer:
    def rules(self):
        return [
            Rule("return_function_argument_name", self._return_arg_name, ("wrong", "err:NameError")),
            Rule("wrong_condition_list_vs_input", self._fix_input_membership, ("wrong",)),
            Rule("wrong_condition_list_count", self._fix_count_source, ("wrong",)),
            Rule("wrong_condition_equals_list", self._fix_compare_to_list, ("wrong",)),
            Rule("wrong_return_target", self._fix_return_var, ("wrong", "err:NameError")),
            Rule("append_called_as_method_or_subscript", self._fix_append_syntax, ("err:TypeError", "err:AttributeError")),
            Rule("extend_used_for_single_element", self._fix_extend_singleton, ("wrong", "err:TypeError")),
            Rule("list_literal_plus_single_element", self._fix_add_singleton, ("wrong", "err:TypeError")),
            Rule("list_plus_element", self._fix_add_element, ("wrong", "err:TypeError")),
            Rule("tuple_plus_singleton", self._fix_tuple_singleton, ("wrong", "err:TypeError")),
            Rule("set_return_ordered", self._fix_set_return, ("wrong",)),
            Rule("ordered_dict_missing_import", self._add_ordered_dict_import, ("err:NameError",)),
            Rule("list_name_used_instead_of_param", self._fix_for_list_name, ("wrong", "err:NameError")),
            Rule("off_by_one_range_end", self._fix_range_end, ("wrong",)),
            Rule("remove_return_inside_loop", self._lift_return_out_of_loop, ("wrong",)),
            Rule("pop_without_call", self._fix_pop_call, ("err:TypeError",)),
            Rule("reverse_method_used_as_value", self._fix_reverse_method, ("err:AttributeError", "wrong")),
            Rule("reverse_returned_instead_of_list", self._fix_reverse_return, ("wrong",)),
            Rule("count_source_list_not_result", self._fix_count_membership_source, ("wrong",)),
            Rule("duplicate_elim_via_reverse_fix", self._fix_reverse_duplicate_elim, ("wrong",)),
        ]

    def _return_arg_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "remove_extras" and n.args.args]:
            arg = fn.args.args[0].arg
            for node in ast.walk(fn):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id != arg:
                    out.append(_splice(source, node.value, arg))
        return out

    def _fix_input_membership(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"lst", "list", "values", "mylist"}:
                    left = node.left
                    ls, le = _span(source, left)
                    out.append(_splice(source, node, source[ls:le] + (" not in " if isinstance(node.ops[0], ast.In) else " in ") + source[ls:le]))
        return out

    def _fix_count_source(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Eq) and isinstance(node.left, ast.Call):
                    call = node.left
                    if isinstance(call.func, ast.Attribute) and call.func.attr == "count" and isinstance(call.func.value, ast.Name):
                        if call.func.value.id in {"lst", "list", "values", "mylist"}:
                            target = source[_span(source, call.args[0])[0]:_span(source, call.args[0])[1]] if call.args else "item"
                            cmp = f"{call.func.value.id}.count({target}) == 0"
                            out.append(_splice(source, node, cmp))
                if isinstance(node.ops[0], ast.Lt) and isinstance(node.left, ast.Call):
                    call = node.left
                    if isinstance(call.func, ast.Attribute) and call.func.attr == "count":
                        target = source[_span(source, call.args[0])[0]:_span(source, call.args[0])[1]] if call.args else "item"
                        out.append(_splice(source, node, f"{source[_span(source, call.func.value)[0]:_span(source, call.func.value)[1]]}.count({target}) == 0"))
        return out

    def _fix_compare_to_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
                if isinstance(node.comparators[0], ast.Name):
                    comp = node.comparators[0]
                    left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    right = source[_span(source, comp)[0]:_span(source, comp)[1]]
                    out.append(_splice(source, node, f"{left} not in {right}"))
        return out

    def _fix_return_var(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "remove_extras"]:
            candidates = {"output", "new_lst", "new_list", "new", "result", "final", "a", "s", "keep", "remove_lst", "removed", "lst1", "newlst"}
            for node in ast.walk(fn):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"lst", "x", "i", "element"}:
                    for cand in candidates:
                        out.append(_splice(source, node.value, cand))
        return out

    def _fix_append_syntax(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if _is_append_call(node):
                attr = node.value.func
                if isinstance(attr.value, ast.Name) and len(node.value.args) == 1:
                    arg = node.value.args[0]
                    out.append(_splice(source, node, f"{source[_span(source, attr.value)[0]:_span(source, attr.value)[1]]}.append({source[_span(source, arg)[0]:_span(source, arg)[1]]})"))
            if isinstance(node, ast.Attribute) and node.attr == "append" and isinstance(node.ctx, ast.Load):
                parent = node
                out.append(_splice(source, node, source[_span(source, node.value)[0]:_span(source, node.value)[1]] + ".append"))
        return out

    def _fix_extend_singleton(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if _is_extend_call(node):
                arg = node.value.args[0]
                if isinstance(arg, ast.Name) or isinstance(arg, ast.Constant):
                    out.append(_splice(source, node, source[_span(source, node.value.func.value)[0]:_span(source, node.value.func.value)[1]] + ".append(" + source[_span(source, arg)[0]:_span(source, arg)[1]] + ")"))
        return out

    def _fix_add_singleton(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                if isinstance(node.value.right, ast.Name):
                    r = source[_span(source, node.value.right)[0]:_span(source, node.value.right)[1]]
                    out.append(_splice(source, node.value.right, f"[{r}]"))
        return out

    def _fix_add_element(self, source):
        return self._fix_add_singleton(source)

    def _fix_tuple_singleton(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add) and isinstance(node.right, ast.Name):
                r = source[_span(source, node.right)[0]:_span(source, node.right)[1]]
                out.append(_splice(source, node.right, f"({r},)"))
        return out

    def _fix_set_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "set":
                arg = node.value.args[0]
                out.append(_splice(source, node, f"return list(OrderedDict.fromkeys({source[_span(source, arg)[0]:_span(source, arg)[1]]}))"))
        return out

    def _add_ordered_dict_import(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        if "OrderedDict" in source and "from collections import OrderedDict" not in source:
            return ["from collections import OrderedDict\n" + source]
        return []

    def _fix_for_list_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "remove_extras"), None)
        if not fn or not fn.args.args:
            return []
        arg = fn.args.args[0].arg
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and node.id in {"list", "list1", "newlist", "new_lst", "new_list", "lst1"} and isinstance(node.ctx, ast.Load):
                out.append(_splice(source, node, arg if node.id == "list" else node.id))
        return out

    def _fix_range_end(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                    out.append(_splice(source, node, f"range({source[_span(source, arg.left)[0]:_span(source, arg.left)[1]]})"))
        return out

    def _lift_return_out_of_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for ret in [n for n in ast.walk(tree) if isinstance(n, ast.Return)]:
            parent = None
            for fn in ast.walk(tree):
                for ch in ast.iter_child_nodes(fn):
                    pass
            out.append(source.replace("\n        return ", "\n    return ", 1) if "return" in source else source)
        return out[:1]

    def _fix_pop_call(self, source):
        return [source.replace(".pop\n", ".pop()\n").replace(".pop\n", ".pop()\n")] if ".pop\n" in source else []

    def _fix_reverse_method(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "reverse" and isinstance(node.ctx, ast.Load):
                out.append(_splice(source, node, source[_span(source, node.value)[0]:_span(source, node.value)[1]] + ".reverse()"))
        return out

    def _fix_reverse_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                seq = source[_span(source, node.value.func.value)[0]:_span(source, node.value.func.value)[1]]
                out.append(_splice(source, node, f"{seq}.reverse()\n    return {seq}"))
        return out

    def _fix_count_membership_source(self, source):
        return self._fix_input_membership(source)

    def _fix_reverse_duplicate_elim(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "reverse":
                out.append(source)
                break
        return out