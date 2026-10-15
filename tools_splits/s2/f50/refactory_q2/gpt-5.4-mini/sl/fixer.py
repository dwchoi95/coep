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


def _name(node):
    return getattr(node, "id", None)


def _simple_name(node, value):
    return isinstance(node, ast.Name) and node.id == value


def _unique_day_day_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unique_day"]:
        arg = fn.args.args[0].arg if fn.args.args else None
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant) and left.slice.value == 1 and _simple_name(right, "day"):
                    s, e = _span(source, right)
                    out.append(source[:s] + arg + source[e:])
                if isinstance(right, ast.Subscript) and isinstance(right.slice, ast.Constant) and right.slice.value == 1 and _simple_name(left, "day"):
                    s, e = _span(source, left)
                    out.append(source[:s] + arg + source[e:])
                if isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant) and left.slice.value == 1 and _simple_name(right, "date"):
                    s, e = _span(source, right)
                    out.append(source[:s] + arg + source[e:])
                if isinstance(right, ast.Subscript) and isinstance(right.slice, ast.Constant) and right.slice.value == 1 and _simple_name(left, "date"):
                    s, e = _span(source, left)
                    out.append(source[:s] + arg + source[e:])
    return out


def _unique_month_month_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unique_month"]:
        arg = fn.args.args[0].arg if fn.args.args else None
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant) and left.slice.value == 0 and _simple_name(right, "month"):
                    s, e = _span(source, right)
                    out.append(source[:s] + arg + source[e:])
                if isinstance(right, ast.Subscript) and isinstance(right.slice, ast.Constant) and right.slice.value == 0 and _simple_name(left, "month"):
                    s, e = _span(source, left)
                    out.append(source[:s] + arg + source[e:])
    return out


def _contains_unique_day_day_arg(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and _name(node.func) == "unique_day" and len(node.args) >= 1:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Subscript) and isinstance(arg0.slice, ast.Constant) and arg0.slice.value in (0, 1):
                    replacement = source[_span(source, arg0)[0]:_span(source, arg0)[1]]
                    if arg0.slice.value == 0:
                        s, e = _span(source, arg0)
                        out.append(source[:s] + replacement.replace("[0]", "[1]") + source[e:])
                    elif arg0.slice.value == 1:
                        s, e = _span(source, arg0)
                        out.append(source[:s] + replacement.replace("[1]", "[0]") + source[e:])
                if _simple_name(arg0, "i"):
                    s, e = _span(source, arg0)
                    out.append(source[:s] + "i[1]" + source[e:])
    return out


def _fix_count_gt_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left, right = node.left, node.comparators[0]
            s, e = _span(source, node)
            out.append(source[:s] + source[_span(source, left)[0]:_span(source, left)[1]] + " == " + source[_span(source, right)[0]:_span(source, right)[1]] + source[e:])
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
            left, right = node.left, node.comparators[0]
            s, e = _span(source, node)
            out.append(source[:s] + source[_span(source, left)[0]:_span(source, left)[1]] + " == " + source[_span(source, right)[0]:_span(source, right)[1]] + source[e:])
    return out


def _fix_bad_return_true_on_nonunique(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in ("unique_day", "unique_month"):
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
                    s, e = _span(source, node)
                    out.append(source[:s] + source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " == " + source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]] + source[e:])
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                    s, e = _span(source, node)
                    out.append(source[:s] + source[_span(source, node.left)[0]:_span(source, node.left)[1]] + " == " + source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]] + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="unique_day_uses_day_argument", apply=_unique_day_day_var, symptoms=("wrong",)),
            Rule(name="unique_month_uses_month_argument", apply=_unique_month_month_var, symptoms=("wrong",)),
            Rule(name="contains_unique_day_pass_day_not_tuple", apply=_contains_unique_day_day_arg, symptoms=("wrong",)),
            Rule(name="count_comparison_to_equality", apply=_fix_count_gt_one, symptoms=("wrong",)),
            Rule(name="count_comparison_to_equality_alt", apply=_fix_bad_return_true_on_nonunique, symptoms=("wrong",)),
        ]