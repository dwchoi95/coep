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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _arg_name(func):
    return func.args.args[0].arg if func.args.args else None


def _contains_rule(source):
    tree = _parse(source)
    if tree is None:
        return []

    out = []
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    names = {f.name for f in funcs}
    target_names = {"unique_day", "unique_month", "contains_unique_day"}
    if not target_names.issubset(names):
        return []

    for func in funcs:
        if func.name not in target_names:
            continue
        if not func.body:
            continue

        if func.name == "contains_unique_day":
            for node in ast.walk(func):
                if isinstance(node, ast.If):
                    test = node.test
                    if isinstance(test, ast.Compare) and len(test.ops) == 1:
                        if isinstance(test.ops[0], ast.In) and isinstance(test.left, ast.Name):
                            if isinstance(test.comparators[0], ast.Name):
                                if test.left.id == "month" and test.comparators[0].id != "month":
                                    return []

        if func.name in ("unique_day", "unique_month"):
            arg = _arg_name(func)
            for node in ast.walk(func):
                if isinstance(node, ast.Compare) and len(node.ops) == 1:
                    left = node.left
                    right = node.comparators[0]
                    if isinstance(node.ops[0], ast.In):
                        if isinstance(left, ast.Name) and left.id == arg:
                            s, e = _span(source, node)
                            new = source[s:e].replace(" in ", " == ")
                            out.append(source[:s] + new + source[e:])
                    if isinstance(node.ops[0], ast.Eq):
                        if isinstance(left, ast.Name) and isinstance(right, ast.Subscript):
                            if isinstance(right.slice, ast.Constant):
                                if right.slice.value in (0, 1):
                                    s, e = _span(source, node)
                                    new = source[s:e].replace("==", "in", 1)
                                    out.append(source[:s] + new + source[e:])
                    if isinstance(node.ops[0], ast.LtE):
                        s, e = _span(source, node)
                        new = source[s:e].replace("<=", "==")
                        out.append(source[:s] + new + source[e:])
                    if isinstance(node.ops[0], ast.Gt):
                        s, e = _span(source, node)
                        new = source[s:e].replace(">", "==")
                        out.append(source[:s] + new + source[e:])

            for node in ast.walk(func):
                if isinstance(node, ast.Name) and node.id in {"date", "day", "month"}:
                    if node.id != arg:
                        s, e = _span(source, node)
                        out.append(source[:s] + arg + source[e:])

    return out


def _fix_unique_day_month_misuse(source):
    tree = _parse(source)
    if tree is None:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and len(sub.ops) == 1:
                    if isinstance(sub.ops[0], ast.Eq) and isinstance(sub.left, ast.Subscript):
                        if isinstance(sub.left.slice, ast.Constant) and sub.left.slice.value == 1:
                            s, e = _span(source, sub.left)
                            out.append(source[:s] + source[s:e].replace("[1]", "[0]") + source[e:])
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], ast.Eq):
                    if isinstance(sub.left, ast.Name) and sub.left.id in {"month", "day"}:
                        if isinstance(sub.comparators[0], ast.Subscript):
                            if isinstance(sub.comparators[0].slice, ast.Constant):
                                idx = sub.comparators[0].slice.value
                                if sub.left.id == "month" and idx == 1:
                                    s, e = _span(source, sub.comparators[0])
                                    out.append(source[:s] + source[s:e].replace("[1]", "[0]") + source[e:])
                                if sub.left.id == "day" and idx == 0:
                                    s, e = _span(source, sub.comparators[0])
                                    out.append(source[:s] + source[s:e].replace("[0]", "[1]") + source[e:])
    return out


def _fix_bool_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value in ("true", "false", "True", "False"):
            if node.value == "true":
                s, e = _span(source, node)
                out.append(source[:s] + "True" + source[e:])
            if node.value == "false":
                s, e = _span(source, node)
                out.append(source[:s] + "False" + source[e:])
    return out


def _fix_return_none(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        if func.name == "contains_unique_day":
            if len(func.body) == 1 and isinstance(func.body[0], ast.Return) and func.body[0].value is None:
                s, e = _span(source, func.body[0])
                new = "for birthday in possible_birthdays:\n        if birthday[0] == month:\n            if unique_day(birthday[1], possible_birthdays):\n                return True\n    return False"
                out.append(source[:s] + new + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="compare_day_and_month_by_position",
                apply=_fix_unique_day_month_misuse,
                symptoms=("wrong",),
            ),
            Rule(
                name="replace_membership_with_equality_and_fix_arg_names",
                apply=_contains_rule,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_bool_literal_typos",
                apply=_fix_bool_return,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="replace_bare_return_in_contains_unique_day",
                apply=_fix_return_none,
                symptoms=("wrong",),
            ),
        ]