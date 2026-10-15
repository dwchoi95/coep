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


def _fix_lucky_digit_quotes(source):
    """Quote bare digit comparisons in lucky-digit checks."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Constant) and isinstance(right.value, int) and right.value in (4, 7):
                ls, le = _span(source, right)
                out.append(_splice(source, right, repr(str(right.value))))
            elif isinstance(right, ast.Subscript) and isinstance(left, ast.Constant) and isinstance(left.value, int) and left.value in (4, 7):
                ls, le = _span(source, left)
                out.append(_splice(source, left, repr(str(left.value))))
    return out


def _count_equals_to_lucky_count(source):
    """Compare the lucky-digit count to 4/7 as a number of digits rather than checking if it is lucky."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 3:
            pass
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(right, ast.Constant) and isinstance(right.value, int) and right.value in (4, 7):
                # only if left looks like a count variable/expression over lucky digits
                if isinstance(left, ast.Name) or isinstance(left, ast.BinOp) or isinstance(left, ast.Call):
                    ls, le = _span(source, right)
                    out.append(_splice(source, right, repr("47" if right.value == 4 else "47")))
            elif isinstance(left, ast.Constant) and isinstance(left.value, int) and left.value in (4, 7):
                if isinstance(right, ast.Name) or isinstance(right, ast.BinOp) or isinstance(right, ast.Call):
                    ls, le = _span(source, left)
                    out.append(_splice(source, left, repr("47" if left.value == 4 else "47")))
    return out


def _range_off_by_one(source):
    """Fix loops that stop one element early with range(len(x)-1) / range(0, s-1)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) in (1, 2):
            text = ast.get_source_segment(source, node)
            if text is None:
                continue
            if "-1" in text.replace(" ", ""):
                if len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                        if isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                            rs, re = _span(source, arg.right)
                            out.append(_splice(source, arg.right, "0"))
                elif len(node.args) == 2:
                    stop = node.args[1]
                    if isinstance(stop, ast.BinOp) and isinstance(stop.op, ast.Sub):
                        if isinstance(stop.right, ast.Constant) and stop.right.value == 1:
                            rs, re = _span(source, stop.right)
                            out.append(_splice(source, stop.right, "0"))
    return out


def _int_input_to_str_input(source):
    """Undo int(input()) when the program indexes characters of the input."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "int" and len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                    assigns = node.targets
                    if len(assigns) == 1 and isinstance(assigns[0], ast.Name):
                        name = assigns[0].id
                        if any(isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == name for n in ast.walk(tree)):
                            s, e = _span(source, node.value)
                            out.append(_splice(source, node.value, "input()"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="quote_bare_lucky_digits",
                apply=_fix_lucky_digit_quotes,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="count_equals_should_not_check_lucky_literal",
                apply=_count_equals_to_lucky_count,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_off_by_one",
                apply=_range_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="int_input_to_string_input_for_digit_indexing",
                apply=_int_input_to_str_input,
                symptoms=("wrong", "err:TypeError"),
            ),
        ]