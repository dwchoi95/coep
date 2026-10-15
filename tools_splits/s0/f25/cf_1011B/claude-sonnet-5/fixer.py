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


def _is_int_split_call(val):
    """Detect map(int, input().split()) or [int(i) for i in input().split()]."""
    if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == 'map':
        if len(val.args) == 2 and isinstance(val.args[0], ast.Name) and val.args[0].id == 'int':
            return True
    if isinstance(val, ast.ListComp):
        if isinstance(val.elt, ast.Call) and isinstance(val.elt.func, ast.Name) and val.elt.func.id == 'int':
            return True
    return False


def _find_input_pair_vars(tree):
    """Find the first `X, Y = map(int, input().split())`-like statement and
    return (X_name, Y_name); this corresponds to (n, m) in the problem."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Tuple) and len(tgt.elts) == 2 and \
               all(isinstance(e, ast.Name) for e in tgt.elts):
                if _is_int_split_call(node.value):
                    return tgt.elts[0].id, tgt.elts[1].id
    return None


def _constant_int_assign_pairs(node):
    """Yield (name, value_node) for simple or tuple assignments whose value
    is a plain int Constant."""
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return
    tgt = node.targets[0]
    val = node.value
    if isinstance(tgt, ast.Name) and isinstance(val, ast.Constant) and \
       isinstance(val.value, int) and not isinstance(val.value, bool):
        yield tgt.id, val
    elif isinstance(tgt, ast.Tuple) and isinstance(val, ast.Tuple) and \
         len(tgt.elts) == len(val.elts):
        for t_el, v_el in zip(tgt.elts, val.elts):
            if isinstance(t_el, ast.Name) and isinstance(v_el, ast.Constant) and \
               isinstance(v_el.value, int) and not isinstance(v_el.value, bool):
                yield t_el.id, v_el


def _sub_names(expr):
    """If expr is `A - B` with A, B plain names, return (A, B)."""
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Sub) and \
       isinstance(expr.left, ast.Name) and isinstance(expr.right, ast.Name):
        return expr.left.id, expr.right.id
    return None


def _while_uses_bound_as_r(while_node, r_name):
    """Check whether `while_node`'s test compares (r_name - l) to a constant,
    in either operand order; this is the classic `r - l > 1` binary-search
    convergence test. Returns the paired `l` variable name, or None."""
    test = while_node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return None
    op = test.ops[0]
    left = test.left
    right = test.comparators[0]

    sn = _sub_names(left)
    if sn and sn[0] == r_name and isinstance(right, ast.Constant) and \
       isinstance(right.value, int) and isinstance(op, (ast.Gt, ast.GtE)):
        return sn[1]

    sn = _sub_names(right)
    if sn and sn[0] == r_name and isinstance(left, ast.Constant) and \
       isinstance(left.value, int) and isinstance(op, (ast.Lt, ast.LtE)):
        return sn[1]

    return None


def _hardcoded_binsearch_bound(source):
    """Binary search over the answer whose upper bound is seeded with a
    hardcoded literal (e.g. `r = 100`) instead of a bound derived from the
    actual input size (`m`). This makes the search invariant `check(r) is
    False` fail exactly when some count reaches the constraint's maximum,
    producing an off-by-one wrong answer. Replace the literal bound with
    `<m> + 1`, which is always a valid "false" sentinel for this problem.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    pair = _find_input_pair_vars(tree)
    if not pair:
        return []
    n_name, m_name = pair

    whiles = [node for node in ast.walk(tree) if isinstance(node, ast.While)]
    if not whiles:
        return []

    out = []
    seen = set()
    for node in ast.walk(tree):
        for r_name, val_node in _constant_int_assign_pairs(node):
            if r_name in (n_name, m_name):
                continue
            matched = any(_while_uses_bound_as_r(w, r_name) is not None for w in whiles)
            if not matched:
                continue
            key = (id(node), r_name, val_node.value)
            if key in seen:
                continue
            seen.add(key)
            replacement = "%s + 1" % m_name
            new_src = _splice(source, val_node, replacement)
            if new_src != source:
                out.append(new_src)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="binsearch_hardcoded_upper_bound",
                apply=_hardcoded_binsearch_bound,
                symptoms=("wrong",),
            ),
        ]