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


def _line_span(source, node):
    """Full-line span (start of first line to end of last line, incl. newline)."""
    lines = source.splitlines(keepends=True)
    start_line = node.lineno - 1
    end_line = node.end_lineno - 1
    s = sum(len(l) for l in lines[:start_line])
    e = sum(len(l) for l in lines[:end_line + 1])
    return s, e


def _flip_lt_le(source):
    """Flip strict/non-strict comparisons (Lt<->LtE, Gt<->GtE) one at a time."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        op = node.ops[0]
        if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            left = node.left
            right = node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            if isinstance(op, ast.Lt):
                new_op = "<="
            elif isinstance(op, ast.LtE):
                new_op = "<"
            elif isinstance(op, ast.Gt):
                new_op = ">="
            else:
                new_op = ">"
            new_cmp = source[ls:le] + " " + new_op + " " + source[rs:re_]
            candidate = _splice(source, node, new_cmp)
            if candidate != source:
                out.append(candidate)
    return out


def _return_none_to_zero(source):
    """Replace `return None` with `return 0` (empty-sequence handling)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) \
                and node.value.value is None:
            candidate = _splice(source, node, "return 0")
            if candidate != source:
                out.append(candidate)
    return out


def _bare_return_to_break(source):
    """Replace a value-less `return` used inside a loop with `break`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    loop_nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
    for loop in loop_nodes:
        for node in ast.walk(loop):
            if node is loop:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(node, ast.Return) and node.value is None:
                candidate = _splice(source, node, "break")
                if candidate != source:
                    out.append(candidate)
    return out


def _dedent_trailing_loop_return(source):
    """A statement after an if-return inside a for-loop that should run only
    after the loop finishes, but is mistakenly left indented inside the loop
    body (executes every iteration instead of only once at the end)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if len(node.body) < 2:
            continue
        last = node.body[-1]
        if not isinstance(last, ast.Return):
            continue
        if last.col_offset <= node.col_offset:
            continue
        s, e = _line_span(source, last)
        stmt_text = source[s:e]
        stripped = stmt_text.lstrip(" \t")
        indent = " " * node.col_offset
        if not stripped.endswith("\n"):
            stripped += "\n"
        new_text = indent + stripped
        candidate = source[:s] + new_text + source[e:]
        if candidate != source:
            out.append(candidate)
    return out


def _add_missing_final_return(source):
    """Insert `return 0` after a trailing for-loop that can fall through
    without returning (function silently returns None)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.body:
            continue
        last = node.body[-1]
        if not isinstance(last, ast.For):
            continue
        has_return_in_loop_top = any(
            isinstance(s, ast.Return) for s in ast.walk(last)
        )
        if not has_return_in_loop_top:
            continue
        s, e = _line_span(source, last)
        indent = " " * last.col_offset
        tail = source[e:]
        if tail.lstrip().startswith("return"):
            continue
        insertion = indent + "return 0\n"
        candidate = source[:e] + insertion + source[e:]
        if candidate != source:
            out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="dedent_trailing_loop_return",
                apply=_dedent_trailing_loop_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_none_to_zero",
                apply=_return_none_to_zero,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="bare_return_to_break",
                apply=_bare_return_to_break,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="add_missing_final_return",
                apply=_add_missing_final_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="flip_lt_le_gt_ge",
                apply=_flip_lt_le,
                symptoms=("wrong", "err:IndexError"),
            ),
        ]