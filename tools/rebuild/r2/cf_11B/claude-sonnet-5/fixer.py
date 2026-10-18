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


def _is_input_int_call(call):
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "int"
        and len(call.args) == 1
        and isinstance(call.args[0], ast.Call)
        and isinstance(call.args[0].func, ast.Name)
        and call.args[0].func.id == "input"
    )


def _wrap_int_input_abs(source):
    """x = int(input())  ->  x = abs(int(input()))"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if _is_input_int_call(node.value):
                s, e = _span(source, node.value)
                new_text = "abs(" + source[s:e] + ")"
                out.append(_splice(source, node.value, new_text))
    return out


def _find_x_var(tree):
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            val = node.value
            inner = val
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "abs"
                and len(inner.args) == 1
            ):
                inner = inner.args[0]
            if _is_input_int_call(inner):
                return node.targets[0].id
    return None


def _fix_sign_sim_loop(source):
    """Replace a 'greedy sign choice' simulation loop (while pos != x: ...
    add/subtract counter based on comparisons) with the correct
    pos < x or parity-mismatch loop, keeping the original variable names."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    x_var = _find_x_var(tree)
    if not x_var:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.NotEq)
        ):
            continue
        left, right = test.left, test.comparators[0]
        if not (isinstance(left, ast.Name) and isinstance(right, ast.Name)):
            continue
        names = [left.id, right.id]
        if x_var not in names:
            continue
        pos_var = names[0] if names[1] == x_var else names[1]
        if pos_var == x_var:
            continue

        counter_var = None
        for n2 in ast.walk(node):
            if (
                isinstance(n2, ast.AugAssign)
                and isinstance(n2.op, ast.Add)
                and isinstance(n2.target, ast.Name)
                and isinstance(n2.value, ast.Constant)
                and n2.value.value == 1
            ):
                counter_var = n2.target.id
                break
        if counter_var is None:
            continue

        indent = " " * node.col_offset
        body_indent = indent + "    "
        new_text = (
            f"while {pos_var} < {x_var} or ({pos_var}-{x_var}) % 2 != 0:\n"
            f"{body_indent}{counter_var} += 1\n"
            f"{body_indent}{pos_var} += {counter_var}"
        )
        out.append(_splice(source, node, new_text))
    return out


def _is_map_input_int(call):
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "map"
        and len(call.args) == 2
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "int"
        and isinstance(call.args[1], ast.Call)
        and isinstance(call.args[1].func, ast.Name)
        and call.args[1].func.id == "input"
    )


def _fix_map_noop(source):
    """x = map(int, input()); print(x) -> read, compute jumps, print jumps."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    assign_node = None
    xvar = None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and _is_map_input_int(node.value)
        ):
            assign_node = node
            xvar = node.targets[0].id
            break
    if assign_node is None:
        return []

    print_node = None
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if (
                isinstance(call.func, ast.Name)
                and call.func.id == "print"
                and len(call.args) == 1
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id == xvar
            ):
                print_node = node
                break
    if print_node is None:
        return []

    indent = " " * print_node.col_offset
    body_indent = indent + "    "
    new_print_text = (
        "jumps = 0\n"
        f"{indent}pos = 0\n"
        f"{indent}while pos < {xvar} or (pos-{xvar}) % 2 != 0:\n"
        f"{body_indent}jumps += 1\n"
        f"{body_indent}pos += jumps\n"
        f"{indent}print(jumps)"
    )

    new_source = _splice(source, print_node, new_print_text)

    s1, e1 = _span(source, assign_node.value)
    new_source = new_source[:s1] + "abs(int(input()))" + new_source[e1:]

    return [new_source]


def _match_triangular(node):
    """Matches the shape (v*v+v)/2 for some single variable v."""
    try:
        if not (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and isinstance(node.right, ast.Constant)
            and node.right.value == 2
        ):
            return False
        add = node.left
        if not (isinstance(add, ast.BinOp) and isinstance(add.op, ast.Add)):
            return False
        mult = add.left
        tail = add.right
        if not (isinstance(mult, ast.BinOp) and isinstance(mult.op, ast.Mult)):
            return False
        a, b = mult.left, mult.right
        if not (isinstance(a, ast.Name) and isinstance(b, ast.Name) and isinstance(tail, ast.Name)):
            return False
        return a.id == b.id == tail.id
    except Exception:
        return False


def _fix_triangular_search(source):
    """Replace a 'while True' triangular-number search (with sign-fixing
    min() guesses) by the correct pos/jumps parity loop."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for wnode in ast.walk(tree):
        if not isinstance(wnode, ast.While):
            continue
        test = wnode.test
        if not (isinstance(test, ast.Constant) and test.value is True):
            continue

        xvar = None
        for cnode in ast.walk(wnode):
            if isinstance(cnode, ast.Compare):
                sides = [cnode.left] + list(cnode.comparators)
                for side in sides:
                    if _match_triangular(side):
                        for other in sides:
                            if other is not side and isinstance(other, ast.Name):
                                xvar = other.id
                                break
                    if xvar:
                        break
            if xvar:
                break
        if xvar is None:
            continue

        indent = " " * wnode.col_offset
        body_indent = indent + "    "
        new_text = (
            "jumps = 0\n"
            f"{indent}pos = 0\n"
            f"{indent}while pos < {xvar} or (pos-{xvar}) % 2 != 0:\n"
            f"{body_indent}jumps += 1\n"
            f"{body_indent}pos += jumps\n"
            f"{indent}print(jumps)"
        )
        out.append(_splice(source, wnode, new_text))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="wrap_input_int_with_abs",
                apply=_wrap_int_input_abs,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_sign_choice_simulation_loop",
                apply=_fix_sign_sim_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_map_input_noop",
                apply=_fix_map_noop,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_triangular_number_search",
                apply=_fix_triangular_search,
                symptoms=("wrong",),
            ),
        ]