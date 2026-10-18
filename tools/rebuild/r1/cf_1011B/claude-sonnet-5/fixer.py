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


def _widen_binary_search_bound(source):
    """
    Binary searches of the shape `while r - l > 1` need a sentinel upper
    bound `r` that is provably larger than any achievable answer. Several
    submissions set the initial r to a small constant (e.g. 100), which is
    too tight when the true optimum can equal that bound exactly. Widen it.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    assigns = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)
                and not isinstance(node.value.value, bool)):
            assigns.append((node.targets[0].id, node))

    bound_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            test = node.test
            if (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Gt)):
                left = test.left
                if (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Sub)
                        and isinstance(left.left, ast.Name)
                        and isinstance(left.right, ast.Name)):
                    bound_vars.add(left.left.id)

    out = []
    for var, node in assigns:
        if var in bound_vars and 0 < node.value.value <= 1000:
            out.append(_splice(source, node.value, "100000"))
    return out


def _fix_greedy_swap_allocation(source):
    """
    A recurring misconception: instead of searching for the largest k such
    that sum(count_i // k) >= n, submissions build a per-type count list and
    then try to *greedily rebalance* a per-type allocation array by swapping
    single units between types, tracking a running `days = counts[0] // alloc[0]`
    style value. This local hill-climb is not optimal. The structural
    fingerprint is an assignment `D = COUNTS[0] // ALLOC[0]` (a floor division
    of two zero-indexed subscripts) sitting among top-level statements right
    before the broken allocation loop. Replace that statement through the end
    of the module with the correct linear scan over possible day counts,
    reusing the already-computed per-type counts list and the number of
    participants.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    n_name = None
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Tuple)):
            elts = node.targets[0].elts
            if (len(elts) == 2 and all(isinstance(e, ast.Name) for e in elts)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "map"):
                n_name = elts[0].id
                break
    if n_name is None:
        return []

    target_idx = None
    counts_name = None
    for i, node in enumerate(tree.body):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.BinOp)
                and isinstance(node.value.op, ast.FloorDiv)):
            left, right = node.value.left, node.value.right
            if (isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript)
                    and isinstance(left.value, ast.Name)
                    and isinstance(right.value, ast.Name)):
                target_idx = i
                counts_name = left.value.id
                break
    if target_idx is None:
        return []

    start_node = tree.body[target_idx]
    end_node = tree.body[-1]
    if start_node is end_node:
        return []

    s, _ = _span(source, start_node)
    _, e = _span(source, end_node)

    replacement = (
        "__ans = 0\n"
        "for __k in range(1, 101):\n"
        "    __tot = 0\n"
        f"    for __v in {counts_name}:\n"
        "        __tot += __v // __k\n"
        f"    if __tot >= {n_name}:\n"
        "        __ans = __k\n"
        "print(__ans)\n"
    )
    return [source[:s] + replacement + source[e:]]


def _lt_to_le(source):
    """Relax a strict `<` comparison to `<=` (classic off-by-one slip)."""
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


def _flip_true_false_return(source):
    """Swap a function's lone `return True` / `return False` bodies."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Return) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, bool)):
            new_val = "False" if node.value.value else "True"
            out.append(_splice(source, node.value, new_val))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="widen_binary_search_sentinel_bound",
                apply=_widen_binary_search_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="greedy_swap_allocation_to_linear_scan",
                apply=_fix_greedy_swap_allocation,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="flipped_bool_return",
                apply=_flip_true_false_return,
                symptoms=("wrong",),
            ),
        ]