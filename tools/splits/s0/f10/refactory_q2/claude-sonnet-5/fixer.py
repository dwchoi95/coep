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


def _apply_edits(source, edits):
    spans = [(_span(source, node), text) for node, text in edits]
    spans.sort(key=lambda x: x[0][0], reverse=True)
    out = source
    for (s, e), text in spans:
        out = out[:s] + text + out[e:]
    return out


def _is_bool_const(node, value):
    return isinstance(node, ast.Constant) and node.value is value


def _rule_gt1_to_eq1(source):
    """`if x > 1: return False` (then/else) `return True` misses the 0-count case."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        for idx, stmt in enumerate(body):
            if not (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare)
                    and len(stmt.test.ops) == 1 and isinstance(stmt.test.ops[0], ast.Gt)
                    and len(stmt.test.comparators) == 1
                    and isinstance(stmt.test.comparators[0], ast.Constant)
                    and stmt.test.comparators[0].value == 1):
                continue
            if not (len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Return)
                    and _is_bool_const(stmt.body[0].value, False)):
                continue
            false_ret = stmt.body[0]
            true_ret = None
            if stmt.orelse and len(stmt.orelse) == 1 and isinstance(stmt.orelse[0], ast.Return) \
               and _is_bool_const(stmt.orelse[0].value, True):
                true_ret = stmt.orelse[0]
            elif not stmt.orelse and idx + 1 < len(body) and isinstance(body[idx + 1], ast.Return) \
                    and _is_bool_const(body[idx + 1].value, True):
                true_ret = body[idx + 1]
            if true_ret is None:
                continue
            left_s, left_e = _span(source, stmt.test.left)
            right_s, right_e = _span(source, stmt.test.comparators[0])
            new_test = source[left_s:left_e] + " == " + source[right_s:right_e]
            edits = [(stmt.test, new_test), (false_ret.value, "True"), (true_ret.value, "False")]
            out.append(_apply_edits(source, edits))
    return out


def _rule_flag_var_return(source):
    """A sentinel/flag variable is checked for duplicates but the final
    `return True` ignores the zero-match case; should return the flag's
    "was ever set" state instead."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        if len(body) < 2:
            continue
        first = body[0]
        if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)
                and isinstance(first.value, ast.Constant)):
            continue
        flag_name = first.targets[0].id
        for_node = None
        for stmt in body[1:]:
            if isinstance(stmt, ast.For):
                for_node = stmt
                break
        if for_node is None:
            continue
        assigns_flag = False
        for n in ast.walk(for_node):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
               and isinstance(n.targets[0], ast.Name) and n.targets[0].id == flag_name:
                assigns_flag = True
                break
        if not assigns_flag:
            continue
        last = body[-1]
        if not (isinstance(last, ast.Return) and _is_bool_const(last.value, True)):
            continue
        init_s, init_e = _span(source, first.value)
        init_text = source[init_s:init_e]
        new_return = "return {} != {}".format(flag_name, init_text)
        out.append(_splice(source, last, new_return))
    return out


