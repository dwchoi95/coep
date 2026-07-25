import ast
from src.core.repair import Rule


def _span(source, node):
    """(start, end) char offsets of node in source."""
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


def _fix_missing_return_false_unique_month(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month" and node.body:
            last = node.body[-1]
            if isinstance(last, ast.If) and last.orelse == []:
                if len(last.body) == 1 and isinstance(last.body[0], ast.Return):
                    # Insert explicit "return False" after the last if in the function.
                    insert_pos = _span(source, last)[1]
                    out.append(source[:insert_pos] + "\n    return False" + source[insert_pos:])
    return out


def _fix_unique_day_name_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_day":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], ast.Eq):
                    left = sub.left
                    right = sub.comparators[0]
                    if isinstance(right, ast.Name) and right.id == "day":
                        rs, re_ = _span(source, right)
                        out.append(source[:rs] + "date" + source[re_:])
    return out


def _fix_unique_month_return_false(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    if len(sub.body) == 1 and isinstance(sub.body[0], ast.Return) and sub.orelse == []:
                        insert_pos = _span(source, sub)[1]
                        out.append(source[:insert_pos] + "\n    return False" + source[insert_pos:])
                        break
    return out


def _fix_unique_day_name_mismatch_general(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_day":
            arg0 = node.args.args[0].arg if node.args.args else None
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], ast.Eq):
                    right = sub.comparators[0]
                    if isinstance(right, ast.Name) and arg0 and right.id != arg0:
                        rs, re_ = _span(source, right)
                        out.append(source[:rs] + arg0 + source[re_:])
                        return out
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="unique_day_uses_wrong_parameter_name",
                apply=_fix_unique_day_name_mismatch_general,
                symptoms=("wrong",),
            ),
            Rule(
                name="unique_month_needs_explicit_false_return",
                apply=_fix_unique_month_return_false,
                symptoms=("wrong",),
            ),
            Rule(
                name="unique_month_missing_final_false",
                apply=_fix_missing_return_false_unique_month,
                symptoms=("wrong",),
            ),
            Rule(
                name="unique_day_day_parameter_mismatch",
                apply=_fix_unique_day_name_mismatch,
                symptoms=("wrong",),
            ),
        ]