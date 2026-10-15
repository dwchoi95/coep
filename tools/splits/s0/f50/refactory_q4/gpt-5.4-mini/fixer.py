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


def _expr_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _find_func(tree):
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == "sort_age":
            return n
    return None


class Fixer:
    def rules(self):
        return [
            Rule("wrong_return_name", self._wrong_return_name, ("wrong",)),
            Rule("final_statement_missing_return", self._missing_return, ("wrong",)),
            Rule("assignment_to_self_or_wrong_var", self._assign_target_fix, ("wrong",)),
            Rule("remove_operand_should_be_name", self._remove_operand_fix, ("wrong", "err:TypeError")),
            Rule("append_tuple_item_misuse", self._append_tuple_fix, ("wrong", "err:TypeError")),
            Rule("compare_age_not_whole_tuple", self._compare_age_fix, ("wrong",)),
            Rule("selection_sort_direction_fix", self._selection_direction_fix, ("wrong",)),
            Rule("selection_sort_index_bounds", self._range_bound_fix, ("wrong", "err:IndexError")),
            Rule("reverse_after_ascending_sort", self._reverse_after_sort_fix, ("wrong",)),
            Rule("insert_return_after_recursive_remove", self._recursive_remove_fix, ("wrong",)),
            Rule("call_reverse_on_result_not_return", self._reverse_return_fix, ("wrong",)),
        ]

    def _wrong_return_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"sort", "final", "new"}:
                if node.value.id != "sort" and "sort" in source:
                    continue
                out.append(_splice(source, node.value, "sort"))
        return out

    def _missing_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        func = _find_func(tree)
        if not func or not func.body:
            return []
        last = func.body[-1]
        if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call) and getattr(last.value.func, "id", "") == "print":
            return [_splice(source, last, "return " + _expr_text(source, last.value.args[0]) if last.value.args else "return lst")]
        return []

    def _assign_target_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                t = node.targets[0]
                if isinstance(t, ast.Name) and isinstance(node.value, ast.Name) and t.id != node.value.id:
                    if node.value.id in {"n", "i", "j", "x", "tpl", "smallsest", "oldest", "largest", "biggest", "smallest"}:
                        out.append(_splice(source, node.value, t.id))
        return out

    def _remove_operand_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "remove" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    continue
                if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float, str, tuple)):
                    for assign in ast.walk(tree):
                        if isinstance(assign, ast.Assign) and len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name):
                            if assign.targets[0].id in {"biggest", "largest", "oldest", "smallest", "max_age", "minimum"}:
                                out.append(_splice(source, arg, assign.targets[0].id))
                                break
        return out

    def _append_tuple_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name):
                    if node.target.id in {"result", "newlst", "new_list", "output", "sort"}:
                        out.append(_splice(source, node.value, f"({node.value.id},)"))
        return out

    def _compare_age_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left = node.left
                comp = node.comparators[0]
                ltxt = _expr_text(source, left)
                ctxt = _expr_text(source, comp)
                if ltxt.endswith("]") and ctxt.endswith("]") and ("[1]" not in ltxt or "[1]" not in ctxt):
                    out.append(_splice(source, node, f"{ltxt}[1] {ast.dump(node.ops[0])[ast.dump(node.ops[0]).find('(')+1:-1]} {ctxt}[1]"))
                if isinstance(left, ast.Name) and left.id in {"largest", "smallest", "oldest"} and not ltxt.endswith("[1]"):
                    op = "<" if isinstance(node.ops[0], ast.Gt) else ">"
                    out.append(_splice(source, node, f"{ctxt}[1] {op} {ltxt}[1]"))
                if isinstance(comp, ast.Name) and comp.id in {"largest", "smallest", "oldest"} and not ctxt.endswith("[1]"):
                    op = ">" if isinstance(node.ops[0], ast.Gt) else "<"
                    out.append(_splice(source, node, f"{ltxt}[1] {op} {ctxt}[1]"))
        return out

    def _selection_direction_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Lt):
                    out.append(_splice(source, node.ops[0], ">"))
                elif isinstance(node.ops[0], ast.Gt):
                    out.append(_splice(source, node.ops[0], "<"))
        return out

    def _range_bound_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                    if isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                        out.append(_splice(source, arg.right, "0"))
                    elif isinstance(arg.left, ast.Constant) and arg.left.value == 1:
                        out.append(_splice(source, arg.left, "0"))
        return out

    def _reverse_after_sort_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                    parent = _find_func(tree)
                    if parent and any(isinstance(x, ast.Return) for x in parent.body):
                        out.append(_splice(source, node, "return lst"))
        return out

    def _recursive_remove_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                txt = _expr_text(source, node.value.right)
                if "sort_age(lst.remove(holder))" in txt:
                    out.append(_splice(source, node.value.right, "sort_age(lst)"))
        return out

    def _reverse_return_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "reverse":
                    out.append(_splice(source, node, "lst.reverse()\n    return lst"))
        return out