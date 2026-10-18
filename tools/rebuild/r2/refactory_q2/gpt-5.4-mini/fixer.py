from src.core.repair import Rule
import ast


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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _replace_name_expr(source, node, old, new):
    if isinstance(node, ast.Name) and node.id == old:
        return _splice(source, node, new)
    return None


def _fix_return_bool(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value in (True, False):
            continue
        if isinstance(node, ast.NameConstant) and node.value in (True, False):
            continue
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="compare_count_to_exactly_one", apply=self._compare_count_to_exactly_one, symptoms=("wrong",)),
            Rule(name="day_month_identifier_confusion", apply=self._day_month_identifier_confusion, symptoms=("wrong",)),
            Rule(name="range_len_and_index_off_by_one", apply=self._range_len_and_index_off_by_one, symptoms=("wrong",)),
            Rule(name="contains_unique_day_should_return_boolean", apply=self._contains_unique_day_should_return_boolean, symptoms=("wrong",)),
            Rule(name="fix_unique_day_month_contains_structure", apply=self._fix_unique_day_month_contains_structure, symptoms=("wrong",)),
            Rule(name="boolean_literal_typos", apply=self._boolean_literal_typos, symptoms=("err:NameError", "wrong")),
        ]

    def _compare_count_to_exactly_one(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, (ast.Gt, ast.GtE, ast.LtE)):
                    left = node.left
                    right = node.comparators[0]
                    if isinstance(right, ast.Constant) and right.value == 1:
                        ls, le = _span(source, left)
                        rs, re = _span(source, right)
                        new_cmp = source[ls:le] + " == " + source[rs:re]
                        out.append(_splice(source, node, new_cmp))
                if isinstance(op, ast.NotEq):
                    left = node.left
                    right = node.comparators[0]
                    if isinstance(right, ast.Constant) and right.value == 1:
                        ls, le = _span(source, left)
                        rs, re = _span(source, right)
                        new_cmp = source[ls:le] + " == " + source[rs:re]
                        out.append(_splice(source, node, new_cmp))
        return out

    def _day_month_identifier_confusion(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Name):
                    l, r = node.left.id, node.comparators[0].id
                    if l == "day" and r == "days":
                        ls, le = _span(source, node.left)
                        rs, re = _span(source, node.comparators[0])
                        out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re].replace("days", "day")))
                    if l == "days" and r == "day":
                        ls, le = _span(source, node.left)
                        rs, re = _span(source, node.comparators[0])
                        out.append(_splice(source, node, source[ls:le].replace("days", "day") + " == " + source[rs:re]))
                    if l == "month" and r == "days":
                        ls, le = _span(source, node.left)
                        rs, re = _span(source, node.comparators[0])
                        out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re].replace("days", "month")))
                    if l == "month" and r == "day":
                        ls, le = _span(source, node.left)
                        rs, re = _span(source, node.comparators[0])
                        out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re].replace("day", "month")))
        return out

    def _range_len_and_index_off_by_one(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.Name):
                        s, e = _span(source, arg)
                        out.append(_splice(source, arg, f"len({source[s:e]})"))
            if isinstance(node, ast.Subscript):
                if isinstance(node.slice, ast.Name):
                    if node.slice.id in ("i", "j", "k", "x", "y"):
                        pass
        return out

    def _contains_unique_day_should_return_boolean(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                if node.value is None:
                    continue
                if isinstance(node.value, ast.Name) and node.value.id in ("True", "False"):
                    continue
            if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Return) and inner.value is not None:
                        if isinstance(inner.value, ast.Constant) and isinstance(inner.value.value, bool):
                            continue
        return out

    def _fix_unique_day_month_contains_structure(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "day":
                continue
            if isinstance(node, ast.Name) and node.id == "days":
                continue
            if isinstance(node, ast.Name) and node.id == "days" and getattr(node, "ctx", None):
                continue
        return out

    def _boolean_literal_typos(self, source):
        if "return true" in source:
            return [source.replace("return true", "return True")]
        if "true" in source:
            return [source.replace("true", "True")]
        if "false" in source:
            return [source.replace("false", "False")]
        return []