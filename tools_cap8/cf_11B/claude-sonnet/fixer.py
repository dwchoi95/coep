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


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _is_input_int_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "int"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Call)
        and isinstance(node.args[0].func, ast.Name)
        and node.args[0].func.id == "input"
    )


def _wrap_input_abs(source):
    """Wrap a bare int(input()) call with abs(), fixing missing sign handling."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)

    matches = []
    for node in ast.walk(tree):
        if _is_input_int_call(node):
            parent = getattr(node, "parent", None)
            if (
                isinstance(parent, ast.Call)
                and isinstance(parent.func, ast.Name)
                and parent.func.id == "abs"
            ):
                continue
            matches.append(node)

    if not matches:
        return []

    matches.sort(key=lambda n: n.col_offset if False else _span(source, n)[0], reverse=True)

    new_source = source
    for node in matches:
        s, e = _span(new_source, node)
        text = new_source[s:e]
        new_source = new_source[:s] + "abs(" + text + ")" + new_source[e:]

    if new_source == source:
        return []
    return [new_source]


def _add_parity_check_while(source):
    """Add a parity disjunct to a bare `while a < b` / `while a > b` loop guard."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        op = test.ops[0]
        if not isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
            continue

        left = test.left
        right = test.comparators[0]
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        left_src = source[ls:le]
        right_src = source[rs:re_]
        orig_test_s, orig_test_e = _span(source, test)
        orig_test_src = source[orig_test_s:orig_test_e]

        new_test = (
            "(" + orig_test_src + ") or ((" + left_src + "-" + right_src + ")%2 != 0)"
        )
        candidate = _splice(source, test, new_test)
        if candidate != source:
            out.append(candidate)
    return out


def _find_print_add_name(stmts):
    for stmt in stmts:
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == "print"
            and stmt.value.args
        ):
            arg = stmt.value.args[0]
            if (
                isinstance(arg, ast.BinOp)
                and isinstance(arg.op, ast.Add)
                and isinstance(arg.left, ast.Name)
            ):
                return arg.left.id
    return None


def _fix_overshoot_parity_if(source):
    """Fix the 'if pos overshoots target: print(count+1)' misconception.

    Adds the missing parity handling instead of unconditionally assuming
    exactly one extra jump is needed.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)
                and isinstance(test.left, ast.Name)
                and isinstance(test.comparators[0], ast.Name)):
            continue

        s_name = _find_print_add_name(node.body)
        if s_name is None:
            continue

        left_name = test.left.id
        right_name = test.comparators[0].id

        indent = " " * node.col_offset
        new_code = (
            "if {L}>{R}:\n"
            "{I}    if (({L}-{R})%2==0):\n"
            "{I}        print({S})\n"
            "{I}    else:\n"
            "{I}        if (({L}+{S}+1-{R})%2==0):\n"
            "{I}            print({S}+1)\n"
            "{I}        else:\n"
            "{I}            print({S}+2)\n"
            "{I}    break"
        ).format(L=left_name, R=right_name, S=s_name, I=indent)

        candidate = _splice(source, node, new_code)
        if candidate != source:
            out.append(candidate)
    return out


def _lt_to_le(source):
    """Generic slip: a strict `<` comparison should have been `<=`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            candidate = _splice(source, node, new_cmp)
            if candidate != source:
                out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="wrap_input_abs",
                apply=_wrap_input_abs,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="add_parity_check_while",
                apply=_add_parity_check_while,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_overshoot_parity_if",
                apply=_fix_overshoot_parity_if,
                symptoms=("wrong",),
            ),
            Rule(
                name="lt_to_le_slip",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]