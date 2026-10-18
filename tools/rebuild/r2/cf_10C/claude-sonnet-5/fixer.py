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


_CANONICAL = (
    "q, r = divmod(n, 9)\n"
    "__d = [q] + [q + 1] * r + [q] * (8 - r)\n"
    "__res = 0\n"
    "for __i in range(9):\n"
    "    for __j in range(9):\n"
    "        __res += __d[__i] * __d[__j] * __d[(__i * __j) % 9]\n"
    "for __k in range(1, n + 1):\n"
    "    __res -= n // __k\n"
    "print(__res)\n"
)


def _is_digit_root_func(source, fn):
    """Detects a helper function that computes a digit/digital root via
    recursion or a while-loop on the string form of the number -- the
    hallmark of the 'brute force digital root check' misconception."""
    if not isinstance(fn, ast.FunctionDef):
        return False
    s, e = _span(source, fn)
    text = source[s:e]
    if 'str(' not in text or 'int(' not in text:
        return False
    calls_self = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name
        for n in ast.walk(fn)
    )
    has_while = any(isinstance(n, ast.While) for n in ast.walk(fn))
    return calls_self or has_while


def _find_n_assignment(stmt):
    """Matches `NAME = int(input(...))` style statements, returns NAME."""
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
       and isinstance(stmt.targets[0], ast.Name):
        val = stmt.value
        if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == 'int':
            if len(val.args) == 1 and isinstance(val.args[0], ast.Call) \
               and isinstance(val.args[0].func, ast.Name) and val.args[0].func.id == 'input':
                return stmt.targets[0].id
    return None


def _digital_root_bruteforce_rule(source):
    """The class misconception: a nested O(N^2) loop (or direct recursive
    digit-root computation) is used to simulate Billy's check instead of
    the closed-form digit-root-bucket counting formula.  We keep whatever
    digit-root helper function(s) the student wrote (dead code afterwards)
    and the original input-reading statement (if any), and replace only
    the remaining top-level computation/printing statements with the
    correct closed-form computation."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    body = tree.body
    droot_funcs = [n for n in body if _is_digit_root_func(source, n)]
    if not droot_funcs:
        return []

    rest = [n for n in body if not isinstance(n, ast.FunctionDef)]
    if not rest:
        return []

    joined = "\n".join(ast.dump(n) for n in rest)
    if 'divmod' in joined and 'Mod' in joined and '9' in joined:
        return []

    n_var = None
    keep_stmt = None
    for stmt in rest:
        v = _find_n_assignment(stmt)
        if v:
            n_var = v
            keep_stmt = stmt
            break

    first = rest[0]
    last = rest[-1]
    start_s, _ = _span(source, first)
    _, end_e = _span(source, last)

    if keep_stmt is not None:
        _, keep_end = _span(source, keep_stmt)
        if n_var == 'n':
            block = _CANONICAL
        else:
            block = "n = {}\n".format(n_var) + _CANONICAL
        new_source = source[:keep_end] + "\n" + block + source[end_e:]
    else:
        block = "n = int(input())\n" + _CANONICAL
        new_source = source[:start_s] + block + source[end_e:]

    if new_source == source:
        return []
    return [new_source]


def _lt_to_le(source):
    """Relax a strict `<` comparison to `<=` (off-by-one boundary slip)."""
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


def _range_upper_bound_off_by_one(source):
    """Bump a `range(a, n)` upper bound to `range(a, n + 1)` when the
    bound is a bare Name -- a common off-by-one on an inclusive range."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'range' and len(node.args) == 2:
            upper = node.args[1]
            if isinstance(upper, ast.Name):
                s, e = _span(source, upper)
                new_text = source[s:e] + " + 1"
                candidate = source[:s] + new_text + source[e:]
                if candidate != source:
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="digital_root_bruteforce_to_closed_form",
                apply=_digital_root_bruteforce_rule,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_upper_bound_off_by_one",
                apply=_range_upper_bound_off_by_one,
                symptoms=("wrong",),
            ),
        ]