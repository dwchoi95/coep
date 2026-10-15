import ast


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


def _apply_edits(source, edits):
    """edits: list of (start, end, replacement). Applies right-to-left so
    earlier offsets stay valid."""
    edits = sorted(edits, key=lambda t: t[0], reverse=True)
    out = source
    for s, e, rep in edits:
        out = out[:s] + rep + out[e:]
    return out


def _find_int_input_assign(tree):
    """Find `NAME = int(input())` (possibly already abs-wrapped elsewhere)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
               and val.func.id == 'int' and len(val.args) == 1:
                arg = val.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) \
                   and arg.func.id == 'input':
                    return node
    return None


def _walk_sim_wrong_direction(source):
    """
    Fixes the class of "simulated walk" solutions that never used abs(x)
    and whose greedy step-direction logic doesn't match the correct
    parity/lower-bound stopping condition. Detected shape:

        X = int(input())
        ...
        while POS != X:
            COUNTER += 1
            <arbitrary branching updating POS by +/- COUNTER>

    Rewritten to the canonical stopping rule, keeping the student's own
    variable names so the rest of the file (e.g. the trailing print) still
    works unmodified.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    assign_node = _find_int_input_assign(tree)
    if assign_node is None:
        return []
    x_name = assign_node.targets[0].id

    already_abs = isinstance(assign_node.value, ast.Call) \
        and isinstance(assign_node.value.func, ast.Name) \
        and assign_node.value.func.id == 'abs'

    target_while = None
    pos_name = None
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 \
               and isinstance(test.ops[0], ast.NotEq):
                left, right = test.left, test.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                    names = [left.id, right.id]
                    if x_name in names and names[0] != names[1]:
                        pos_name = names[0] if names[1] == x_name else names[1]
                        target_while = node
                        break
    if target_while is None or not target_while.body:
        return []

    counter_name = None
    for sub in ast.walk(target_while):
        if isinstance(sub, ast.AugAssign) and isinstance(sub.op, ast.Add) \
           and isinstance(sub.target, ast.Name) \
           and isinstance(sub.value, ast.Constant) and sub.value.value == 1:
            counter_name = sub.target.id
            break
    if counter_name is None:
        return []

    indent = ' ' * target_while.body[0].col_offset

    edits = []

    body_s, _ = _span(source, target_while.body[0])
    _, body_e = _span(source, target_while.body[-1])
    new_body = f"{counter_name} += 1\n{indent}{pos_name} += {counter_name}"
    edits.append((body_s, body_e, new_body))

    test_s, test_e = _span(source, target_while.test)
    new_test = f"{pos_name} < {x_name} or ({pos_name}-{x_name}) % 2 != 0"
    edits.append((test_s, test_e, new_test))

    if not already_abs:
        vs, ve = _span(source, assign_node.value)
        edits.append((vs, ve, f"abs({source[vs:ve]})"))

    return [_apply_edits(source, edits)]


def _is_triangular_formula(node):
    """Matches (V*V+V)/2 shaped expressions used by formula-based attempts."""
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
        return False
    left = node.left
    if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add)):
        return False
    inner = left.left
    if not (isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Mult)):
        return False
    return isinstance(inner.left, ast.Name) and isinstance(inner.right, ast.Name) \
        and inner.left.id == inner.right.id


def _formula_based_fix(source):
    """
    Fixes solutions that abandon simulation entirely for a triangular-number
    formula ((n*n+n)/2) with ad-hoc branch corrections. Rather than trying to
    patch the broken arithmetic, replaces just the enclosing `while True:`
    search loop with the canonical simulation, leaving the original input
    read untouched.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    assign_node = _find_int_input_assign(tree)
    if assign_node is None:
        return []
    x_name = assign_node.targets[0].id

    target_while = None
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            t = node.test
            is_true = (isinstance(t, ast.Constant) and t.value is True) or \
                      (isinstance(t, ast.Name) and t.id == 'True')
            if not is_true:
                continue
            for sub in ast.walk(node):
                if _is_triangular_formula(sub):
                    target_while = node
                    break
            if target_while is not None:
                break
    if target_while is None:
        return []

    indent = ' ' * target_while.col_offset
    new_code = (
        f"jumps = 0\n"
        f"{indent}pos = 0\n"
        f"{indent}while pos < abs({x_name}) or (pos-abs({x_name})) % 2 != 0:\n"
        f"{indent}    jumps += 1\n"
        f"{indent}    pos += jumps\n"
        f"{indent}print(jumps)"
    )
    return [_splice(source, target_while, new_code)]


def _map_input_stub_fix(source):
    """
    Fixes the "reads input with map() and just prints it back" misconception
    (student never implemented the jump-counting algorithm at all). Only
    fires when there is no loop anywhere in the file, to keep it scoped to
    genuine stubs rather than partially-correct attempts.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    if any(isinstance(n, (ast.While, ast.For)) for n in ast.walk(tree)):
        return []

    target_assign = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
               and val.func.id == 'map' and len(val.args) == 2:
                a0, a1 = val.args
                if isinstance(a0, ast.Name) and a0.id == 'int' \
                   and isinstance(a1, ast.Call) and isinstance(a1.func, ast.Name) \
                   and a1.func.id == 'input':
                    target_assign = node
                    break
    if target_assign is None:
        return []
    x_name = target_assign.targets[0].id

    print_call = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'print' and len(node.args) == 1 \
           and isinstance(node.args[0], ast.Name) and node.args[0].id == x_name:
            print_call = node
            break
    if print_call is None:
        return []

    a_s, a_e = _span(source, target_assign)
    new_assign_code = (
        f"{x_name} = abs(int(input()))\n"
        f"jumps = 0\n"
        f"pos = 0\n"
        f"while pos < {x_name} or (pos-{x_name}) % 2 != 0:\n"
        f"    jumps += 1\n"
        f"    pos += jumps"
    )

    arg_node = print_call.args[0]
    p_s, p_e = _span(source, arg_node)

    edits = [(a_s, a_e, new_assign_code), (p_s, p_e, 'jumps')]
    return [_apply_edits(source, edits)]


def _lt_to_le(source):
    """Relax a strict `<` comparison to `<=` (generic off-by-one slip)."""
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
            out.append(_splice(source, node, new_cmp))
    return out


def _gt_to_ge(source):
    """Relax a strict `>` comparison to `>=` (generic off-by-one slip)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Gt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " >= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="walk_sim_wrong_direction",
                apply=_walk_sim_wrong_direction,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="formula_based_triangular_fix",
                apply=_formula_based_fix,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="map_input_stub_fix",
                apply=_map_input_stub_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_should_be_gte",
                apply=_gt_to_ge,
                symptoms=("wrong",),
            ),
        ]


from src.core.repair import Rule