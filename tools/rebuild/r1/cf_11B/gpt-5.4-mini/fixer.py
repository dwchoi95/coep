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


def _replace_node(source, target, new_text):
    try:
        return [_splice(source, target, new_text)]
    except Exception:
        return []


def _abs_input_to_jump_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id != "map":
            continue
        if len(call.args) != 2:
            continue
        if not (isinstance(call.args[0], ast.Name) and call.args[0].id == "int"):
            continue
        if not (
            isinstance(call.args[1], ast.Call)
            and isinstance(call.args[1].func, ast.Name)
            and call.args[1].func.id == "input"
        ):
            continue

        prefix = source[: _span(source, node)[0]]
        suffix = source[_span(source, node)[1] :]
        var = node.targets[0].id
        repl = (
            f"{var} = abs(int(input()))\n"
            f"jumps = 0\n"
            f"pos = 0\n"
            f"while pos < {var} or (pos-{var}) % 2 != 0:\n"
            f"    jumps += 1\n"
            f"    pos += jumps\n"
            f"print(jumps)"
        )
        out.append(prefix + repl + suffix)
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.NotEq)
                and isinstance(test.left, ast.Name)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Name)
            ):
                left = test.left.id
                right = test.comparators[0].id
                body = node.body
                if len(body) >= 2 and isinstance(body[0], ast.AugAssign) and isinstance(body[0].target, ast.Name):
                    if body[0].target.id == "n" and isinstance(body[0].op, ast.Add):
                        s, e = _span(source, node)
                        new = (
                            f"while {left} < {right} or ({left}-{right}) % 2 != 0:\n"
                            f"    {source[_span(source, body[0])[0]:_span(source, body[0])[1]]}\n"
                            f"    {source[_span(source, body[1])[0]:_span(source, body[1])[1]]}"
                        )
                        out.append(source[:s] + new + source[e:])
                        return out

    return []


def _abs_and_monotone_jump_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        if not isinstance(node.test, ast.Compare):
            continue
        cmp = node.test
        if len(cmp.ops) != 1 or not isinstance(cmp.ops[0], ast.NotEq):
            continue
        if not isinstance(cmp.left, ast.Name) or len(cmp.comparators) != 1 or not isinstance(cmp.comparators[0], ast.Name):
            continue
        pos_name = cmp.left.id
        x_name = cmp.comparators[0].id
        if not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.AugAssign) or not isinstance(first.target, ast.Name):
            continue
        if not isinstance(first.op, ast.Add):
            continue
        if not isinstance(first.value, ast.Name):
            continue
        jump_name = first.value.id

        s, e = _span(source, node)
        ind = " " * node.col_offset
        new = (
            f"while {pos_name} < {x_name} or ({pos_name}-{x_name}) % 2 != 0:\n"
            f"{ind}    {jump_name} += 1\n"
            f"{ind}    {pos_name} += {jump_name}"
        )
        out.append(source[:s] + new + source[e:])
        return out
    return []


def _fix_zero_case_abs_input(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "int":
                arg = node.value.args[0] if node.value.args else None
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                    s, e = _span(source, node.value)
                    new = f"abs(int(input()))"
                    out.append(source[:s] + new + source[e:])
                    return out
    return []


def _arith_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            parent_text = source[_span(source, node)[0] : _span(source, node)[1]]
            if "(n*n+n)" in parent_text or "((n*n+n)/2)" in parent_text:
                s, e = _span(source, node)
                out.append(source[:s] + parent_text.replace("/ 2", "// 2").replace("/2", "//2") + source[e:])
                return out
    return []


class Fixer:
    def rules(self):
        return [
            Rule(
                name="input_parsing_and_jump_loop",
                apply=_abs_input_to_jump_loop,
                symptoms=("wrong", "err:TypeError", "err:ValueError"),
            ),
            Rule(
                name="while_not_equal_to_parity_condition",
                apply=_abs_and_monotone_jump_loop,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="wrap_input_with_abs",
                apply=_fix_zero_case_abs_input,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_float_division_in_triangular_number",
                apply=_arith_fix,
                symptoms=("wrong",),
            ),
        ]