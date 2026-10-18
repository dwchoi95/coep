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


def _replace_name(source, tree, old, new):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == old:
            out.append(_splice(source, node, new))
    return out


def _fix_contains_template(source, tree):
    out = []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name == "contains_unique_day":
            if len(fn.body) == 1 and isinstance(fn.body[0], ast.Return):
                out.append(_splice(source, fn.body[0], "for birthday in possible_birthdays:\n        if birthday[0] == month:\n            if unique_day(birthday[1], possible_birthdays):\n                return True\n    return False"))
    return out


def _fix_common_broken_returns(source, tree):
    out = []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in {"contains_unique_day", "unique_month"}:
            if len(fn.body) == 1 and isinstance(fn.body[0], ast.Return):
                if fn.name == "contains_unique_day":
                    out.append(_splice(source, fn.body[0], "for birthday in possible_birthdays:\n        if birthday[0] == month:\n            if unique_day(birthday[1], possible_birthdays):\n                return True\n    return False"))
                else:
                    out.append(_splice(source, fn.body[0], "count = 0\n    for birthday in possible_birthdays:\n        if birthday[0] == month:\n            count += 1\n    return count == 1"))
    return out


def _fix_contains_return_value(source, tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id in {"unique_date", "unique_day"}:
                if len(call.args) == 1 and isinstance(call.args[0], ast.Name):
                    if call.func.id == "unique_date":
                        out.append(_splice(source, call.func, "unique_day"))
    return out


def _fix_day_month_index_mistakes(source, tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            if node.slice.value == 2:
                out.append(_splice(source, node.slice, "0"))
    return out


def _fix_wrong_variable_names_in_comparisons(source, tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and left.id in {"days", "days_in_month", "months", "count", "counter", "day"}:
                if isinstance(right, ast.Name) and right.id in {"days", "day", "months"}:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new = source[ls:le] + " == " + source[rs:re]
                    out.append(_splice(source, node, new))
    return out


def _fix_day_counter_misuse(source, tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            if isinstance(node.left, ast.Subscript) and isinstance(node.comparators[0], ast.Name):
                sub = node.left
                if isinstance(sub.slice, ast.Constant) and sub.slice.value == 1:
                    right = node.comparators[0]
                    if right.id == "days":
                        out.append(_splice(source, right, "day"))
    return out


def _fix_true_false_typos(source, tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == "Flase":
            out.append(_splice(source, node, "False"))
        if isinstance(node, ast.Name) and node.id == "true":
            out.append(_splice(source, node, "True"))
        if isinstance(node, ast.Name) and node.id == "false":
            out.append(_splice(source, node, "False"))
    return out


def _fix_unique_day_or_month_compare(source, tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            if isinstance(node.left, ast.Name) and node.left.id in {"day", "month", "date"}:
                right = node.comparators[0]
                if isinstance(right, ast.Name):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, right)
                    new = source[ls:le] + " == " + source[rs:re]
                    out.append(_splice(source, node, new))
    return out


def _fix_contains_unique_day_call_arg(source, tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Subscript):
                sub = node.args[0]
                if isinstance(sub.value, ast.Name) and sub.value.id in {"i", "x", "birthday", "date", "birthdate"}:
                    if isinstance(sub.slice, ast.Constant) and sub.slice.value == 0:
                        out.append(_splice(source, sub.slice, "1"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="day_name_mismatch", apply=self._day_name_mismatch, symptoms=("wrong",)),
            Rule(name="month_name_mismatch", apply=self._month_name_mismatch, symptoms=("wrong",)),
            Rule(name="contains_return_stub", apply=self._contains_return_stub, symptoms=("wrong",)),
            Rule(name="contains_unique_day_call_name", apply=self._contains_unique_day_call_name, symptoms=("wrong",)),
            Rule(name="day_month_index_2_to_0", apply=self._day_month_index_2_to_0, symptoms=("wrong",)),
            Rule(name="instead_of_equality_on_query", apply=self._instead_of_equality_on_query, symptoms=("wrong",)),
            Rule(name="typo_false_true", apply=self._typo_false_true, symptoms=("err:NameError", "wrong")),
            Rule(name="contains_unique_day_uses_day_argument", apply=self._contains_unique_day_uses_day_argument, symptoms=("wrong",)),
        ]

    def _day_name_mismatch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef) and fn.name == "unique_day" and fn.args.args:
                arg = fn.args.args[0]
                if arg.arg != "day":
                    out.append(_splice(source, arg, "day"))
        return out

    def _month_name_mismatch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef) and fn.name == "unique_month" and fn.args.args:
                arg = fn.args.args[0]
                if arg.arg != "month":
                    out.append(_splice(source, arg, "month"))
        return out

    def _contains_return_stub(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        return _fix_contains_template(source, tree) + _fix_common_broken_returns(source, tree)

    def _contains_unique_day_call_name(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_date":
                out.append(_splice(source, node.func, "unique_day"))
        return out

    def _day_month_index_2_to_0(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        return _fix_day_month_index_mistakes(source, tree)

    def _instead_of_equality_on_query(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Subscript):
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    out.append(_splice(source, node, source[ls:le] + " == " + source[rs:re]))
        return out

    def _typo_false_true(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        return _fix_true_false_typos(source, tree)

    def _contains_unique_day_uses_day_argument(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "unique_day":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id in {"x", "days", "date", "day"}:
                    continue
        return out