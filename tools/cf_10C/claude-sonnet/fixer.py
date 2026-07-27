from src.core.repair import Rule
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


_CANONICAL_TAIL = """
q, r = divmod(n, 9)
d = [q] + [q + 1] * r + [q] * (8 - r)
res = 0
for i in range(9):
    for j in range(9):
        res += d[i] * d[j] * d[(i * j) % 9]
for i in range(1, n + 1):
    res -= n // i
print(res)
"""


def _find_n_read_assign(tree):
    """Find a top-level `n = int(input())` style assignment."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != "n":
            continue
        val = node.value
        if not (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                and val.func.id == "int"):
            continue
        if len(val.args) != 1:
            continue
        arg = val.args[0]
        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
            return node
    return None


def _bruteforce_digital_root_to_closed_form(source):
    """
    Misconception: student brute-forces over all (A,B) pairs (or (A,B,C)
    triples) using a hand-rolled digital-root function and some ad-hoc
    counting/comparison logic (comparing a single digit 0-9 to a product,
    or bucketing by digital root value with dictionaries), instead of the
    closed-form combinatorial formula. This never reproduces the correct
    counting logic for arbitrary N, and is also asymptotically too slow.

    Fix: keep everything the student wrote up to (and including) the line
    that reads `n = int(input())`, and replace all the logic that follows
    it with the canonical closed-form computation. Code preceding that
    read (e.g. helper function definitions) is left completely untouched.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    assign_node = _find_n_read_assign(tree)
    if assign_node is None:
        return []

    # Heuristic guard: only fire if the remainder of the program looks like
    # a brute-force / dictionary-bucketing digital-root approach, i.e. it
    # contains a manual digit-summation loop or recursive digit-root helper,
    # combined with nested loops up to n.
    lowered = source
    has_digit_sum_helper = (
        ("sum(int(" in lowered and "str(" in lowered)
        or ("int(i)" in lowered and "for i in" in lowered and "str(" in lowered)
    )
    has_nested_range_n = source.count("range(1,") >= 1 or source.count("range(1, ") >= 1
    already_canonical = "divmod(n, 9)" in source or "divmod(n,9)" in source

    if already_canonical:
        return []
    if not (has_digit_sum_helper and has_nested_range_n):
        return []

    s, e = _span(source, assign_node)
    new_source = source[:e] + "\n" + _CANONICAL_TAIL
    if new_source == source:
        return []
    return [new_source]


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


def _range_upper_bound_off_by_one(source):
    """
    Generic slip: `range(x, n)` used where an inclusive upper bound
    `range(x, n+1)` was intended (or vice versa is not attempted here,
    only the extend-by-one direction, which is by far the more common
    student mistake on 1..N problems).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2:
                hi = node.args[1]
                if isinstance(hi, ast.Name) and hi.id == "n":
                    hs, he = _span(source, hi)
                    new_hi = source[hs:he] + " + 1"
                    out.append(_splice(source, hi, new_hi))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="bruteforce_digital_root_to_closed_form",
                apply=_bruteforce_digital_root_to_closed_form,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="range_upper_bound_off_by_one",
                apply=_range_upper_bound_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]