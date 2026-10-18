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
            Rule(name="list_name_to_param", apply=self._list_name_to_param, symptoms=("wrong",)),
            Rule(name="wrong_membership_container", apply=self._wrong_membership_container, symptoms=("wrong",)),
            Rule(name="wrong_return_name", apply=self._wrong_return_name, symptoms=("wrong",)),
            Rule(name="append_result_instead_of_input", apply=self._append_result_instead_of_input, symptoms=("wrong",)),
            Rule(name="append_called_as_attribute", apply=self._append_called_as_attribute, symptoms=("wrong",)),
            Rule(name="count_against_input_instead_of_output", apply=self._count_against_input_instead_of_output, symptoms=("wrong",)),
            Rule(name="extend_or_add_singleton_item", apply=self._extend_or_add_singleton_item, symptoms=("wrong",)),
            Rule(name="append_return_value_mistake", apply=self._append_return_value_mistake, symptoms=("wrong",)),
            Rule(name="set_or_ordereddict_needs_list", apply=self._set_or_ordereddict_needs_list, symptoms=("wrong",)),
            Rule(name="missing_ordereddict_import", apply=self._missing_ordereddict_import, symptoms=("err:NameError",)),
            Rule(name="return_none_for_empty_list", apply=self._return_none_for_empty_list, symptoms=("wrong",)),
            Rule(name="wrong_list_element_variable", apply=self._wrong_list_element_variable, symptoms=("wrong",)),
            Rule(name="reverse_return_none", apply=self._reverse_return_none, symptoms=("wrong",)),
            Rule(name="count_based_remove_self", apply=self._count_based_remove_self, symptoms=("wrong",)),
            Rule(name="off_by_one_range_bound", apply=self._off_by_one_range_bound, symptoms=("wrong",)),
            Rule(name="strict_comparison_to_self", apply=self._strict_comparison_to_self, symptoms=("wrong",)),
        ]

    def _list_name_to_param(self, source):
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

    def _wrong_membership_container(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "lst":
                    ls, le = _span(source, node.comparators[0])
                    out.append(source[:ls] + ast.get_source_segment(source, node.left) + source[le:])
                elif isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"list", "values"}:
                    ls, le = _span(source, node.comparators[0])
                    out.append(source[:ls] + "new_lst" + source[le:])
        return out

    def _wrong_return_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"new_list", "newlst", "lst", "x", "i"}:
                ls, le = _span(source, node.value)
                out.append(source[:ls] + "new_lst" + source[le:])
        return out

    def _append_result_instead_of_input(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                    arg = node.args[0].id
                    if arg in {"lst", "list", "values"}:
                        s, e = _span(source, node.args[0])
                        out.append(source[:s] + "i" + source[e:])
        return out

    def _append_called_as_attribute(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                seg = ast.get_source_segment(source, node)
                if seg and ".append." in seg:
                    s, e = _span(source, node.func)
                    out.append(source[:s] + source[s:e].replace(".append", ".append(") + ")" + source[e:])
        return out

    def _count_against_input_instead_of_output(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Attribute) and node.left.func.attr == "count":
                    if isinstance(node.left.func.value, ast.Name) and node.left.func.value.id in {"lst", "list", "values"}:
                        v = ast.get_source_segment(source, node.left.args[0]) if node.left.args else None
                        if v:
                            ls, le = _span(source, node.left.func.value)
                            out.append(source[:ls] + "new_lst" + source[le:])
        return out

    def _extend_or_add_singleton_item(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                    a = node.args[0].id
                    if a in {"i", "item", "element", "entry", "value", "ele", "x", "num", "n"}:
                        s, e = _span(source, node.args[0])
                        out.append(source[:s] + "[" + source[s:e] + "]" + source[e:])
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if isinstance(node.right, ast.Name) and node.right.id in {"i", "item", "element", "entry", "value", "ele", "x", "num"}:
                    s, e = _span(source, node.right)
                    out.append(source[:s] + "[" + source[s:e] + "]" + source[e:])
        return out

    def _append_return_value_mistake(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "append":
                s, e = _span(source, node.value)
                out.append(source[:s] + ast.get_source_segment(source, node.value.func.value) + ".append(" + ast.get_source_segment(source, node.value.args[0]) + ")" + source[e:])
        return out

    def _set_or_ordereddict_needs_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"set", "lists"}:
                s, e = _span(source, node.func)
                out.append(source[:s] + "list" + source[e:])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fromkeys":
                parent = ast.get_source_segment(source, node)
                if parent and not parent.strip().startswith("list("):
                    s, e = _span(source, node)
                    out.append(source[:s] + "list(" + parent + ")" + source[e:])
        return out

    def _missing_ordereddict_import(self, source):
        if "OrderedDict.fromkeys" not in source or "from collections import OrderedDict" in source:
            return []
        return ["from collections import OrderedDict\n\n" + source]

    def _return_none_for_empty_list(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
                s, e = _span(source, node.value)
                out.append(source[:s] + "[]" + source[e:])
        return out

    def _wrong_list_element_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"n", "element", "item", "entry", "value", "ele"}:
                if node.id == "n":
                    s, e = _span(source, node)
                    out.append(source[:s] + "i" + source[e:])
                elif node.id in {"element", "entry", "value", "ele"}:
                    s, e = _span(source, node)
                    out.append(source[:s] + "i" + source[e:])
        return out

    def _reverse_return_none(self, source):
        if ".reverse()" in source and "return lst.reverse()" in source:
            return [source.replace("return lst.reverse()", "lst.reverse()\n    return lst")]
        return []

    def _count_based_remove_self(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Attribute) and node.left.func.attr == "count":
                    s, e = _span(source, node)
                    out.append(source[:s] + ast.get_source_segment(source, node.left.func.value) + ".count(" + ast.get_source_segment(source, node.left.args[0]) + ") == 0" + source[e:])
        return out

    def _off_by_one_range_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Add):
                    rhs = node.args[0].right
                    if isinstance(rhs, ast.Constant) and rhs.value == 1:
                        s, e = _span(source, node.args[0])
                        out.append(source[:s] + ast.get_source_segment(source, node.args[0].left) + source[e:])
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                    if node.args[0].id == "l":
                        s, e = _span(source, node.args[0])
                        out.append(source[:s] + "len(lst)" + source[e:])
        return out

    def _strict_comparison_to_self(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Eq) and isinstance(node.right, ast.Name) and node.right.id in {"final", "new_list", "new_lst", "new", "a"}:
                    s, e = _span(source, node)
                    out.append(source[:s] + ast.get_source_segment(source, node.left) + " not in " + ast.get_source_segment(source, node.right) + source[e:])
                if isinstance(node.ops[0], ast.NotEq) and isinstance(node.right, ast.Name) and node.right.id in {"final", "new_list", "new_lst", "new", "a"}:
                    s, e = _span(source, node)
                    out.append(source[:s] + ast.get_source_segment(source, node.left) + " not in " + ast.get_source_segment(source, node.right) + source[e:])
        return out