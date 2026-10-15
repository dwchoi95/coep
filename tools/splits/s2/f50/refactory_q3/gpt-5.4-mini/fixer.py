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


def _find_parent(tree):
    parent = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parent[c] = p
    return parent


def _replace_name_in_target(source, old, new, target_fn="remove_extras"):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == target_fn]:
        parent = _find_parent(fn)
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and node.id == old:
                p = parent.get(node)
                if isinstance(p, ast.Attribute) and p.attr == old and p.value is node:
                    continue
                out.append(source[:_span(source, node)[0]] + new + source[_span(source, node)[1]:])
    return list(dict.fromkeys(out))


class Fixer:
    def rules(self):
        return [
            Rule("wrong_iterable_name_list_to_lst", self._iterable_name_fix, ("wrong",)),
            Rule("wrong_membership_target_lst_to_output", self._membership_target_fix, ("wrong",)),
            Rule("wrong_return_variable", self._wrong_return_fix, ("wrong",)),
            Rule("append_result_of_append", self._append_result_fix, ("wrong",)),
            Rule("append_method_call_missing_parens", self._append_method_fix, ("wrong",)),
            Rule("extend_scalar_to_append", self._extend_scalar_fix, ("wrong",)),
            Rule("count_self_vs_output", self._count_self_fix, ("wrong",)),
            Rule("set_or_ordereddict_to_list_ordered", self._ordered_set_fix, ("wrong",)),
            Rule("tuple_builder_to_list_builder", self._tuple_to_list_fix, ("wrong",)),
            Rule("list_name_typos", self._name_typos_fix, ("wrong",)),
            Rule("append_to_wrong_container", self._wrong_container_append_fix, ("wrong",)),
            Rule("remove_extras_return_none_or_missing", self._missing_return_fix, ("wrong",)),
        ]

    def _iterable_name_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
                s, e = _span(source, node.iter)
                out.append(source[:s] + "lst" + source[e:])
        return list(dict.fromkeys(out))

    def _membership_target_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "lst":
                    left = node.left
                    if isinstance(left, ast.Name) and left.id != "lst":
                        continue
                    s1, e1 = _span(source, node.left)
                    s2, e2 = _span(source, node.comparators[0])
                    out.append(source[:s1] + source[s1:e1] + " not in " + source[s2:e2] + source[e2:])
        return list(dict.fromkeys(out))

    def _wrong_return_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id in {"lst", "x", "i", "element", "entry"}:
                    continue
                s, e = _span(source, node.value)
                if "new" in node.value.id.lower() or "keep" in node.value.id.lower() or "result" in node.value.id.lower() or "output" in node.value.id.lower() or "new_list" in node.value.id.lower() or "newlst" in node.value.id.lower():
                    out.append(source[:s] + "output" + source[e:])
        return list(dict.fromkeys(out))

    def _append_result_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                    s, e = _span(source, node.value)
                    obj = source[_span(source, call.func.value)[0]:_span(source, call.func.value)[1]]
                    arg = source[_span(source, call.args[0])[0]:_span(source, call.args[0])[1]] if call.args else None
                    if arg:
                        out.append(source[:s] + obj + " = " + obj + " + [" + arg + "]" + source[e:])
        return list(dict.fromkeys(out))

    def _append_method_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "append":
                parent = _find_parent(tree).get(node)
                if isinstance(parent, ast.Call) and parent.func is node and len(parent.args) == 1:
                    continue
                s, e = _span(source, node)
                out.append(source[:s] + source[s:e] + "append" + source[e:])
        return list(dict.fromkeys(out))

    def _extend_scalar_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    s, e = _span(source, arg)
                    out.append(source[:s] + "[" + source[s:e] + "]" + source[e:])
        return list(dict.fromkeys(out))

    def _count_self_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Name):
                    if node.left.id == "lst" and node.comparators[0].id != "lst":
                        s, e = _span(source, node.left)
                        out.append(source[:s] + node.comparators[0].id + source[e:])
        return list(dict.fromkeys(out))

    def _ordered_set_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        if "set(" in source:
            return [source.replace("set(lst)", "OrderedDict.fromkeys(lst)").replace("set(values)", "OrderedDict.fromkeys(values)")]
        if "list(OrderedDict.fromkeys" in source and "from collections import OrderedDict" not in source:
            return ["from collections import OrderedDict\n\n" + source]
        return []

    def _tuple_to_list_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
                s, e = _span(source, node.value)
                txt = source[s:e]
                if txt.startswith("(") and txt.endswith(")"):
                    out.append(source[:s] + "[" + txt[1:-1] + "]" + source[e:])
        return list(dict.fromkeys(out))

    def _name_typos_fix(self, source):
        out = []
        replacements = [("neW_lst", "new_lst"), ("new_list", "newlst"), ("newlst", "new_list")]
        for old, new in replacements:
            if old in source:
                out.append(source.replace(old, new))
        return list(dict.fromkeys(out))

    def _wrong_container_append_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if isinstance(node.func.value, ast.Name) and node.func.value.id in {"lst", "list"}:
                    s, e = _span(source, node.func.value)
                    out.append(source[:s] + "new_list" + source[e:])
        return list(dict.fromkeys(out))

    def _missing_return_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        if any(isinstance(n, ast.Return) for n in ast.walk(tree)):
            return []
        fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "remove_extras"]
        out = []
        for fn in fns:
            if fn.body:
                last = fn.body[-1]
                if isinstance(last, ast.Expr):
                    s, e = _span(source, last)
                    out.append(source[:s] + "return output" + source[e:])
        return list(dict.fromkeys(out))