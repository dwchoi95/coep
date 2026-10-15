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


def _contains_mod2(node):
    for n in ast.walk(node):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod):
            right = n.right
            if isinstance(right, ast.Constant) and right.value == 2:
                return True
    return False


def _eq_to_parity_check(source):
    """
    The classic 'triangular number / sqrt formula' solution for this problem
    needs to test whether the gap between the reached triangular number and
    the target has the *same parity*, not whether it lands exactly on the
    target.  Submissions that wrote `if location == x:` (followed by an
    elif that already does the correct `% 2 == 0` check for the +1/+2
    cases) made this slip.  We rewrite the equality test into the parity
    test using the exact same operands.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)):
            continue
        orelse = node.orelse
        if len(orelse) != 1 or not isinstance(orelse[0], ast.If):
            continue
        elif_node = orelse[0]
        if not _contains_mod2(elif_node.test):
            continue
        left = test.left
        right = test.comparators[0]
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        new_test = "(" + source[ls:le] + " - " + source[rs:re_] + ") % 2 == 0"
        candidate = _splice(source, test, new_test)
        if candidate != source:
            out.append(candidate)
    return out


def _missing_abs_on_input(source):
    """
    The answer to this problem only depends on |x|, so many correct
    solutions wrap the parsed input in abs().  Submissions that read
    `int(input())` and feed it straight into a formula that implicitly
    assumes a non-negative target (without ever negating it) fail only on
    negative inputs.  Wrap the bare `int(input())` call with abs(), unless
    it is already wrapped.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'int' and len(node.args) == 1):
            continue
        inner = node.args[0]
        if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                and inner.func.id == 'input'):
            continue
        s, e = _span(source, node)
        prefix = source[:s].rstrip()
        if prefix.endswith('abs('):
            continue
        new_text = "abs(" + source[s:e] + ")"
        candidate = _splice(source, node, new_text)
        if candidate != source:
            out.append(candidate)
    return out


_ALT_OP = {
    ast.Lt: '<=',
    ast.LtE: '<',
    ast.Gt: '>=',
    ast.GtE: '>',
}


def _comparison_bound_relax(source):
    """
    Generic off-by-one slip: a strict/non-strict boundary comparison is
    flipped the wrong way (e.g. a loop or condition stops one step too
    early/late).  Generate the alternate-strictness variant of each
    single-operator comparison.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
            continue
        op = node.ops[0]
        alt = _ALT_OP.get(type(op))
        if alt is None:
            continue
        left, right = node.left, node.comparators[0]
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        new_cmp = source[ls:le] + " " + alt + " " + source[rs:re_]
        candidate = _splice(source, node, new_cmp)
        if candidate != source:
            out.append(candidate)
    return out


def _range_bound_off_by_one(source):
    """
    Generic off-by-one slip: the final bound of a range() call is one too
    high or too low.  Generate both +1 and -1 variants of the last
    argument.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'range' and len(node.args) in (1, 2, 3)):
            continue
        last = node.args[-1]
        ls, le = _span(source, last)
        text = source[ls:le]
        for sign in ('+', '-'):
            new_arg = "(" + text + " " + sign + " 1)"
            candidate = _splice(source, last, new_arg)
            if candidate != source:
                out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="eq_should_be_parity_check",
                apply=_eq_to_parity_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_abs_on_input",
                apply=_missing_abs_on_input,
                symptoms=("wrong",),
            ),
            Rule(
                name="comparison_bound_relax",
                apply=_comparison_bound_relax,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="range_bound_off_by_one",
                apply=_range_bound_off_by_one,
                symptoms=("wrong",),
            ),
        ]