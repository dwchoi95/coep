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
    except Exception:
        return None


def _safe(fn):
    def wrapper(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapper


def _detect_accumulator(inner_for):
    """Detect a 'for x in seq: if acc OP x: acc = x' max/min tracking loop.
    Returns the accumulator variable name, or None."""
    if not isinstance(inner_for, ast.For) or not isinstance(inner_for.target, ast.Name):
        return None
    inner_var = inner_for.target.id
    for stmt in inner_for.body:
        if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare) and len(stmt.test.ops) == 1:
            left, right = stmt.test.left, stmt.test.comparators[0]
            candidates = []
            if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                if left.id == inner_var and right.id != inner_var:
                    candidates.append(right.id)
                elif right.id == inner_var and left.id != inner_var:
                    candidates.append(left.id)
            for acc in candidates:
                for b in stmt.body:
                    if (isinstance(b, ast.Assign) and len(b.targets) == 1 and
                            isinstance(b.targets[0], ast.Name) and b.targets[0].id == acc and
                            isinstance(b.value, ast.Name) and b.value.id == inner_var):
                        return acc
    return None


def _contains_remove_call(body, list_name, acc_name):
    for stmt in body:
        for node in ast.walk(stmt):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'remove' and isinstance(node.func.value, ast.Name) and
                    node.func.value.id == list_name):
                args = node.args
                if len(args) == 1 and isinstance(args[0], ast.Name) and args[0].id == acc_name:
                    return True
    return False


def _is_initialized_as_list(scope_node, name):
    for node in ast.walk(scope_node):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name) and node.targets[0].id == name and
                isinstance(node.value, ast.List)):
            return True
    return False


@_safe
def _fix_range_k_minus_one(source):
    """range(k - 1) should be range(k): off-by-one on the main counting loop."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or len(fn.args.args) < 2:
            continue
        k_name = fn.args.args[1].arg
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                    node.func.id == 'range' and len(node.args) == 1):
                arg = node.args[0]
                if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and
                        isinstance(arg.left, ast.Name) and arg.left.id == k_name and
                        isinstance(arg.right, ast.Constant) and arg.right.value == 1):
                    new_src = _splice(source, arg, k_name)
                    if new_src != source:
                        out.append(new_src)
    return out


@_safe
def _fix_accumulator_init_with_loop_var(source):
    """A max/min tracker is seeded with the outer loop index instead of a
    neutral starting value (e.g. `y = i` right before `if y < j: y = j`)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for outer in ast.walk(tree):
        if not isinstance(outer, ast.For) or not isinstance(outer.target, ast.Name):
            continue
        outer_var = outer.target.id
        body = outer.body
        for idx, stmt in enumerate(body):
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and
                    isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, ast.Name) and
                    stmt.value.id == outer_var):
                acc_name = stmt.targets[0].id
                for later in body[idx + 1:]:
                    acc = _detect_accumulator(later)
                    if acc == acc_name:
                        new_src = _splice(source, stmt.value, "0")
                        if new_src != source:
                            out.append(new_src)
                        break
    return out


@_safe
def _fix_augassign_to_append(source):
    """`x += y` on a list that was built with `x = []` should be `x.append(y)`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and
                    isinstance(node.target, ast.Name)):
                name = node.target.id
                if not _is_initialized_as_list(fn, name):
                    continue
                value = node.value
                if isinstance(value, (ast.List, ast.Tuple, ast.ListComp)):
                    continue
                s, e = _span(source, node)
                t_s, t_e = _span(source, node.target)
                v_s, v_e = _span(source, value)
                new_stmt = "{}.append({})".format(source[t_s:t_e], source[v_s:v_e])
                new_src = source[:s] + new_stmt + source[e:]
                if new_src != source:
                    out.append(new_src)
    return out


@_safe
def _fix_missing_remove_after_search(source):
    """A max/min search loop finds a value but never removes it from the
    source list, so the next iteration finds the same value again."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for outer in ast.walk(tree):
        if not isinstance(outer, ast.For):
            continue
        body = outer.body
        for idx, stmt in enumerate(body):
            if not isinstance(stmt, ast.For) or not isinstance(stmt.iter, ast.Name):
                continue
            acc = _detect_accumulator(stmt)
            if not acc:
                continue
            list_name = stmt.iter.id
            if _contains_remove_call(body, list_name, acc):
                continue
            used_later = any(
                isinstance(n, ast.Name) and n.id == acc
                for later in body[idx + 1:] for n in ast.walk(later)
            )
            if not used_later:
                continue
            s, e = _span(source, stmt)
            indent = ' ' * stmt.col_offset
            insertion = "\n{}{}.remove({})".format(indent, list_name, acc)
            new_src = source[:e] + insertion + source[e:]
            if new_src != source:
                out.append(new_src)
    return out


