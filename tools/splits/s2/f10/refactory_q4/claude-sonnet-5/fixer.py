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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _return_undefined_name_use_accumulator(source):
    """A function returns a bare name that was never assigned (e.g. `return sort`
    when the built-up list is actually called `sortt`/`result`/...). Find the
    single list accumulator (`x = []` later `.append`-ed to) and point the
    stray return at it instead."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue

        assigned_names = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned_names.add(t.id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                assigned_names.add(node.target.id)

        param_names = {a.arg for a in func.args.args}

        accumulators = []
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.List)
                    and len(node.value.elts) == 0):
                name = node.targets[0].id
                appended = False
                for n2 in ast.walk(func):
                    if (isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute)
                            and n2.func.attr == 'append'
                            and isinstance(n2.func.value, ast.Name)
                            and n2.func.value.id == name):
                        appended = True
                        break
                if appended:
                    accumulators.append(name)

        if len(accumulators) != 1:
            continue
        acc = accumulators[0]

        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                name = node.value.id
                if name != acc and name not in assigned_names and name not in param_names:
                    out.append(_splice(source, node.value, acc))

    return out


def _empty_tuple_compared_to_list(source):
    """`if lst == ():` never matches when lst is the empty list `[]`, so the
    intended base-case short-circuit silently fails. Replace the empty-tuple
    literal with an empty-list literal."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            candidates = [node.left] + node.comparators
            for c in candidates:
                if isinstance(c, ast.Tuple) and len(c.elts) == 0:
                    out.append(_splice(source, c, "[]"))
    return out


_FLIP = {ast.Lt: (ast.Gt, '>'), ast.Gt: (ast.Lt, '<'),
         ast.LtE: (ast.GtE, '>='), ast.GtE: (ast.LtE, '<=')}


def _swap_sort_comparison_direction(source):
    """A selection-sort style tracker compares `item[idx] < best[idx]` /
    `item[idx] > best[idx]` with the wrong direction, producing ascending
    instead of descending order (or vice versa). Offer the flipped
    comparator as a candidate."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            flip = _FLIP.get(type(op))
            if flip is None:
                continue
            left, right = node.left, node.comparators[0]
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                _, sym = flip
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + f" {sym} " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


def _range_len_off_by_one(source):
    """`range(len(x) - 1)` skips the last index, a classic off-by-one that
    drops the final element from a scan/insertion loop. Offer the version
    without the stray `- 1`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'range' and len(node.args) == 1):
            arg = node.args[0]
            if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
                    and isinstance(arg.right, ast.Constant) and arg.right.value == 1):
                inner = arg.left
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == 'len':
                    s, e = _span(source, inner)
                    out.append(_splice(source, arg, source[s:e]))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="return_undefined_name_use_accumulator",
                apply=_return_undefined_name_use_accumulator,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="empty_tuple_compared_to_list",
                apply=_empty_tuple_compared_to_list,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="swap_sort_comparison_direction",
                apply=_swap_sort_comparison_direction,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_len_off_by_one",
                apply=_range_len_off_by_one,
                symptoms=("wrong", "err:IndexError"),
            ),
        ]