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


def _find_pos_var(tree):
    """Find the variable that receives int(input()) (optionally wrapped in abs())."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            inner = val
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) \
               and inner.func.id == 'abs' and len(inner.args) == 1:
                inner = inner.args[0]
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) \
               and inner.func.id == 'int' and len(inner.args) == 1:
                arg = inner.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) \
                   and arg.func.id == 'input':
                    return node.targets[0].id
    return None


def _match_increment_binop(stmt, op_type):
    """Match `x = x <op> y` or `x <op>= y` where y is a Name. Returns (x, y) or None."""
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
       and isinstance(stmt.targets[0], ast.Name):
        x = stmt.targets[0].id
        val = stmt.value
        if isinstance(val, ast.BinOp) and isinstance(val.op, op_type):
            if isinstance(val.left, ast.Name) and val.left.id == x \
               and isinstance(val.right, ast.Name):
                return x, val.right.id
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) \
       and isinstance(stmt.op, op_type):
        if isinstance(stmt.value, ast.Name):
            return stmt.target.id, stmt.value.id
    return None


def _match_self_increment_by_one(stmt, var_name):
    """Match `var += 1` or `var = var + 1` (or `1 + var`)."""
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) \
       and stmt.target.id == var_name and isinstance(stmt.op, ast.Add):
        if isinstance(stmt.value, ast.Constant) and stmt.value.value == 1:
            return True
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
       and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == var_name:
        val = stmt.value
        if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
            if isinstance(val.left, ast.Name) and val.left.id == var_name \
               and isinstance(val.right, ast.Constant) and val.right.value == 1:
                return True
            if isinstance(val.right, ast.Name) and val.right.id == var_name \
               and isinstance(val.left, ast.Constant) and val.left.value == 1:
                return True
    return False


def _scan_branch_for_pair(branch_stmts, op_type):
    for i, s in enumerate(branch_stmts):
        m = _match_increment_binop(s, op_type)
        if m:
            curr_name, incr_name = m
            for s2 in branch_stmts[i + 1:]:
                if _match_self_increment_by_one(s2, incr_name):
                    return curr_name, incr_name
    return None


def _find_cnt_var(while_body, if_stmt):
    for s in while_body:
        if s is if_stmt:
            break
        if isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name) \
           and isinstance(s.op, ast.Add):
            if isinstance(s.value, ast.Constant) and s.value.value == 1:
                return s.target.id
    return None


def _find_pos_from_test(test, curr_var):
    for n in ast.walk(test):
        if isinstance(n, ast.Name) and n.id != curr_var:
            return n.id
    return None


def _dual_counter_sim_rewrite(source):
    """Fixes the misconception of using two separate, independently growing
    step counters for the 'go right' and 'go left' branches of a jump
    simulation. Replaces the simulation loop with a direct search for the
    minimal number of jumps using the triangular-number parity rule."""
    tree = _safe_parse(source)
    if tree is None:
        return []

    global_pos_var = _find_pos_var(tree)
    out = []

    for w in ast.walk(tree):
        if not isinstance(w, ast.While):
            continue
        body = getattr(w, 'body', [])
        for stmt in body:
            if not (isinstance(stmt, ast.If) and stmt.orelse):
                continue

            combos = [(ast.Add, ast.Sub), (ast.Sub, ast.Add)]
            match = None
            for if_op, else_op in combos:
                if_match = _scan_branch_for_pair(stmt.body, if_op)
                else_match = _scan_branch_for_pair(stmt.orelse, else_op)
                if if_match and else_match and if_match[0] == else_match[0] \
                   and if_match[1] != else_match[1]:
                    match = (if_match, else_match)
                    break
            if not match:
                continue

            curr_var = match[0][0]
            cnt_var = _find_cnt_var(body, stmt)
            if cnt_var is None:
                continue

            pos_var = _find_pos_from_test(w.test, curr_var)
            if pos_var is None:
                pos_var = global_pos_var
            if pos_var is None:
                continue

            indent = ' ' * w.col_offset
            lines = [
                f"{cnt_var} = 0",
                "__s = 0",
                f"__ax = abs({pos_var})",
                "while __s < __ax or (__s - __ax) % 2 != 0:",
                f"    {cnt_var} += 1",
                f"    __s += {cnt_var}",
            ]
            new_text = "\n".join(indent + l for l in lines)
            out.append(_splice(source, w, new_text))

    return out


def _adhoc_min_branch_rewrite(source):
    """Fixes the misconception of searching for the triangular-number bound
    with a 'while True' loop and then patching up the parity mismatch with
    an ad-hoc pair of corrective formulas fed into min(). Replaces the whole
    search loop with the correct parity-based search."""
    tree = _safe_parse(source)
    if tree is None:
        return []

    pos_var = _find_pos_var(tree)
    if pos_var is None:
        return []

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        is_true = (isinstance(test, ast.Constant) and test.value is True) or \
                  (isinstance(test, ast.Name) and test.id == 'True')
        if not is_true:
            continue

        found_min_print = False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
               and sub.func.id == 'print':
                for a in sub.args:
                    if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) \
                       and a.func.id == 'min':
                        found_min_print = True
        if not found_min_print:
            continue

        indent = ' ' * node.col_offset
        lines = [
            f"__ax = abs({pos_var})",
            "__n = 0",
            "__s = 0",
            "while __s < __ax or (__s - __ax) % 2 != 0:",
            "    __n += 1",
            "    __s += __n",
            "print(__n)",
        ]
        new_text = "\n".join(indent + l for l in lines)
        out.append(_splice(source, node, new_text))

    return out


def _lt_to_le(source):
    """Relax a strict `<` comparison to `<=` (classic off-by-one slip)."""
    tree = _safe_parse(source)
    if tree is None:
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


def _gt_to_ge(source):
    """Relax a strict `>` comparison to `>=` (classic off-by-one slip)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Gt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " >= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="dual_counter_sim_rewrite",
                apply=_dual_counter_sim_rewrite,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="adhoc_min_branch_rewrite",
                apply=_adhoc_min_branch_rewrite,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_should_be_gte",
                apply=_gt_to_ge,
                symptoms=("wrong",),
            ),
        ]