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


def _line_indent(source, node):
    """Literal leading whitespace (tabs/spaces) preceding node on its line."""
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[:node.col_offset]


def _fix_overshoot_branch(source):
    """
    Pattern: if formula < x: n+=1
             elif formula == x: print(n); break
             elif formula > x: <buggy one-shot adjustment>
    The overshoot branch must keep bumping n until the parity of
    (formula - x) matches, not just add a single fixed offset.
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
                and isinstance(test.ops[0], ast.Lt)):
            continue
        if len(node.orelse) != 1 or not isinstance(node.orelse[0], ast.If):
            continue
        eq_if = node.orelse[0]
        eq_test = eq_if.test
        if not (isinstance(eq_test, ast.Compare) and len(eq_test.ops) == 1
                and isinstance(eq_test.ops[0], ast.Eq)):
            continue
        if len(eq_if.orelse) != 1 or not isinstance(eq_if.orelse[0], ast.If):
            continue
        gt_if = eq_if.orelse[0]
        gt_test = gt_if.test
        if not (isinstance(gt_test, ast.Compare) and len(gt_test.ops) == 1
                and isinstance(gt_test.ops[0], ast.Gt)):
            continue
        try:
            f1s, f1e = _span(source, test.left)
            v1s, v1e = _span(source, test.comparators[0])
            f2s, f2e = _span(source, gt_test.left)
            v2s, v2e = _span(source, gt_test.comparators[0])
        except Exception:
            continue
        formula_src = source[f1s:f1e]
        var_src = source[v1s:v1e]
        if source[f2s:f2e] != formula_src or source[v2s:v2e] != var_src:
            continue
        n_name = None
        for st in node.body:
            if (isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name)
                    and isinstance(st.op, ast.Add)):
                n_name = st.target.id
                break
        if n_name is None:
            continue
        indent = _line_indent(source, gt_if)
        new_body = (
            f"while (int({formula_src}) - ({var_src})) % 2 != 0:\n"
            f"{indent}    {n_name} += 1\n"
            f"{indent}print(int({n_name}))\n"
            f"{indent}break"
        )
        out.append(_splice(source, gt_if, new_body))
    return out


def _fix_cumulative_sum_loop(source):
    """
    Pattern: while p < n:
                 if <cond>:
                     s += 1
                 else:
                     p += s
                     s += 1
    This never re-checks parity of the remaining gap, so it stops one
    step early/late. Replace with the standard sum-with-parity loop.
    """
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
                and isinstance(test.ops[0], ast.Lt)
                and isinstance(test.left, ast.Name)
                and isinstance(test.comparators[0], ast.Name)):
            continue
        p_name = test.left.id
        n_name = test.comparators[0].id
        if len(node.body) != 1 or not isinstance(node.body[0], ast.If):
            continue
        if_node = node.body[0]
        if len(if_node.orelse) != 2:
            continue
        s1, s2 = if_node.orelse
        if not (isinstance(s1, ast.AugAssign) and isinstance(s1.op, ast.Add)
                and isinstance(s1.target, ast.Name) and s1.target.id == p_name
                and isinstance(s1.value, ast.Name)):
            continue
        s_name = s1.value.id
        if not (isinstance(s2, ast.AugAssign) and isinstance(s2.op, ast.Add)
                and isinstance(s2.target, ast.Name) and s2.target.id == s_name
                and isinstance(s2.value, ast.Constant) and s2.value.value == 1):
            continue
        indent = _line_indent(source, node)
        new_while = (
            f"while {p_name} < {n_name} or ({n_name} - {p_name}) % 2 != 0:\n"
            f"{indent}    {p_name} += {s_name}\n"
            f"{indent}    {s_name} += 1"
        )
        out.append(_splice(source, node, new_while))
    return out


def _break_into_else(source):
    """
    Pattern: if temp % 2 == 1:
                 c += 1
             break
    The bare 'break' always fires, even though the adjustment only
    produced a correct answer sometimes. It should only break when no
    further adjustment is needed (i.e. move it into an else branch).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    blocks = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(node, field, None)
            if isinstance(lst, list):
                blocks.append(lst)
    for block in blocks:
        for i in range(len(block) - 1):
            a, b = block[i], block[i + 1]
            if isinstance(a, ast.If) and not a.orelse and isinstance(b, ast.Break):
                s1, e1 = _span(source, a)
                s2, e2 = _span(source, b)
                indent = _line_indent(source, a)
                if_text = source[s1:e1]
                new_text = if_text + "\n" + indent + "else:\n" + indent + "    break"
                out.append(source[:s1] + new_text + source[e2:])
    return out


