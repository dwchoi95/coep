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


def _name(source, node):
    return source[_span(source, node)[0]:_span(source, node)[1]]


class Fixer:
    def rules(self):
        return [
            Rule(name="use_param_not_builtin_list", apply=self._use_param_not_builtin_list, symptoms=("wrong", "err:NameError")),
            Rule(name="use_result_container_in_membership", apply=self._use_result_container_in_membership, symptoms=("wrong", "err:NameError")),
            Rule(name="append_instead_of_extend_scalar", apply=self._append_instead_of_extend_scalar, symptoms=("wrong", "err:TypeError")),
            Rule(name="append_call_not_method_object", apply=self._append_call_not_method_object, symptoms=("wrong", "err:AttributeError")),
            Rule(name="return_accumulator_instead_of_input", apply=self._return_accumulator_instead_of_input, symptoms=("wrong",)),
            Rule(name="fix_set_ordered_dict_dedup", apply=self._fix_set_ordered_dict_dedup, symptoms=("wrong",)),
            Rule(name="fix_counts_against_source_list", apply=self._fix_counts_against_source_list, symptoms=("wrong",)),
            Rule(name="invert_membership_condition", apply=self._invert_membership_condition, symptoms=("wrong",)),
            Rule(name="loop_over_input_not_result", apply=self._loop_over_input_not_result, symptoms=("wrong", "timeout")),
            Rule(name="fix_empty_return_none", apply=self._fix_empty_return_none, symptoms=("wrong",)),
            Rule(name="fix_wrong_variable_return", apply=self._fix_wrong_variable_return, symptoms=("wrong",)),
            Rule(name="range_stop_off_by_one", apply=self._range_stop_off_by_one, symptoms=("wrong",)),
            Rule(name="fix_append_subscript", apply=self._fix_append_subscript, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_append_method_return_assignment", apply=self._fix_append_method_return_assignment, symptoms=("wrong",)),
        ]

    def _use_param_not_builtin_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
                s, e = _span(source, node.iter)
                out.append(source[:s] + "lst" + source[e:])
        return out

    def _use_result_container_in_membership(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                left = node.left
                right = node.comparators[0]
                if isinstance(right, ast.Name) and right.id in {"lst", "list", "values"}:
                    rs, re = _span(source, right)
                    for cand in ("new_lst", "new_list", "output", "result", "new", "keep", "a", "pst", "store", "removed", "s", "final"):
                        out.append(source[:rs] + cand + source[re:])
                        break
        return out

    def _append_instead_of_extend_scalar(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name) or isinstance(arg, ast.Constant):
                    fs, fe = _span(source, node.func)
                    out.append(source[:fs] + _name(source, node.func.value) + ".append" + source[fe:])
        return out

    def _append_call_not_method_object(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "append":
                parent = node
                fs, fe = _span(source, parent)
                out.append(source[:fs] + _name(source, node.value) + ".append" + source[fe:])
            if isinstance(node, ast.Attribute) and node.attr == "extend":
                fs, fe = _span(source, node)
                out.append(source[:fs] + _name(source, node.value) + ".extend" + source[fe:])
        return out

    def _return_accumulator_instead_of_input(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "lst":
                s, e = _span(source, node.value)
                out.append(source[:s] + "new_lst" + source[e:])
        return out

    def _fix_wrong_variable_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        candidates = {"new_list", "newlst", "new_lst", "output", "result", "new", "final", "keep", "a", "s", "store", "removed", "pst", "seq", "l", "rem_lst"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id not in candidates:
                    continue
                body = None
                func = None
                for p in ast.walk(tree):
                    pass
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            assigned = []
            for n in ast.walk(func):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            assigned.append(t.id)
                if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                    assigned.append(n.target.id)
            for n in ast.walk(func):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id not in assigned:
                    if assigned:
                        s, e = _span(source, n.value)
                        out.append(source[:s] + assigned[-1] + source[e:])
        return out

    def _fix_set_ordered_dict_dedup(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "list" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "set":
                    s, e = _span(source, node)
                    out.append(source[:s] + "list(OrderedDict.fromkeys(" + _name(source, arg.args[0]) + "))" + source[e:])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "lists":
                s, e = _span(source, node.func)
                out.append(source[:s] + "list" + source[e:])
        return out

    def _fix_counts_against_source_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Attribute) and node.left.func.attr == "count":
                    owner = node.left.func.value
                    if isinstance(owner, ast.Name) and owner.id in {"lst", "list"}:
                        s, e = _span(source, owner)
                        out.append(source[:s] + "new_lst" + source[e:])
                if isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 1 and isinstance(node.left, ast.Call):
                    pass
        return out

    def _invert_membership_condition(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                op = node.test.ops[0]
                if isinstance(op, ast.In):
                    s, e = _span(source, node.test)
                    left = _name(source, node.test.left)
                    right = _name(source, node.test.comparators[0])
                    out.append(source[:s] + f"{left} not in {right}" + source[e:])
                elif isinstance(op, ast.NotIn):
                    s, e = _span(source, node.test)
                    left = _name(source, node.test.left)
                    right = _name(source, node.test.comparators[0])
                    out.append(source[:s] + f"{left} in {right}" + source[e:])
        return out

    def _loop_over_input_not_result(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id in {"list", "new_lst", "new_list"}:
                s, e = _span(source, node.iter)
                out.append(source[:s] + "lst" + source[e:])
        return out

    def _fix_empty_return_none(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                s, e = _span(source, node)
                out.append(source[:s] + "return lst" + source[e:])
            if isinstance(node, ast.Constant) and node.value is None:
                s, e = _span(source, node)
                out.append(source[:s] + "lst" + source[e:])
        return out

    def _range_stop_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    s, e = _span(source, arg)
                    out.append(source[:s] + f"len({arg.id})" + source[e:])
        return out

    def _fix_append_subscript(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Subscript):
                    s, e = _span(source, node)
                    out.append(source[:s] + _name(source, node.func.value) + ".append(" + _name(source, arg) + ")" + source[e:])
        return out

    def _fix_append_method_return_assignment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                    s, e = _span(source, node.value)
                    out.append(source[:s] + _name(source, call.func.value) + ".append(" + _name(source, call.args[0]) + ")" + source[e:])
        return out