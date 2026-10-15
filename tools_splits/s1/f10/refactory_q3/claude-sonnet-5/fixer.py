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


def _find_empty_list_accumulator(func_node):
    """Find a variable initialized as `name = []` directly in the function body."""
    for stmt in func_node.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
           and isinstance(stmt.targets[0], ast.Name):
            val = stmt.value
            if isinstance(val, ast.List) and len(val.elts) == 0:
                return stmt.targets[0].id
    return None


def _fix_wrong_container_in_membership_check(source):
    """
    Misconception: the loop checks membership/count against the wrong
    container (the original input list, the loop variable itself, or an
    undefined name) instead of checking against the accumulator list that
    is being built up to hold the de-duplicated results.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        acc_name = _find_empty_list_accumulator(func)
        if acc_name is None:
            continue

        edits = {}
        for node in ast.walk(func):
            if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
                continue
            loop_var = node.target.id

            for sub in ast.walk(node):
                if not isinstance(sub, ast.If):
                    continue
                test = sub.test
                if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
                    continue
                op = test.ops[0]

                if isinstance(op, (ast.In, ast.NotIn)):
                    left = test.left
                    right = test.comparators[0]
                    left_is_loopvar = isinstance(left, ast.Name) and left.id == loop_var
                    right_is_acc = isinstance(right, ast.Name) and right.id == acc_name

                    if left_is_loopvar and not right_is_acc:
                        span = _span(source, right)
                        if source[span[0]:span[1]] != acc_name:
                            edits[span] = acc_name
                    elif right_is_acc and not left_is_loopvar:
                        span = _span(source, left)
                        if source[span[0]:span[1]] != loop_var:
                            edits[span] = loop_var

                elif isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)):
                    for side in (test.left, test.comparators[0]):
                        if isinstance(side, ast.Call) and isinstance(side.func, ast.Attribute) \
                           and side.func.attr == "count" and len(side.args) == 1:
                            container = side.func.value
                            if isinstance(container, ast.Name) and container.id != acc_name:
                                span = _span(source, container)
                                if source[span[0]:span[1]] != acc_name:
                                    edits[span] = acc_name

        if not edits:
            continue

        new_source = source
        for (s, e) in sorted(edits.keys(), key=lambda se: se[0], reverse=True):
            new_source = new_source[:s] + edits[(s, e)] + new_source[e:]
        if new_source != source:
            out.append(new_source)

    return out


def _fix_augassign_append_misuse(source):
    """
    Misconception: using `acc += something.append(x)` (which is a TypeError /
    nonsense, since list.append returns None) instead of a plain
    `acc.append(x)` statement. Rewrite just that statement, using the
    accumulator name actually being updated (the AugAssign target).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) \
           and isinstance(node.target, ast.Name):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
               and val.func.attr == "append" and len(val.args) == 1:
                arg_s, arg_e = _span(source, val.args[0])
                arg_text = source[arg_s:arg_e]
                target_name = node.target.id
                new_stmt = f"{target_name}.append({arg_text})"
                candidate = _splice(source, node, new_stmt)
                if candidate != source:
                    out.append(candidate)

    return out


def _fix_set_based_dedup(source):
    """
    Misconception: using `set(x)` (or similar) to remove duplicates, which
    loses ordering. Replace just that call expression with an order
    preserving equivalent, leaving everything else untouched.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "set" and len(node.args) == 1 and not node.keywords:
            arg_s, arg_e = _span(source, node.args[0])
            arg_text = source[arg_s:arg_e]
            new_expr = f"list(dict.fromkeys({arg_text}))"
            candidate = _splice(source, node, new_expr)
            if candidate != source:
                out.append(candidate)

    return out


from src.core.repair import Rule


class Fixer:
    def rules(self):
        return [
            Rule(
                name="wrong_container_in_membership_check",
                apply=_fix_wrong_container_in_membership_check,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="augassign_append_misuse",
                apply=_fix_augassign_append_misuse,
                symptoms=("wrong", "err:TypeError", "err:NameError"),
            ),
            Rule(
                name="set_based_dedup_loses_order",
                apply=_fix_set_based_dedup,
                symptoms=("wrong",),
            ),
        ]