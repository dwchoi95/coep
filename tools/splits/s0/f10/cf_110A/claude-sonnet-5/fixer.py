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


def _fix_int_digit_compare(source):
    """Comparing a string subscript (e.g. n[i]) to an int literal 4/7
    instead of the string "4"/"7"."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and \
           isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            left, right = node.left, node.comparators[0]
            target = None
            if isinstance(right, ast.Constant) and isinstance(right.value, int) \
               and not isinstance(right.value, bool) and right.value in (4, 7) \
               and isinstance(left, ast.Subscript):
                target = right
            elif isinstance(left, ast.Constant) and isinstance(left.value, int) \
                 and not isinstance(left.value, bool) and left.value in (4, 7) \
                 and isinstance(right, ast.Subscript):
                target = left
            if target is not None:
                new_text = '"%d"' % target.value
                candidate = _splice(source, target, new_text)
                if candidate != source and candidate not in out:
                    out.append(candidate)
    return out


def _fix_range_off_by_one(source):
    """range(X - 1) / range(0, X - 1) that skips the last character/index
    of the sequence being iterated."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
           node.func.id == "range":
            for i, arg in enumerate(node.args):
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and \
                   isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                    new_args_src = []
                    for j, a in enumerate(node.args):
                        if j == i:
                            ls, le = _span(source, arg.left)
                            new_args_src.append(source[ls:le])
                        else:
                            s2, e2 = _span(source, a)
                            new_args_src.append(source[s2:e2])
                    new_call = "range(" + ", ".join(new_args_src) + ")"
                    candidate = _splice(source, node, new_call)
                    if candidate != source and candidate not in out:
                        out.append(candidate)
    return out


def _fix_wrong_count_disjuncts(source):
    """Dropping nonsensical disjuncts like `count4 == 4` or `count7 == 7`
    (comparing a per-digit counter to the digit's own value) from an
    `or`-chain that otherwise correctly checks the total count."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            bad_idx = []
            for idx, val in enumerate(node.values):
                if isinstance(val, ast.Compare) and len(val.ops) == 1 and \
                   isinstance(val.ops[0], ast.Eq):
                    left, right = val.left, val.comparators[0]
                    if isinstance(left, ast.Name) and isinstance(right, ast.Constant) \
                       and isinstance(right.value, int) and not isinstance(right.value, bool) \
                       and right.value in (4, 7) and str(right.value) in left.id:
                        bad_idx.append(idx)
            if bad_idx and len(bad_idx) < len(node.values):
                keep = [v for i2, v in enumerate(node.values) if i2 not in bad_idx]
                if not keep:
                    continue
                parts = []
                for v in keep:
                    vs, ve = _span(source, v)
                    parts.append(source[vs:ve])
                new_text = " or ".join(parts)
                candidate = _splice(source, node, new_text)
                if candidate != source and candidate not in out:
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="str_digit_compared_to_int_literal",
                apply=_fix_int_digit_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="off_by_one_range_bound",
                apply=_fix_range_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="per_digit_count_compared_to_own_digit",
                apply=_fix_wrong_count_disjuncts,
                symptoms=("wrong",),
            ),
        ]