@_safe
def _fix_typo_append_target(source):
    """`.append()` is called on a name that was never assigned (a typo of
    the one list variable actually built in this function)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        assigned_names = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned_names.add(t.id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                assigned_names.add(node.target.id)
        for a in fn.args.args:
            assigned_names.add(a.arg)
        list_vars = []
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1 and
                    isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.List)):
                list_vars.append(node.targets[0].id)
        if len(list_vars) != 1:
            continue
        correct = list_vars[0]
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'append' and isinstance(node.func.value, ast.Name)):
                name = node.func.value.id
                if name in assigned_names or name == correct:
                    continue
                new_src = _splice(source, node.func.value, correct)
                if new_src != source:
                    out.append(new_src)
    return out


@_safe
def _fix_prune_min_then_exhaust(source):
    """Student removes the k smallest elements first (wrong approach), then
    drains the *whole* remaining list with max()/remove() instead of only
    taking k values. Drop the pruning loop and bound the drain loop by k."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or len(fn.args.args) < 2:
            continue
        k_param = fn.args.args[1].arg
        body = fn.body
        for i, stmt in enumerate(body):
            if not isinstance(stmt, ast.While):
                continue
            test = stmt.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and
                    isinstance(test.ops[0], ast.Lt) and isinstance(test.left, ast.Name)):
                continue
            if not (isinstance(test.comparators[0], ast.Name) and test.comparators[0].id == k_param):
                continue
            counter_name = test.left.id
            has_min_remove = False
            list_name = None
            for b in stmt.body:
                for node in ast.walk(b):
                    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
                            node.func.attr == 'remove' and isinstance(node.func.value, ast.Name)):
                        args = node.args
                        if (len(args) == 1 and isinstance(args[0], ast.Call) and
                                isinstance(args[0].func, ast.Name) and args[0].func.id == 'min'):
                            has_min_remove = True
                            list_name = node.func.value.id
            if not has_min_remove or not list_name:
                continue
            for j in range(i + 1, len(body)):
                stmt2 = body[j]
                if not isinstance(stmt2, ast.While):
                    continue
                has_max = any(
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'max'
                    for b in stmt2.body for node in ast.walk(b)
                )
                if not has_max or not stmt2.body:
                    continue
                src = source
                new_test_src = "{} < {}".format(counter_name, k_param)
                src = _splice(src, stmt2.test, new_test_src)
                last_stmt = stmt2.body[-1]
                ls, le = _span(src, last_stmt)
                indent = ' ' * last_stmt.col_offset
                incr = "\n{}{} = {} + 1".format(indent, counter_name, counter_name)
                src = src[:le] + incr + src[le:]
                s1, e1 = _span(src, stmt)
                new_src = src[:s1] + src[e1:]
                if new_src != source:
                    out.append(new_src)
                break
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="off_by_one_range_k_minus_1",
                apply=_fix_range_k_minus_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="accumulator_seeded_with_loop_index",
                apply=_fix_accumulator_init_with_loop_var,
                symptoms=("wrong",),
            ),
            Rule(
                name="augassign_scalar_onto_list_should_append",
                apply=_fix_augassign_to_append,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="missing_remove_after_max_search",
                apply=_fix_missing_remove_after_search,
                symptoms=("wrong",),
            ),
            Rule(
                name="typo_append_target_undefined_name",
                apply=_fix_typo_append_target,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="prune_k_smallest_then_exhaust_remainder",
                apply=_fix_prune_min_then_exhaust,
                symptoms=("wrong", "err:NameError"),
            ),
        ]