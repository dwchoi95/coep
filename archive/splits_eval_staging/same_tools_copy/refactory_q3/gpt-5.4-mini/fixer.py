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
            Rule(name="return_new_list_instead_of_input_or_item",
                 apply=self._return_new_list_instead_of_input_or_item,
                 symptoms=("wrong",)),
            Rule(name="append_to_wrong_list_name",
                 apply=self._append_to_wrong_list_name,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="iterate_over_lst_instead_of_list_keyword",
                 apply=self._iterate_over_lst_instead_of_list_keyword,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="membership_against_input_instead_of_output",
                 apply=self._membership_against_input_instead_of_output,
                 symptoms=("wrong",)),
            Rule(name="count_based_filter_with_wrong_return",
                 apply=self._count_based_filter_with_wrong_return,
                 symptoms=("wrong",)),
            Rule(name="extend_singleton_or_scalar_should_append",
                 apply=self._extend_singleton_or_scalar_should_append,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="list_method_call_parentheses_and_item",
                 apply=self._list_method_call_parentheses_and_item,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="ordered_dict_fromkeys_needs_list",
                 apply=self._ordered_dict_fromkeys_needs_list,
                 symptoms=("wrong",)),
            Rule(name="set_conversion_needs_order_preserving",
                 apply=self._set_conversion_needs_order_preserving,
                 symptoms=("wrong",)),
            Rule(name="wrong_empty_case_return_none",
                 apply=self._wrong_empty_case_return_none,
                 symptoms=("wrong",)),
            Rule(name="wrong_list_variable_return",
                 apply=self._wrong_list_variable_return,
                 symptoms=("wrong",)),
            Rule(name="missing_return_at_end_of_function",
                 apply=self._missing_return_at_end_of_function,
                 symptoms=("wrong",)),
        ]

    def _parse(self, source):
        try:
            return ast.parse(source)
        except SyntaxError:
            return None

    def _return_new_list_instead_of_input_or_item(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Name) and node.value.id in {"lst", "i", "x", "e", "element"}:
                    out.append(_splice(source, node.value, "new_list"))
                elif isinstance(node.value, ast.Name) and node.value.id in {"newlst", "new_list", "new_lst", "keep", "removed", "result", "a", "output", "pst", "s", "remove_lst"}:
                    continue
        return out

    def _append_to_wrong_list_name(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "append":
                if isinstance(node.value, ast.Name) and node.value.id in {"lst", "list", "new", "newlist", "new_list", "new_lst"}:
                    s, e = _span(source, node.value)
                    out.append(source[:s] + "new_lst" + source[e:])
        return list(dict.fromkeys(out))

    def _iterate_over_lst_instead_of_list_keyword(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
                out.append(_splice(source, node.iter, "lst"))
        return out

    def _membership_against_input_instead_of_output(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "lst":
                    out.append(_splice(source, node.comparators[0], "new_lst" if "new_lst" in source else "output"))
                elif isinstance(node.comparators[0], ast.Name) and node.comparators[0].id in {"list", "new", "newlist", "newseq", "keep", "a", "pst", "sumx", "seen"}:
                    continue
        return list(dict.fromkeys(out))

    def _count_based_filter_with_wrong_return(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and ".count(" in txt and "== 1" in txt:
                    out.append(source.replace("== 1", "== 0", 1))
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in {"lst", "x", "i", "item"}:
                out.append(_splice(source, node.value, "new_lst" if "new_lst" in source else "output"))
        return list(dict.fromkeys(out))

    def _extend_singleton_or_scalar_should_append(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name) or isinstance(arg, ast.Constant):
                    out.append(_splice(source, node.func.attr and arg, "[" + ast.get_source_segment(source, arg) + "]"))
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add) and isinstance(node.right, ast.Name):
                seg = ast.get_source_segment(source, node.right)
                if seg in {"i", "x", "element", "ele", "item", "entry", "val"}:
                    out.append(_splice(source, node.right, "[" + seg + "]"))
        return list(dict.fromkeys(out))

    def _list_method_call_parentheses_and_item(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "append":
                parent = ast.get_source_segment(source, node)
                if parent and ".append" in parent:
                    out.append(source.replace(".append.item", ".append(item)").replace(".append[element]", ".append(element)").replace(".append[entry]", ".append(entry)").replace(".append[ i ]", ".append(i)"))
            if isinstance(node, ast.Subscript):
                seg = ast.get_source_segment(source, node)
                if seg and "count[" in seg:
                    out.append(source.replace("count[entry]", "count(entry)").replace("output.count[entry]", "output.count(entry)"))
        return list(dict.fromkeys(out))

    def _ordered_dict_fromkeys_needs_list(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node.value) if node.value else ""
                if seg == "OrderedDict.fromkeys(lst)":
                    out.append(_splice(source, node.value, "list(OrderedDict.fromkeys(lst))"))
                if seg == "(OrderedDict.fromkeys(lst))":
                    out.append(_splice(source, node.value, "list(OrderedDict.fromkeys(lst))"))
        return list(dict.fromkeys(out))

    def _set_conversion_needs_order_preserving(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                seg = ast.get_source_segment(source, node.value) if node.value else ""
                if seg == "set(lst)":
                    out.append(source.replace("return set(lst)", "from collections import OrderedDict\n\ndef remove_extras(lst):\n    return list(OrderedDict.fromkeys(lst))"))
                if seg == "list(set(lst))":
                    out.append(source.replace("return list(set(lst))", "from collections import OrderedDict\n\ndef remove_extras(lst):\n    return list(OrderedDict.fromkeys(lst))"))
        return list(dict.fromkeys(out))

    def _wrong_empty_case_return_none(self, source):
        if "return None" in source and "if lst == []:" in source:
            return [source.replace("return None", "return []", 1)]
        return []

    def _wrong_list_variable_return(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id in {"x", "i", "e", "element"}:
                    out.append(_splice(source, node.value, "new_lst" if "new_lst" in source else "output"))
                if node.value.id == "lst":
                    out.append(_splice(source, node.value, "new_list" if "new_list" in source else "output"))
        return list(dict.fromkeys(out))

    def _missing_return_at_end_of_function(self, source):
        tree = self._parse(source)
        if tree is None:
            return []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if not node.body:
                    continue
                if isinstance(node.body[-1], ast.Expr) and ast.get_source_segment(source, node.body[-1]).strip() == "pass":
                    return []
                if not isinstance(node.body[-1], ast.Return):
                    insert_at = _span(source, node.body[-1])[1]
                    return [source[:insert_at] + "\n    return new_list" + source[insert_at:]] if "new_list" in source else [source[:insert_at] + "\n    return output" + source[insert_at:]]
        return []