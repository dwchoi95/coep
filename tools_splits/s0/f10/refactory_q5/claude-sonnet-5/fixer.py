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


def _build_parent_map(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _node_eq_name(a, b):
    return isinstance(a, ast.Name) and isinstance(b, ast.Name) and a.id == b.id


def _index_is_name(slice_node, idx_name):
    target = slice_node
    if isinstance(target, ast.Index):  # pragma: no cover (py<3.9)
        target = target.value
    return isinstance(target, ast.Name) and target.id == idx_name


def _fix_off_by_one(source):
    """A `k+1` upper bound in a slice, or `k-1` bound in range(), is a classic
    off-by-one around the count `k`. Drop the +/-1, keeping only the name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parents = _build_parent_map(tree)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub))):
            continue
        left, right = node.left, node.right
        const = other = None
        if isinstance(right, ast.Constant) and isinstance(right.value, int) and right.value == 1:
            const, other = right, left
        elif (isinstance(node.op, ast.Add) and isinstance(left, ast.Constant)
              and isinstance(left.value, int) and left.value == 1):
            const, other = left, right
        if const is None or not isinstance(other, ast.Name):
            continue

        parent = parents.get(node)
        is_slice_upper = isinstance(parent, ast.Slice) and parent.upper is node
        is_range_arg = (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name)
                         and parent.func.id == 'range' and node in parent.args)
        if not (is_slice_upper or is_range_arg):
            continue

        other_src = ast.get_source_segment(source, other)
        if other_src is None:
            continue
        out.append(_splice(source, node, other_src))
    return out


def _add_reverse_true(source):
    """`.sort()` with no reverse argument, used to pick "top" values, is
    sorting the wrong direction. Add reverse=True."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'sort' and not node.args and not node.keywords):
            fs, fe = _span(source, node.func)
            func_src = source[fs:fe]
            new_call = func_src + "(reverse=True)"
            s, e = _span(source, node)
            out.append(source[:s] + new_call + source[e:])
    return out


def _fix_manual_max_pop(source):
    """Collapse the manual "scan range(-len(x),0), compare to max(x), pop,
    bump counter" idiom down to the direct max()/remove() idiom. This fixes
    the duplicate-value / mutate-while-iterating misconception without
    touching anything else in the function."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue

        it = node.iter
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == 'range'):
            continue
        if len(it.args) != 2:
            continue
        a0, a1 = it.args
        if not (isinstance(a0, ast.UnaryOp) and isinstance(a0.op, ast.USub)):
            continue
        inner = a0.operand
        if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                and inner.func.id == 'len' and len(inner.args) == 1):
            continue
        x_node = inner.args[0]
        if not (isinstance(a1, ast.Constant) and a1.value == 0):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        idx_name = node.target.id

        if_node = None
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                if_node = stmt
                break
        if if_node is None:
            continue

        test = if_node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
            continue
        left, right = test.left, test.comparators[0]

        def is_sub(n):
            return (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                    and _node_eq_name(n.value, x_node) and _index_is_name(n.slice, idx_name))

        def is_maxcall(n):
            return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'max'
                    and len(n.args) == 1 and _node_eq_name(n.args[0], x_node))

        if is_sub(left) and is_maxcall(right):
            pass
        elif is_sub(right) and is_maxcall(left):
            pass
        else:
            continue

        append_call = None
        counter_incr = None
        results_name_node = None
        for s2 in if_node.body:
            if isinstance(s2, ast.Expr) and isinstance(s2.value, ast.Call):
                call = s2.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == 'append' and len(call.args) == 1:
                    inner_call = call.args[0]
                    if (isinstance(inner_call, ast.Call) and isinstance(inner_call.func, ast.Attribute)
                            and inner_call.func.attr == 'pop' and isinstance(inner_call.func.value, ast.Name)
                            and _node_eq_name(inner_call.func.value, x_node)):
                        append_call = s2
                        results_name_node = call.func.value
            elif isinstance(s2, ast.AugAssign) and isinstance(s2.op, ast.Add):
                counter_incr = s2
            elif isinstance(s2, ast.Assign) and len(s2.targets) == 1:
                tgt, val = s2.targets[0], s2.value
                if isinstance(tgt, ast.Name) and isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                    counter_incr = s2

        if append_call is None or counter_incr is None or not isinstance(results_name_node, ast.Name):
            continue

        x_src = ast.get_source_segment(source, x_node)
        results_src = ast.get_source_segment(source, results_name_node)
        if x_src is None or results_src is None:
            continue
        if isinstance(counter_incr, ast.AugAssign):
            counter_name = counter_incr.target.id
        else:
            counter_name = counter_incr.targets[0].id

        s, e = _span(source, node)
        lines = source.splitlines(keepends=True)
        starts = [0]
        for ln in lines:
            starts.append(starts[-1] + len(ln))
        line_start = starts[node.lineno - 1]
        indent = source[line_start:s]

        new_text = (
            f"{results_src}.append(max({x_src}))\n"
            f"{indent}{x_src}.remove(max({x_src}))\n"
            f"{indent}{counter_name} += 1"
        )
        out.append(source[:s] + new_text + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="off_by_one_bound",
                apply=_fix_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="sort_missing_reverse",
                apply=_add_reverse_true,
                symptoms=("wrong",),
            ),
            Rule(
                name="manual_max_search_collapse",
                apply=_fix_manual_max_pop,
                symptoms=("wrong", "timeout"),
            ),
        ]