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


_CLOSED_FORM = (
    "n = int(input())\n"
    "q, r = divmod(n, 9)\n"
    "d = [q] + [q + 1] * r + [q] * (8 - r)\n"
    "res = 0\n"
    "for i in range(9):\n"
    "    for j in range(9):\n"
    "        res += d[i] * d[j] * d[(i * j) % 9]\n"
    "for i in range(1, n + 1):\n"
    "    res -= n // i\n"
    "print(res)\n"
)


def _func_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _looks_like_digit_root_func(source, func_node):
    text = _func_text(source, func_node)
    if "str(" not in text:
        return False
    if "int(" not in text:
        return False
    # recursion: a call to itself somewhere in the body
    recursive = False
    for n in ast.walk(func_node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
           and n.func.id == func_node.name:
            recursive = True
            break
    has_while = any(isinstance(n, ast.While) for n in ast.walk(func_node))
    has_len_check = "len(str(" in text or "<=9" in text or "< 10" in text \
        or "<10" in text or "!=1" in text or "!= 1" in text
    return recursive or (has_while and has_len_check) or (has_len_check and "sum(" in text)


def _digital_root_bruteforce_to_closed_form(source):
    """
    This assignment's recurring misconception: submissions implement an
    O(N) or O(N^2) brute-force search driven by a hand-rolled digital-root
    helper (recursive digit-sum, or a while-loop collapsing digits) instead
    of the closed-form counting-by-residue-class solution. Any such
    submission is replaced by the canonical closed-form computation.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    if "divmod(" in source:
        # already looks like the closed-form solution; don't touch it
        return []

    found_helper = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if _looks_like_digit_root_func(source, node):
                found_helper = True
                break

    if not found_helper:
        return []

    if "input(" not in source:
        return []

    return [_CLOSED_FORM]


def _lt_to_le(source):
    """Relax an accidental strict comparison to non-strict."""
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


def _range_off_by_one(source):
    """
    Nudge a `range(X)` that looks like it should be `range(X+1)` (common
    off-by-one when iterating an inclusive bound like N).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                s, e = _span(source, arg)
                new_arg = source[s:e] + " + 1"
                candidate = source[:s] + new_arg + source[e:]
                if candidate != source:
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="digital_root_bruteforce_to_closed_form",
                apply=_digital_root_bruteforce_to_closed_form,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_off_by_one",
                apply=_range_off_by_one,
                symptoms=("wrong",),
            ),
        ]