def _insert_abs_after_input(source):
    """
    Pattern: X = int(input())
    When X is never wrapped in abs(...) anywhere, yet the algorithm
    relies on a non-negative target, negative inputs break it.
    Insert X = abs(X) right after the read.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    abs_wrapped = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "abs" and len(node.args) == 1
                and isinstance(node.args[0], ast.Name)):
            abs_wrapped.add(node.args[0].id)

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        val = node.value
        if not (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                and val.func.id == "int"):
            continue
        if not (len(val.args) == 1 and isinstance(val.args[0], ast.Call)
                and isinstance(val.args[0].func, ast.Name)
                and val.args[0].func.id == "input"):
            continue
        name = node.targets[0].id
        if name in abs_wrapped:
            continue
        indent = _line_indent(source, node)
        _, e = _span(source, node)
        insertion = f"\n{indent}{name} = abs({name})"
        out.append(source[:e] + insertion + source[e:])
    return out


def _fix_two_step_adjustment(source):
    """
    Pattern: i -= 1
             i += 2 * (n - current)
             print(i)
    following a triangular-number accumulation loop. This single-shot
    adjustment is not always correct; replace with a loop that keeps
    advancing until both the sum and parity conditions hold.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    blocks = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(node, field, None)
            if isinstance(lst, list):
                blocks.append(lst)
    for block in blocks:
        for idx in range(len(block) - 2):
            a, b, c = block[idx], block[idx + 1], block[idx + 2]
            if not (isinstance(a, ast.AugAssign) and isinstance(a.op, ast.Sub)
                    and isinstance(a.target, ast.Name)):
                continue
            if not (isinstance(a.value, ast.Constant) and a.value.value == 1):
                continue
            i_name = a.target.id
            if not (isinstance(b, ast.AugAssign) and isinstance(b.op, ast.Add)
                    and isinstance(b.target, ast.Name) and b.target.id == i_name):
                continue
            bval = b.value
            if not (isinstance(bval, ast.BinOp) and isinstance(bval.op, ast.Mult)):
                continue
            left, right = bval.left, bval.right
            sub_node = None
            if (isinstance(left, ast.Constant) and left.value == 2
                    and isinstance(right, ast.BinOp) and isinstance(right.op, ast.Sub)):
                sub_node = right
            elif (isinstance(right, ast.Constant) and right.value == 2
                    and isinstance(left, ast.BinOp) and isinstance(left.op, ast.Sub)):
                sub_node = left
            if sub_node is None:
                continue
            if not (isinstance(sub_node.left, ast.Name) and isinstance(sub_node.right, ast.Name)):
                continue
            n_name = sub_node.left.id
            current_name = sub_node.right.id
            if not (isinstance(c, ast.Expr) and isinstance(c.value, ast.Call)
                    and isinstance(c.value.func, ast.Name) and c.value.func.id == "print"):
                continue
            if len(c.value.args) != 1 or not (isinstance(c.value.args[0], ast.Name)
                                               and c.value.args[0].id == i_name):
                continue
            indent = _line_indent(source, a)
            new_code = (
                f"while not ({current_name} >= {n_name} and ({current_name} - {n_name}) % 2 == 0):\n"
                f"{indent}    {current_name} += {i_name}\n"
                f"{indent}    {i_name} += 1\n"
                f"{indent}print({i_name} - 1)"
            )
            s_a, _ = _span(source, a)
            _, e_c = _span(source, c)
            out.append(source[:s_a] + new_code + source[e_c:])
    return out


def _lt_to_le(source):
    """Generic: relax a strict '<' comparison to '<=' (cheap generic slip)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            try:
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
            except Exception:
                continue
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="overshoot_branch_one_shot_to_loop",
                apply=_fix_overshoot_branch,
                symptoms=("wrong",),
            ),
            Rule(
                name="cumulative_sum_loop_missing_parity_check",
                apply=_fix_cumulative_sum_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_break_should_be_conditional",
                apply=_break_into_else,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_abs_on_target_input",
                apply=_insert_abs_after_input,
                symptoms=("wrong",),
            ),
            Rule(
                name="two_step_adjustment_should_loop",
                apply=_fix_two_step_adjustment,
                symptoms=("wrong",),
            ),
            Rule(
                name="generic_strict_lt_to_le",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]