import ast

from src.core.repair import Rule


def _span(source, node):
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


def _bump_binary_search_bound(source):
    """A too-small upper bound for a binary search (e.g. r = 100) prevents
    the search from ever reaching the true optimum near that bound.
    Bump small integer literal upper bounds to a safely large constant."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    bound_names = {"r", "end", "hi", "right", "high", "R", "HI"}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in bound_names
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, int)
                and not isinstance(node.value.value, bool)):
            val = node.value.value
            if 0 < val <= 1000:
                s, e = _span(source, node.value)
                candidate = source[:s] + "100000" + source[e:]
                if candidate != source:
                    out.append(candidate)
    return out


def _stmt_lists(tree):
    seen = []
    for node in ast.walk(tree):
        for field, value in ast.iter_fields(node):
            if isinstance(value, list) and value and all(
                    isinstance(v, ast.stmt) for v in value):
                seen.append(value)
    return seen


def _move_accumulator_reset_inside_loop(source):
    """A reset of an accumulator (like `s = 0`) placed *before* an outer
    loop instead of inside it, causing the accumulated count to carry over
    between outer-loop iterations. Move the reset to be the first statement
    inside the outer loop's body, right before the inner accumulation loop."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))

    for stmts in _stmt_lists(tree):
        for idx, node in enumerate(stmts):
            if not (isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                continue
            var = node.targets[0].id
            if not (isinstance(node.value, ast.Constant)
                    and node.value.value == 0
                    and not isinstance(node.value.value, bool)):
                continue
            if idx + 1 >= len(stmts) or not isinstance(stmts[idx + 1], ast.For):
                continue
            outer = stmts[idx + 1]

            inner_for = None
            for stmt in outer.body:
                if isinstance(stmt, ast.For):
                    inner_for = stmt
                    break
            if inner_for is None:
                continue

            accum = any(
                isinstance(s, ast.AugAssign)
                and isinstance(s.target, ast.Name)
                and s.target.id == var
                for s in inner_for.body
            )
            if not accum:
                continue

            assign_line_start = starts[node.lineno - 1]
            assign_line_end = starts[node.end_lineno]
            insertion_offset = starts[inner_for.lineno - 1]

            if insertion_offset < assign_line_end:
                continue

            indent = " " * inner_for.col_offset
            insertion_text = f"{indent}{var} = 0\n"

            new_source = (
                source[:assign_line_start]
                + source[assign_line_end:insertion_offset]
                + insertion_text
                + source[insertion_offset:]
            )
            if new_source != source:
                out.append(new_source)
    return out


def _relax_threshold_comparison(source):
    """A strict/non-strict flip on the feasibility-count threshold check
    (e.g. `k > n` instead of `k >= n`), which shifts the computed answer
    by one. Toggle between Gt/GtE for comparisons against a bare name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    flips = {
        ast.Gt: ("GtE", " >= "),
        ast.GtE: ("Gt", " > "),
        ast.Lt: ("LtE", " <= "),
        ast.LtE: ("Lt", " < "),
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            t = type(op)
            if t in flips:
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                _, sep = flips[t]
                new_cmp = source[ls:le] + sep + source[rs:re_]
                candidate = _splice(source, node, new_cmp)
                if candidate != source:
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="bump_binary_search_upper_bound",
                apply=_bump_binary_search_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="move_accumulator_reset_inside_outer_loop",
                apply=_move_accumulator_reset_inside_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="relax_threshold_comparison",
                apply=_relax_threshold_comparison,
                symptoms=("wrong",),
            ),
        ]