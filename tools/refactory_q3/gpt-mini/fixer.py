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
            Rule(name="append_instead_of_extend_or_add_item", apply=self._append_fix, symptoms=("wrong", "err:TypeError")),
            Rule(name="wrong_membership_target", apply=self._membership_fix, symptoms=("wrong",)),
            Rule(name="wrong_list_variable_name", apply=self._name_fix, symptoms=("wrong", "err:NameError")),
            Rule(name="wrong_return_none_for_empty_list", apply=self._empty_return_fix, symptoms=("wrong",)),
            Rule(name="misused_append_and_count_brackets", apply=self._call_syntax_fix, symptoms=("wrong", "err:TypeError")),
            Rule(name="reverse_missing_call", apply=self._reverse_call_fix, symptoms=("wrong",)),
            Rule(name="missing_import_ordereddict", apply=self._import_fix, symptoms=("err:NameError",)),
            Rule(name="range_off_by_one_and_loop_guard", apply=self._range_fix, symptoms=("wrong", "timeout")),
            Rule(name="delete_loop_bound_uses_item_instead_of_count", apply=self._while_bound_fix, symptoms=("wrong", "timeout")),
            Rule(name="assignment_from_append_method", apply=self._append_assignment_fix, symptoms=("wrong", "err:AttributeError")),
            Rule(name="for_instead_of_while_or_wrong_iterator", apply=self._iterator_fix, symptoms=("wrong",)),
            Rule(name="return_wrong_variable", apply=self._return_var_fix, symptoms=("wrong",)),
            Rule(name="recursive_or_nested_duplicate_removal_bound", apply=self._nested_loop_fix, symptoms=("wrong", "timeout")),
        ]

    def _append_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                rhs = source[_span(source, node.value)[0]:_span(source, node.value)[1]]
                if not (rhs.startswith("[") and rhs.endswith("]")):
                    out.append(_splice(source, node, f"{source[_span(source, node.target)[0]:_span(source, node.target)[1]]} = {source[_span(source, node.target)[0]:_span(source, node.target)[1]]} + [{rhs}]"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and len(node.args) == 1:
                if isinstance(node.parent, ast.Assign) if hasattr(node, "parent") else False:
                    pass
        return out

    def _membership_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                if right in {"lst", "lst[:]"}:
                    out.append(_splice(source, node, f"{left} not in new_lst" if "new_lst" in source else f"{left} not in result" if "result" in source else f"{left} not in new_list"))
                if left == "i" and right == "lst":
                    out.append(_splice(source, node, "i not in result"))
        return out

    def _name_fix(self, source):
        repls = [("new_lst", "new_list"), ("new_list", "new_lst"), ("element", "e"), ("e", "element"), ("remove_mutiple", "remove_multiple"), ("lists(", "list(")]
        out = []
        for a, b in repls:
            if a in source:
                out.append(source.replace(a, b, 1))
        return out

    def _empty_return_fix(self, source):
        if "return None" in source:
            return [source.replace("return None", "return []", 1)]
        return []

    def _call_syntax_fix(self, source):
        out = []
        repls = [("count[entry]", "count(entry)"), ("append[entry]", "append(entry)"), ("append.item", "append(item)"), ("append[i]", "append(i)"), ("append[i]", "append(i)")]
        for a, b in repls:
            if a in source:
                out.append(source.replace(a, b, 1))
        return out

    def _reverse_call_fix(self, source):
        if "lst.reverse" in source and "lst.reverse()" not in source:
            return [source.replace("lst.reverse", "lst.reverse()", 1)]
        return []

    def _import_fix(self, source):
        if "OrderedDict.fromkeys" in source and "from collections import OrderedDict" not in source:
            return ["from collections import OrderedDict\n\n" + source]
        return []

    def _range_fix(self, source):
        out = []
        if "while i < len(lst)+1" in source:
            out.append(source.replace("while i < len(lst)+1", "while x < len(lst)", 1).replace("if lst[x] in new:", "if lst[x] not in new:", 1).replace("else:\n            continue", "else:\n            new += [lst[x]]", 1))
        if "while i!=len(lst)" in source:
            out.append(source.replace("while i!=len(lst)", "while i < len(lst)", 1))
        return out

    def _while_bound_fix(self, source):
        if "while j < i" in source:
            return [source.replace("while j < i", "while j < lst.count(i)", 1)]
        return []

    def _append_assignment_fix(self, source):
        out = []
        if "newlst=newlst.append(i)" in source:
            out.append(source.replace("newlst=newlst.append(i)", "newlst.append(i)", 1))
        if "removed = removed.append(e)" in source:
            out.append(source.replace("removed = removed.append(e)", "removed.append(e)", 1))
        return out

    def _iterator_fix(self, source):
        out = []
        if "for i in lst and not result" in source:
            out.append(source.replace("for i in lst and not result:", "for i in lst:", 1).replace("result += result + i", "result += [i]", 1))
        if "for item in list:" in source:
            out.append(source.replace("for item in list:", "for item in lst:", 1))
        return out

    def _return_var_fix(self, source):
        out = []
        if "return new_lst" in source and "new_lst =" in source and "new_list" in source:
            out.append(source.replace("return new_lst", "return new_list", 1))
        if "return new_lst" in source and "output =" in source and "final" in source:
            out.append(source.replace("return new_lst", "return output", 1))
        if "return new_lst" in source and "new_list" not in source and "new_lst" in source:
            out.append(source.replace("return new_lst", "return new_list", 1))
        return out

    def _nested_loop_fix(self, source):
        out = []
        if "lst = lst[:j] + lst[j+1:]" in source and "else:\n                j += 1" not in source:
            out.append(source.replace("if lst[i] == lst[j]:\n                lst = lst[:j] + lst[j+1:]\n", "if lst[i] == lst[j]:\n                lst = lst[:j] + lst[j+1:]\n            else:\n                j += 1\n", 1))
        if "while i<=len(lst)" in source:
            out.append(source.replace("while i<=len(lst)", "while i<=len(lst)-1", 1))
        return out