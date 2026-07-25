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


def _fix_rounding_constant(source):
    """Repair `(x + k) // 3` where k should be 1 (rounding cm to inch)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv)):
            continue
        right = node.right
        if not (isinstance(right, ast.Constant) and right.value == 3):
            continue
        left = node.left
        if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add)):
            continue
        for side in (left.left, left.right):
            if isinstance(side, ast.Constant) and isinstance(side.value, int) \
               and side.value != 1:
                candidate = _splice(source, side, "1")
                if candidate != source:
                    out.append(candidate)
    return out


def _find_assign_name_via_op(body, opcls):
    """Find an Assign stmt in `body` whose value is a BinOp with op `opcls`
    and whose target is a single Name; return (index, name) or None."""
    for i, stmt in enumerate(body):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
           and isinstance(stmt.targets[0], ast.Name) \
           and isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, opcls):
            return i, stmt.targets[0].id, stmt
    return None


def _fix_missing_inch_wraparound(source):
    """Insert the missing `if inch == 12: feet += 1; inch = 0` wraparound
    after a rounded inch computation like `ic = round(rem/3)`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    blocks = []
    for node in ast.walk(tree):
        if hasattr(node, "body") and isinstance(getattr(node, "body"), list):
            blocks.append(node.body)

    for body in blocks:
        for i, stmt in enumerate(body):
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            val = stmt.value
            is_round_div = (isinstance(val, ast.Call)
                             and isinstance(val.func, ast.Name)
                             and val.func.id == "round"
                             and len(val.args) == 1
                             and isinstance(val.args[0], ast.BinOp)
                             and isinstance(val.args[0].op, ast.Div))
            if not is_round_div:
                continue
            inch_name = stmt.targets[0].id

            feet_name = None
            for j in range(i - 1, -1, -1):
                prev = body[j]
                if isinstance(prev, ast.Assign) and len(prev.targets) == 1 \
                   and isinstance(prev.targets[0], ast.Name) \
                   and isinstance(prev.value, ast.BinOp) \
                   and isinstance(prev.value.op, ast.FloorDiv) \
                   and prev.targets[0].id != inch_name:
                    feet_name = prev.targets[0].id
                    break
            if feet_name is None:
                continue

            already_guarded = False
            if i + 1 < len(body):
                nxt = body[i + 1]
                if isinstance(nxt, ast.If):
                    test = nxt.test
                    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) \
                       and test.left.id == inch_name:
                        already_guarded = True
            if already_guarded:
                continue

            s, e = _span(source, stmt)
            indent = " " * stmt.col_offset
            insert_at = e
            if insert_at < len(source) and source[insert_at] == "\n":
                insert_at += 1
            new_block = (
                f"{indent}if {inch_name} == 12:\n"
                f"{indent}    {feet_name} += 1\n"
                f"{indent}    {inch_name} = 0\n"
            )
            candidate = source[:insert_at] + new_block + source[insert_at:]
            if candidate != source:
                out.append(candidate)
    return out


def _lt_to_le(source):
    """Generic slip: relax a strict comparison to non-strict."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            candidate = _splice(source, node, new_cmp)
            if candidate != source:
                out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_rounding_constant_plus_one",
                apply=_fix_rounding_constant,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_missing_inch_wraparound_after_round",
                apply=_fix_missing_inch_wraparound,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]