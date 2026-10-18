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


def _assigns_name(target, name):
    if isinstance(target, ast.Name) and target.id == name:
        return True
    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) \
       and target.value.id == name:
        return True
    if isinstance(target, (ast.Tuple, ast.List)):
        return any(_assigns_name(e, name) for e in target.elts)
    return False


def _widen_binary_search_bound(source):
    """A binary-search upper bound literal is too small for the search space; widen it."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Gt, ast.GtE))):
            continue
        left = test.left
        if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Sub)):
            continue
        hi, lo = left.left, left.right
        if not (isinstance(hi, ast.Name) and isinstance(lo, ast.Name)):
            continue
        hi_name = hi.id
        for n2 in ast.walk(tree):
            if isinstance(n2, ast.Assign) and len(n2.targets) == 1 \
               and isinstance(n2.targets[0], ast.Name) and n2.targets[0].id == hi_name \
               and isinstance(n2.value, ast.Constant) and isinstance(n2.value.value, int) \
               and not isinstance(n2.value.value, bool):
                if n2.value.value < 100000:
                    out.append(_splice(source, n2.value, "100000"))
    return out


def _fix_greedy_bucket_swap(source):
    """
    Replace the broken 'start with everyone on the biggest pile, then
    pairwise swap one person between buckets while it helps' search with
    the standard 'try every day-count from high to low and check if enough
    participants can be fed' scan, reusing the already-built frequency list
    and participant-count variable.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    if not isinstance(tree, ast.Module):
        return []

    n_name = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Tuple):
            elts = node.targets[0].elts
            if len(elts) >= 2 and all(isinstance(e, ast.Name) for e in elts[:2]):
                if elts[0].id.lower() == 'n' or elts[1].id.lower() == 'm':
                    n_name = elts[0].id
                    break
    if n_name is None:
        return []

    found_swap = False
    freq_name = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Lt)):
            continue
        aug_targets = set()
        div_names = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Subscript) \
               and isinstance(sub.op, (ast.Add, ast.Sub)):
                base = sub.target.value
                if isinstance(base, ast.Name):
                    aug_targets.add(base.id)
            if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.FloorDiv):
                left = sub.left
                if isinstance(left, ast.Subscript) and isinstance(left.value, ast.Name):
                    div_names.add(left.value.id)
        if aug_targets and div_names:
            found_swap = True
            candidates = div_names - aug_targets
            if candidates:
                freq_name = sorted(candidates)[0]
            else:
                freq_name = sorted(div_names)[0]
            break

    if not found_swap or freq_name is None:
        return []

    last_stmt = None
    for node in tree.body:
        hit = False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for t in sub.targets:
                    if _assigns_name(t, freq_name):
                        hit = True
            elif isinstance(sub, ast.AugAssign):
                if _assigns_name(sub.target, freq_name):
                    hit = True
        if hit:
            last_stmt = node

    if last_stmt is None:
        return []

    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    end_off = starts[last_stmt.end_lineno - 1] + last_stmt.end_col_offset

    replacement = (
        "\n"
        "ans = 0\n"
        "for _day_candidate in range(100, 0, -1):\n"
        "    _fed = 0\n"
        f"    for _cnt in {freq_name}:\n"
        "        _fed += _cnt // _day_candidate\n"
        f"    if _fed >= {n_name}:\n"
        "        ans = _day_candidate\n"
        "        break\n"
        "print(ans)\n"
    )

    new_source = source[:end_off] + replacement
    if new_source == source:
        return []
    return [new_source]


def _lt_to_le(source):
    """Relax a strict '<' comparison to '<=' (off-by-one boundary slip)."""
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


def _range_len_minus_one_to_len(source):
    """range(len(x) - 1) likely should be range(len(x)) (off-by-one loop bound)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) \
               and isinstance(arg.right, ast.Constant) and arg.right.value == 1 \
               and isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name) \
               and arg.left.func.id == "len":
                ls, le = _span(source, arg.left)
                candidate = _splice(source, arg, source[ls:le])
                if candidate != source:
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="widen_binary_search_bound",
                apply=_widen_binary_search_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_greedy_bucket_swap_to_divisor_scan",
                apply=_fix_greedy_bucket_swap,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_len_minus_one_off_by_one",
                apply=_range_len_minus_one_to_len,
                symptoms=("wrong", "err:IndexError"),
            ),
        ]