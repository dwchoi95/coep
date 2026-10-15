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


def _widen_binary_search_bound(source):
    """Binary search over an answer with a too-small hi bound (r = 100)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    assigns = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)):
            assigns[node.targets[0].id] = node

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        if not isinstance(test.ops[0], ast.Gt):
            continue
        left = test.left
        if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Sub)):
            continue
        if not (isinstance(left.left, ast.Name) and isinstance(left.right, ast.Name)):
            continue
        r_name = left.left.id
        if r_name not in assigns:
            continue
        assign_node = assigns[r_name]
        val = assign_node.value.value
        if 1 < val <= 1000:
            new_val = max(val * 100, 100000)
            out.append(_splice(source, assign_node.value, str(new_val)))
    return out


def _fix_greedy_pairwise_swap(source):
    """Replace the pairwise-swap greedy heuristic (for j.../while i<j...) that
    tries to balance participants among food types, with a monotone search
    over the number of days, reusing the already-computed list of per-type
    counts and the participants count found in the source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    body = tree.body

    n_name = None
    for stmt in body:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Tuple)):
            elts = stmt.targets[0].elts
            if elts and isinstance(elts[0], ast.Name):
                val = stmt.value
                if (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                        and val.func.id == 'map'):
                    n_name = elts[0].id
                    break

    if n_name is None:
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Subscript)):
                sub = node.targets[0]
                sl = sub.slice
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    if isinstance(node.value, ast.Name):
                        n_name = node.value.id
                        break

    if n_name is None:
        return []

    target_idx = None
    counts_var = None
    for idx, stmt in enumerate(body):
        if not isinstance(stmt, ast.For):
            continue
        it = stmt.iter
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                and it.func.id == 'range'):
            continue
        if len(it.args) < 2:
            continue
        lo, hi = it.args[0], it.args[1]
        if not (isinstance(lo, ast.Constant) and lo.value == 1):
            continue
        if not (isinstance(hi, ast.Call) and isinstance(hi.func, ast.Name)
                and hi.func.id == 'len' and len(hi.args) == 1
                and isinstance(hi.args[0], ast.Name)):
            continue
        has_while = any(isinstance(n, ast.While) for n in ast.walk(stmt))
        if not has_while:
            continue
        target_idx = idx
        counts_var = hi.args[0].id
        break

    if target_idx is None or counts_var is None:
        return []

    if target_idx == 0:
        return []

    start_s, _ = _span(source, body[target_idx])
    _, end_e = _span(source, body[-1])

    replacement = (
        "__ans = 0\n"
        "for __d in range(1, 100001):\n"
        "    __tot = 0\n"
        f"    for __c in {counts_var}:\n"
        "        __tot += __c // __d\n"
        f"    if __tot >= {n_name}:\n"
        "        __ans = __d\n"
        "    else:\n"
        "        break\n"
        "print(__ans)\n"
    )

    return [source[:start_s] + replacement + source[end_e:]]


def _lt_to_le(source):
    """Relax a strict '<' comparison to '<=' (generic off-by-one slip)."""
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


class Fixer:
    def rules(self):
        return [
            Rule(
                name="widen_binary_search_bound",
                apply=_widen_binary_search_bound,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="fix_greedy_pairwise_swap",
                apply=_fix_greedy_pairwise_swap,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="lt_to_le",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]


from src.core.repair import Rule