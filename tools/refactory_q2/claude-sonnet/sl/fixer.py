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


_NAME_GROUPS = [
    {"day", "date"},
    {"month", "months"},
]


def _fix_param_name_mismatch(source):
    """A parameter is named e.g. 'date' but the body refers to the undefined
    sibling name 'day' (or vice versa), causing a NameError. Rename the
    stray Name-loads inside that function to match the actual parameter."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    edits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        args = node.args.args
        if not args:
            continue
        first = args[0].arg
        group = None
        for g in _NAME_GROUPS:
            if first in g:
                group = g
                break
        if group is None:
            continue

        assigned = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                assigned.add(n.id)
        for a in args:
            assigned.discard(a.arg)

        for n in ast.walk(node):
            if (
                isinstance(n, ast.Name)
                and isinstance(n.ctx, ast.Load)
                and n.id in group
                and n.id != first
                and n.id not in assigned
            ):
                s, e = _span(source, n)
                edits.append((s, e, first))

    if not edits:
        return []

    edits.sort(key=lambda t: t[0], reverse=True)
    out = source
    for s, e, rep in edits:
        out = out[:s] + rep + out[e:]
    return [out]


def _add_missing_return_false(source):
    """A function's body ends with `if cond: return True` (no else, no
    trailing return), so the false path implicitly returns None instead of
    False. Insert an explicit `return False` after the if-block."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        body = node.body
        if not body:
            continue
        last = body[-1]
        if not isinstance(last, ast.If) or last.orelse:
            continue

        has_return = any(isinstance(s, ast.Return) for s in ast.walk(last))
        if not has_return:
            continue

        indent = " " * last.col_offset
        _, e = _span(source, last)
        candidate = source[:e] + "\n" + indent + "return False" + source[e:]
        out.append(candidate)
    return out


def _lt_to_le(source):
    """Relax a strict comparison to non-strict (generic off-by-one slip)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Lt)
        ):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


def _eq_to_neq_flip(source):
    """Generic slip: an == comparison that should be != (or vice versa) in
    a counting loop condition."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " != " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_param_name_mismatch",
                apply=_fix_param_name_mismatch,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="add_missing_return_false",
                apply=_add_missing_return_false,
                symptoms=("wrong",),
            ),
            Rule(
                name="lt_to_le",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="eq_to_neq_flip",
                apply=_eq_to_neq_flip,
                symptoms=("wrong",),
            ),
        ]