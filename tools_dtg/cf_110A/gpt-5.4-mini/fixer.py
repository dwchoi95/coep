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


def _count_lucky_cmp_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Eq) and len(node.comparators) == 1:
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                if right in {"4", "7"} or left in {"4", "7"}:
                    continue
                for repl in (" in {4, 7}", " in [4, 7]", " in (4, 7)"):
                    out.append(_splice(source, node, left + repl))
                    break
    return out


def _fix_digit_type_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Constant) and isinstance(right.value, int):
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, source[ls:le] + " == " + repr(str(right.value))))
            if isinstance(right, ast.Subscript) and isinstance(left, ast.Constant) and isinstance(left.value, int):
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_splice(source, node, repr(str(left.value)) + " == " + source[rs:re]))
    return out


def _fix_count_method_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "count" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and arg.value == "4":
                    out.append(_splice(source, arg, "'7'"))
                elif isinstance(arg, ast.Constant) and arg.value == 4:
                    out.append(_splice(source, arg, "'4'"))
                elif isinstance(arg, ast.Constant) and arg.value == 7:
                    out.append(_splice(source, arg, "'7'"))
    return out


def _fix_modulo_lucky_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Mod):
            pass
    return out


def _fix_len_equals_count(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Call):
                if isinstance(right.func, ast.Name) and right.func.id == "len":
                    out.append(_splice(source, node, source[_span(source, left)[0]:_span(source, left)[1]] + " in {4, 7}"))
    return out


def _fix_bool_or_numeric_confusion(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            values = node.values
            if len(values) == 2:
                a, b = values
                if isinstance(a, ast.Compare) and isinstance(b, ast.Compare):
                    if ast.dump(a.left) == ast.dump(b.left) and len(a.ops) == len(b.ops) == 1:
                        sa, ea = _span(source, a)
                        sb, eb = _span(source, b)
                        if source[sa:ea] != source[sb:eb]:
                            continue
                        out.append(_splice(source, node, source[sa:ea] + " in {4, 7}"))
    return out


def _fix_count_not_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Call):
                if isinstance(right.func, ast.Name) and right.func.id == "len":
                    out.append(_splice(source, node, source[_span(source, left)[0]:_span(source, left)[1]] + " in {4, 7}"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="fix_count_method_target", apply=_fix_count_method_target, symptoms=("wrong",)),
            Rule(name="fix_digit_type_compare", apply=_fix_digit_type_compare, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_len_equals_count", apply=_fix_len_equals_count, symptoms=("wrong",)),
            Rule(name="count_lucky_cmp_fix", apply=_count_lucky_cmp_fix, symptoms=("wrong",)),
            Rule(name="fix_count_not_len", apply=_fix_count_not_len, symptoms=("wrong",)),
            Rule(name="fix_bool_or_numeric_confusion", apply=_fix_bool_or_numeric_confusion, symptoms=("wrong",)),
        ]