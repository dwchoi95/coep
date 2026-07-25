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


def _find_n_var(tree):
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                    and val.func.id == 'int' and val.args
                    and isinstance(val.args[0], ast.Call)
                    and isinstance(val.args[0].func, ast.Name)
                    and val.args[0].func.id == 'input'):
                return node.targets[0].id
    return None


def _fix_digital_root_direct_product_bruteforce(source):
    """
    Misconception: student compares the digital-root chain result directly
    against the literal product i*j (instead of separately enumerating C in
    [1, N] and comparing digital roots), e.g.:
        c = digr(digr(i)*digr(j))
        if c < n+1 and c != i*j:
            d += 2
    Fix: replace the counting block (init + loops + print) with the correct
    closed-form digital-root formula, leaving helper defs untouched.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    n_var = _find_n_var(tree)
    if n_var is None:
        return []

    target_if = None
    counter_var = None

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And)):
            continue
        for cmp_node in test.values:
            if not (isinstance(cmp_node, ast.Compare) and len(cmp_node.ops) == 1
                    and isinstance(cmp_node.ops[0], ast.NotEq)):
                continue
            left, right = cmp_node.left, cmp_node.comparators[0]
            mult_node = None
            if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mult):
                mult_node = left
            elif isinstance(right, ast.BinOp) and isinstance(right.op, ast.Mult):
                mult_node = right
            if mult_node is None:
                continue
            if not (isinstance(mult_node.left, ast.Name) and isinstance(mult_node.right, ast.Name)):
                continue
            cv = None
            for stmt in node.body:
                if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                    cv = stmt.target.id
                elif (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)):
                    tgt = stmt.targets[0].id
                    if (isinstance(stmt.value, ast.BinOp)
                            and isinstance(stmt.value.left, ast.Name)
                            and stmt.value.left.id == tgt):
                        cv = tgt
                if cv:
                    break
            if cv:
                counter_var = cv
                target_if = node
                break
        if target_if:
            break

    if target_if is None or counter_var is None:
        return []

    outer_for = None
    for node in tree.body:
        if isinstance(node, ast.For):
            for sub in ast.walk(node):
                if sub is target_if:
                    outer_for = node
                    break
        if outer_for:
            break
    if outer_for is None:
        return []

    init_node = None
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == counter_var):
            init_node = node

    print_node = None
    for node in tree.body:
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == 'print'):
            args = node.value.args
            if args and isinstance(args[0], ast.Name) and args[0].id == counter_var:
                print_node = node

    if init_node is None or print_node is None:
        return []

    start = _span(source, init_node)[0]
    end = _span(source, print_node)[1]

    replacement = (
        "q, r = divmod({n}, 9)\n"
        "_dr = [q] + [q + 1] * r + [q] * (8 - r)\n"
        "{c} = 0\n"
        "for i in range(9):\n"
        "    for j in range(9):\n"
        "        {c} += _dr[i] * _dr[j] * _dr[(i * j) % 9]\n"
        "for i in range(1, {n} + 1):\n"
        "    {c} -= {n} // i\n"
        "print({c})"
    ).format(n=n_var, c=counter_var)

    return [source[:start] + replacement + source[end:]]


def _fix_digital_root_dict_counting(source):
    """
    Misconception: student builds dictionaries keyed by digital root of the
    product i*j (dct1/dctn style bookkeeping) instead of the correct
    counting formula. Detect the recursive digit-root helper plus at least
    two empty-dict top level assignments, and replace everything after the
    last function definition (the buggy main logic + print) with the
    correct closed-form computation.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    n_var = _find_n_var(tree)
    if n_var is None:
        return []

    dict_assigns = [
        node for node in tree.body
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Dict) and not node.value.keys)
    ]
    if len(dict_assigns) < 2:
        return []

    has_recursive_digit_func = False
    last_func_def = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            last_func_def = node
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                        and sub.func.id == node.name):
                    has_recursive_digit_func = True

    if last_func_def is None or not has_recursive_digit_func:
        return []

    uses_keys_call = False
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'keys'):
            uses_keys_call = True
            break
    if not uses_keys_call:
        return []

    idx = tree.body.index(last_func_def)
    tail_nodes = tree.body[idx + 1:]
    if not tail_nodes:
        return []

    start = _span(source, tail_nodes[0])[0]
    end = _span(source, tail_nodes[-1])[1]

    replacement = (
        "q, r = divmod({n}, 9)\n"
        "_dr = [q] + [q + 1] * r + [q] * (8 - r)\n"
        "_res = 0\n"
        "for i in range(9):\n"
        "    for j in range(9):\n"
        "        _res += _dr[i] * _dr[j] * _dr[(i * j) % 9]\n"
        "for i in range(1, {n} + 1):\n"
        "    _res -= {n} // i\n"
        "print(_res)"
    ).format(n=n_var)

    return [source[:start] + replacement + source[end:]]


def _lt_to_le(source):
    """Relax a strict '<' comparison to '<=' (common off-by-one slip)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Lt)):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


def _range_upper_bound_plus_one(source):
    """Off-by-one: extend a range(..., X) upper bound by one."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'range' and len(node.args) in (1, 2)):
            upper = node.args[-1]
            us, ue = _span(source, upper)
            new_upper = source[us:ue] + " + 1"
            out.append(_splice(source, upper, new_upper))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="digital_root_direct_product_bruteforce",
                apply=_fix_digital_root_direct_product_bruteforce,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="digital_root_dict_counting",
                apply=_fix_digital_root_dict_counting,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_upper_bound_off_by_one",
                apply=_range_upper_bound_plus_one,
                symptoms=("wrong",),
            ),
        ]