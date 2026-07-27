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


def _replace_constant(source, node, new_value):
    return _splice(source, node, str(new_value))


def _find_name_loads(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == name:
            yield node


def _fix_upper_bound_100_to_m(source):
    """Expand a too-small binary-search upper bound from 100 to m or m+1."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 100:
            out.append(_replace_constant(source, node, "m"))
            out.append(_replace_constant(source, node, "m + 1"))
    return list(dict.fromkeys(out))


def _fix_zero_start_binary_search(source):
    """Replace a zero lower bound in binary search with one."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 0:
            out.append(_replace_constant(source, node, "1"))
    return list(dict.fromkeys(out))


def _fix_missing_reset_accumulator(source):
    """Move an accumulator reset into the loop when it is incorrectly placed outside."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            tgt = node.targets[0].id
            if isinstance(node.value, ast.Constant) and node.value.value == 0:
                parent_loop = None
                for p in ast.walk(tree):
                    if isinstance(p, (ast.For, ast.While)):
                        for child in ast.iter_child_nodes(p):
                            if child is node:
                                parent_loop = p
                                break
                    if parent_loop:
                        break
                if parent_loop is None:
                    for loop in ast.walk(tree):
                        if isinstance(loop, ast.For):
                            for stmt in loop.body:
                                if isinstance(stmt, ast.For):
                                    for inner in ast.walk(stmt):
                                        if isinstance(inner, ast.Name) and inner.id == tgt:
                                            out.append(_splice(source, node, ""))
                else:
                    pass
    return list(dict.fromkeys([s for s in out if s != source]))


def _fix_if_k_less_n_to_m_less_n(source):
    """Correct a misplaced feasibility check using k instead of m."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            if isinstance(node.left, ast.Name) and node.left.id == "k":
                right = node.comparators[0]
                if isinstance(right, ast.Name) and right.id == "n":
                    left_s, left_e = _span(source, node.left)
                    right_s, right_e = _span(source, right)
                    new_text = source[left_s:left_e] + " < " + source[right_s:right_e]
                    out.append(_splice(source, node, "m < n"))
    return list(dict.fromkeys(out))


def _fix_accumulator_reinit_inside_loop(source):
    """Insert a reset of s at the start of a loop when it accumulates across iterations."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for loop in ast.walk(tree):
        if isinstance(loop, (ast.For, ast.While)) and loop.body:
            for i, stmt in enumerate(loop.body):
                if isinstance(stmt, ast.For):
                    # look for s += ... in nested loop and outer s = 0 before it
                    has_s_add = any(
                        isinstance(x, ast.AugAssign) and isinstance(x.target, ast.Name) and x.target.id == "s"
                        for x in ast.walk(stmt)
                    )
                    if has_s_add:
                        insert_at = _span(source, loop.body[0])[0]
                        out.append(source[:insert_at] + "    s = 0\n" + source[insert_at:])
    return list(dict.fromkeys([s for s in out if s != source]))


def _fix_range_end_plus_one(source):
    """Expand a range upper bound by one for inclusive iteration bugs."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2:
                end = node.args[1]
                s, e = _span(source, end)
                out.append(source[:s] + source[s:e] + " + 1" + source[e:])
    return list(dict.fromkeys([s for s in out if s != source]))


class Fixer:
    def rules(self):
        return [
            Rule(
                name="binary_search_upper_bound_too_small",
                apply=_fix_upper_bound_100_to_m,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="binary_search_lower_bound_zero",
                apply=_fix_zero_start_binary_search,
                symptoms=("wrong",),
            ),
            Rule(
                name="accumulator_not_reset_each_iteration",
                apply=_fix_accumulator_reinit_inside_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="feasibility_check_wrong_variable",
                apply=_fix_if_k_less_n_to_m_less_n,
                symptoms=("wrong",),
            ),
            Rule(
                name="inclusive_range_needs_plus_one",
                apply=_fix_range_end_plus_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="reset_accumulator_or_loop_body_slip",
                apply=_fix_missing_reset_accumulator,
                symptoms=("wrong",),
            ),
        ]