def _rule_param_shadow_counter(source):
    """A counter variable shares a name with (or is confused with) the
    target parameter, and/or the increment uses yet another mismatched
    name than the one checked at the end."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        args = [a.arg for a in fn.args.args]
        if len(args) < 2:
            continue
        pb_arg = next((a for a in args if 'birthday' in a.lower()), None)
        other_arg = next((a for a in args if a != pb_arg), None)
        if pb_arg is None or other_arg is None:
            continue
        body = fn.body
        if not body:
            continue
        first = body[0]
        if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)
                and isinstance(first.value, ast.Constant) and first.value.value == 0):
            continue
        counter_name = first.targets[0].id
        for_node = None
        for stmt in body[1:]:
            if isinstance(stmt, ast.For):
                for_node = stmt
                break
        if for_node is None:
            continue
        cmp_name_node = None
        target_if = None
        for node in ast.walk(for_node):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
               and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq) \
               and isinstance(node.test.comparators[0], ast.Name):
                cmp_name_node = node.test.comparators[0]
                target_if = node
                break
        if cmp_name_node is None:
            continue
        incr_stmt = None
        for s in ast.walk(target_if):
            if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name) \
               and isinstance(s.value, ast.BinOp) and isinstance(s.value.op, ast.Add):
                incr_stmt = s
                break
            if isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name) and isinstance(s.op, ast.Add):
                incr_stmt = s
                break
        if incr_stmt is None:
            continue
        final_if = None
        for stmt in body:
            if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare) \
               and len(stmt.test.ops) == 1 and isinstance(stmt.test.ops[0], ast.Eq) \
               and isinstance(stmt.test.left, ast.Name) \
               and isinstance(stmt.test.comparators[0], ast.Constant) and stmt.test.comparators[0].value == 1:
                final_if = stmt
        if final_if is None:
            continue
        final_name_node = final_if.test.left

        incr_target_name = incr_stmt.targets[0].id if isinstance(incr_stmt, ast.Assign) else incr_stmt.target.id
        mismatched = (cmp_name_node.id != other_arg) or (counter_name == other_arg) \
            or (incr_target_name != counter_name) or (final_name_node.id != counter_name)
        if not mismatched:
            continue

        used_names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        fresh = "_uniq_counter"
        k = 0
        while fresh in used_names:
            k += 1
            fresh = "_uniq_counter{}".format(k)

        edits = [
            (first, "{} = 0".format(fresh)),
            (cmp_name_node, other_arg),
            (final_name_node, fresh),
        ]
        if isinstance(incr_stmt, ast.Assign):
            edits.append((incr_stmt, "{0} = {0} + 1".format(fresh)))
        else:
            edits.append((incr_stmt, "{} += 1".format(fresh)))
        out.append(_apply_edits(source, edits))
    return out


def _rule_undefined_name_to_param(source):
    """A comparison references an undefined bare name where the target
    parameter was clearly meant (classic `day` vs `date` typo)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        args = [a.arg for a in fn.args.args]
        if len(args) != 2:
            continue
        pb_arg = next((a for a in args if 'birthday' in a.lower()), None)
        other_arg = next((a for a in args if a != pb_arg), None)
        if pb_arg is None or other_arg is None:
            continue
        defined = set(args)
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                defined.add(n.target.id)
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                for side in (node.left, node.comparators[0]):
                    if isinstance(side, ast.Name) and side.id not in defined and side.id != pb_arg:
                        out.append(_splice(source, side, other_arg))
    return out


def _rule_undefined_loop_index(source):
    """A subscript inside a for-loop indexes with a name that is never
    defined in that loop (typically a typo for the loop variable)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = {a.arg for a in fn.args.args}
        for for_node in ast.walk(fn):
            if not (isinstance(for_node, ast.For) and isinstance(for_node.target, ast.Name)):
                continue
            loop_var = for_node.target.id
            safe = {loop_var} | params
            for n in ast.walk(for_node):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            safe.add(t.id)
                if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                    safe.add(n.target.id)
            for sub in ast.walk(for_node):
                if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Name):
                    idx_name = sub.slice.id
                    if idx_name != loop_var and idx_name not in safe:
                        out.append(_splice(source, sub.slice, loop_var))
    return out


def _rule_loop_premature_false(source):
    """`for x in seq: if cond: return True else: return False` bails out
    after the first element instead of continuing and defaulting to False."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.For) and len(node.body) == 1 and isinstance(node.body[0], ast.If):
                if_node = node.body[0]
                if len(if_node.body) == 1 and isinstance(if_node.body[0], ast.Return) \
                   and _is_bool_const(if_node.body[0].value, True) \
                   and len(if_node.orelse) == 1 and isinstance(if_node.orelse[0], ast.Return) \
                   and _is_bool_const(if_node.orelse[0].value, False):
                    orelse_ret = if_node.orelse[0]
                    indent = ' ' * node.col_offset
                    for_s, for_e = _span(source, node)
                    new_source = source[:for_e] + "\n" + indent + "return False" + source[for_e:]
                    s2, e2 = _span(source, orelse_ret)
                    new_source = new_source[:s2] + "continue" + new_source[e2:]
                    out.append(new_source)
    return out


def _rule_premature_return_removal(source):
    """An unconditional `return` appears before other, reachable statements
    in the same block, making the real logic dead code."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        for stmt in body[:-1]:
            if isinstance(stmt, ast.Return):
                s, e = _span(source, stmt)
                line_start = source.rfind('\n', 0, s) + 1
                new_source = source[:line_start] + source[e:]
                out.append(new_source)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="gt1_false_return_true_to_eq1",
                 apply=_rule_gt1_to_eq1,
                 symptoms=("wrong",)),
            Rule(name="flag_var_return_true_to_flag_check",
                 apply=_rule_flag_var_return,
                 symptoms=("wrong",)),
            Rule(name="param_shadow_counter_mismatch",
                 apply=_rule_param_shadow_counter,
                 symptoms=("wrong", "err:UnboundLocalError", "err:NameError")),
            Rule(name="undefined_name_to_param",
                 apply=_rule_undefined_name_to_param,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_loop_index_to_loopvar",
                 apply=_rule_undefined_loop_index,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="loop_return_false_to_continue_plus_final_false",
                 apply=_rule_loop_premature_false,
                 symptoms=("wrong",)),
            Rule(name="premature_return_removal",
                 apply=_rule_premature_return_removal,
                 symptoms=("wrong",)),
        ]