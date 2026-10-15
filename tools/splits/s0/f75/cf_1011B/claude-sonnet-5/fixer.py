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


def _lt_to_le(source):
    """Relax a strict `<` comparison to `<=` (off-by-one guard)."""
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


def _binary_search_bound_too_small(source):
    """
    A binary-search over the answer bounds `l`/`r` with `r` initialized to a
    too-small constant (e.g. 100, the max package type instead of the max
    possible number of days). Bump the bound up so the search range actually
    covers the real answer.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)):
            continue
        var_name = node.targets[0].id
        val = node.value.value
        if not (1 <= val <= 1000):
            continue

        found_binary_search = False
        for n2 in ast.walk(tree):
            if isinstance(n2, ast.While) and isinstance(n2.test, ast.Compare):
                test = n2.test
                left = test.left
                if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Sub):
                    names = set()
                    if isinstance(left.left, ast.Name):
                        names.add(left.left.id)
                    if isinstance(left.right, ast.Name):
                        names.add(left.right.id)
                    if var_name in names:
                        found_binary_search = True
                        break
        if found_binary_search:
            s, e = _span(source, node.value)
            out.append(source[:s] + "100000" + source[e:])
    return out


def _find_counts_list_var(tree):
    """
    Looks for the common idiom:

        counts = [0] * len(items)
        for i in range(len(items)):
            counts[i] = items[i][1]

    which turns a sorted (key, count) list into a plain list of counts.
    Returns the name of the resulting counts-list variable, or None.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        it = node.iter
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                and it.func.id == 'range' and len(it.args) == 1):
            continue
        inner = it.args[0]
        if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                and inner.func.id == 'len'):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Assign):
            continue
        assign = node.body[0]
        if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Subscript):
            continue
        tgt = assign.targets[0]
        val = assign.value
        if isinstance(tgt.value, ast.Name) and isinstance(val, ast.Subscript) \
           and isinstance(val.value, ast.Subscript):
            return tgt.value.id
    return None


def _find_n_name(tree):
    """Find `n, m = map(int, input().split())` style unpack; return n's name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Tuple):
            elts = node.targets[0].elts
            if len(elts) == 2 and all(isinstance(e, ast.Name) for e in elts):
                val = node.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
                   and val.func.id == 'map':
                    return elts[0].id
    return None


def _greedy_redistribution_replace_with_bruteforce(source):
    """
    Targets submissions that compute the counts-per-type list correctly but
    then try to find the answer via an ad-hoc greedy pair-swapping loop
    (moving one unit of capacity between two buckets while it "helps") instead
    of simply scanning candidate day counts from high to low. Rather than
    untangling that loop, insert a correct brute-force recomputation of the
    final printed variable right before the final `print(...)`, using the
    already-computed counts list and participant count `n`.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    counts_var = _find_counts_list_var(tree)
    if counts_var is None:
        return []

    n_name = _find_n_name(tree)
    if n_name is None:
        return []

    body = tree.body
    if not body:
        return []
    last = body[-1]
    if not (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
            and isinstance(last.value.func, ast.Name)
            and last.value.func.id == 'print'):
        return []
    args = last.value.args
    if len(args) != 1 or not isinstance(args[0], ast.Name):
        return []
    printed_var = args[0].id

    s, _ = _span(source, last)
    indent = ' ' * last.col_offset
    insertion = (
        f"{printed_var} = 0\n"
        f"{indent}for _rep_d in range(100, 0, -1):\n"
        f"{indent}    if sum(_rep_c // _rep_d for _rep_c in {counts_var}) >= {n_name}:\n"
        f"{indent}        {printed_var} = _rep_d\n"
        f"{indent}        break\n"
        f"{indent}"
    )
    return [source[:s] + insertion + source[s:]]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="binary_search_bound_too_small",
                apply=_binary_search_bound_too_small,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="greedy_redistribution_replace_with_bruteforce",
                apply=_greedy_redistribution_replace_with_bruteforce,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]