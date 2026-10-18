"""
Repair module for the "Measuring Lengths in Baden" assignment.

Targets recurring misconceptions seen in buggy submissions that convert
centimeters to feet/inches (with 1 inch = 3 cm, 1 foot = 12 inches):

 - rounding an inch-remainder up to 12 without carrying it into an extra foot
 - computing the inch remainder from the *full* input instead of the
   remainder left after removing whole feet
 - rounding feet directly (e.g. int(n/36 + 0.5)) instead of rounding total
   inches first and then splitting into feet/inches
 - printing a single combined float instead of two integers
 - adding the remainder itself instead of adding 1 when rounding up
 - comparing a function's own name instead of its parameter
"""

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


def _find_enclosing_expr_stmt(tree, call_node):
    for cand in ast.walk(tree):
        if isinstance(cand, ast.Expr) and cand.value is call_node:
            return cand
    return None


# ---------------------------------------------------------------------------
# Rule A: feet computed first (n // 36), inch computed from a remainder that
# can round up to 12 inches without carrying into an extra foot.
# ---------------------------------------------------------------------------

def _extract_feet_inch(call):
    args = call.args
    if len(args) == 2:
        return args[0], args[1]
    if len(args) == 3 and isinstance(args[1], ast.Constant) and isinstance(args[1].value, str):
        return args[0], args[2]
    if len(args) == 1:
        a0 = args[0]
        if (isinstance(a0, ast.Call) and isinstance(a0.func, ast.Attribute)
                and a0.func.attr == 'format' and len(a0.args) == 2):
            return a0.args[0], a0.args[1]
        if isinstance(a0, ast.JoinedStr):
            vals = [v.value for v in a0.values if isinstance(v, ast.FormattedValue)]
            if len(vals) == 2:
                return vals[0], vals[1]
        collected = []

        def walk(n):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                walk(n.left)
                walk(n.right)
            elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == 'str' and len(n.args) == 1):
                collected.append(n.args[0])

        walk(a0)
        if len(collected) == 2:
            return collected[0], collected[1]
    return None


def _carry_over_before_output(source):
    """Add an explicit carry into feet whenever the printed inch value hits 12."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
            res = _extract_feet_inch(node)
            if res is None:
                continue
            feet_expr, inch_expr = res
            stmt = _find_enclosing_expr_stmt(tree, node)
            if stmt is None:
                continue
            fs, fe = _span(source, feet_expr)
            is_, ie = _span(source, inch_expr)
            if fs == is_ and fe == ie:
                continue
            edits = sorted([(fs, fe, "__ft"), (is_, ie, "__in")], key=lambda t: t[0], reverse=True)
            new_src = source
            for s0, e0, rep in edits:
                new_src = new_src[:s0] + rep + new_src[e0:]
            s_stmt, _e = _span(source, stmt)
            indent = ' ' * stmt.col_offset
            feet_src = source[fs:fe]
            inch_src = source[is_:ie]
            insert_text = (
                f"__ft, __in = ({feet_src}), ({inch_src})\n"
                f"{indent}if __in >= 12:\n"
                f"{indent}    __ft += 1\n"
                f"{indent}    __in -= 12\n"
                f"{indent}"
            )
            candidate = new_src[:s_stmt] + insert_text + new_src[s_stmt:]
            if candidate != source:
                out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule B: inch value is computed from the *full* input (round(n/3)) instead
# of the remainder left after taking out whole feet (n // 36).
# ---------------------------------------------------------------------------

def _match_div36_name(val):
    if (isinstance(val, ast.BinOp) and isinstance(val.op, ast.FloorDiv)
            and isinstance(val.right, ast.Constant) and val.right.value == 36
            and isinstance(val.left, ast.Name)):
        return val.left.id
    if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == 'int' and len(val.args) == 1:
        arg = val.args[0]
        if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div)
                and isinstance(arg.right, ast.Constant) and arg.right.value == 36
                and isinstance(arg.left, ast.Name)):
            return arg.left.id
    return None


def _find_direct_div3(val, base_name):
    for node in ast.walk(val):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv))
                and isinstance(node.right, ast.Constant) and node.right.value == 3
                and isinstance(node.left, ast.Name) and node.left.id == base_name):
            return node.left
    return None


def _fix_inch_uses_full_base(source):
    """Replace a bare `base` used in a /3 inch computation with `(base % 36)`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for container in ast.walk(tree):
        body = getattr(container, 'body', None)
        if not isinstance(body, list):
            continue
        feet_base = None
        for stmt in body:
            if feet_base is not None:
                if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == feet_base:
                    feet_base = None
                elif isinstance(stmt, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == feet_base for t in stmt.targets):
                    feet_base = None
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                base = _match_div36_name(stmt.value)
                if base:
                    feet_base = base
                    continue
                if feet_base:
                    tnode = _find_direct_div3(stmt.value, feet_base)
                    if tnode is not None:
                        candidate = _splice(source, tnode, f"({feet_base} % 36)")
                        if candidate != source:
                            out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule C: feet is rounded directly from base/36 (int(base/36+0.5)), then the
# inch remainder is rounded too, instead of rounding total inches first.
# ---------------------------------------------------------------------------

def _match_round_half(val, denom):
    if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == 'int' and len(val.args) == 1:
        arg = val.args[0]
        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
            left, right = arg.left, arg.right
            if isinstance(right, ast.Constant) and isinstance(right.value, (int, float)) and abs(right.value - 0.5) < 1e-9:
                if (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Div)
                        and isinstance(left.right, ast.Constant) and left.right.value == denom):
                    return left.left
    return None


def _fix_round_half_foot_first(source):
    """Reorder: round total inches from the base first, then split by 12."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for container in ast.walk(tree):
        body = getattr(container, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 2):
            s1, s2, s3 = body[i], body[i + 1], body[i + 2]
            if not (isinstance(s1, ast.Assign) and len(s1.targets) == 1 and isinstance(s1.targets[0], ast.Name)):
                continue
            feet_name = s1.targets[0].id
            base_node = _match_round_half(s1.value, 36)
            if base_node is None:
                continue
            if not (isinstance(s2, ast.Assign) and len(s2.targets) == 1 and isinstance(s2.targets[0], ast.Name)):
                continue
            r_name = s2.targets[0].id
            v2 = s2.value
            if not (isinstance(v2, ast.BinOp) and isinstance(v2.op, ast.Sub)):
                continue
            if not (isinstance(v2.right, ast.BinOp) and isinstance(v2.right.op, ast.Mult)):
                continue
            mult = v2.right
            names_ok = (
                (isinstance(mult.left, ast.Constant) and mult.left.value == 36
                 and isinstance(mult.right, ast.Name) and mult.right.id == feet_name)
                or
                (isinstance(mult.right, ast.Constant) and mult.right.value == 36
                 and isinstance(mult.left, ast.Name) and mult.left.id == feet_name)
            )
            if not names_ok:
                continue
            if not (isinstance(s3, ast.Assign) and len(s3.targets) == 1 and isinstance(s3.targets[0], ast.Name)):
                continue
            inch_name = s3.targets[0].id
            base_node3 = _match_round_half(s3.value, 3)
            if base_node3 is None or not (isinstance(base_node3, ast.Name) and base_node3.id == r_name):
                continue

            bs, be = _span(source, base_node)
            base_src = source[bs:be]
            s_start, _s = _span(source, s1)
            _e, s_end = _span(source, s3)
            indent = ' ' * s1.col_offset
            new_block = (
                f"__total = int({base_src} / 3 + 0.5)\n"
                f"{indent}{feet_name} = __total // 12\n"
                f"{indent}{inch_name} = __total % 12\n"
                f"{indent}{r_name} = {inch_name}"
            )
            candidate = source[:s_start] + new_block + source[s_end:]
            if candidate != source:
                out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule D: the whole answer is printed as one combined float sum instead of
# two separate integers.
# ---------------------------------------------------------------------------

def _fix_print_single_sum(source):
    """print(A + B) -> split into feet/inches with a carry check."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
            if len(node.args) == 1 and isinstance(node.args[0], ast.BinOp) and isinstance(node.args[0].op, ast.Add):
                stmt = _find_enclosing_expr_stmt(tree, node)
                if stmt is None:
                    continue
                left, right = node.args[0].left, node.args[0].right
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                left_src = source[ls:le]
                right_src = source[rs:re_]
                s_stmt, e_stmt = _span(source, stmt)
                indent = ' ' * stmt.col_offset
                new_block = (
                    f"__ft, __in = ({left_src}), round({right_src})\n"
                    f"{indent}if __in >= 12:\n"
                    f"{indent}    __ft += 1\n"
                    f"{indent}    __in -= 12\n"
                    f"{indent}print(__ft, __in)"
                )
                candidate = source[:s_stmt] + new_block + source[e_stmt:]
                if candidate != source:
                    out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule E: when rounding up, the *remainder itself* is added instead of 1.
# ---------------------------------------------------------------------------

def _fix_add_remainder_not_one(source):
    """`x // 3 + x % 3` should round up by 1, not by the remainder value."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
            right = node.value.right
            if (isinstance(right, ast.BinOp) and isinstance(right.op, ast.Mod)
                    and isinstance(right.right, ast.Constant) and right.right.value == 3):
                candidate = _splice(source, right, "1")
                if candidate != source:
                    out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule F: a helper function compares its own name instead of its parameter.
# ---------------------------------------------------------------------------

def _fix_selfname_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            params = [a.arg for a in node.args.args]
            if not params:
                continue
            fname = node.name
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and isinstance(sub.left, ast.Name) and sub.left.id == fname:
                    candidate = _splice(source, sub.left, params[0])
                    if candidate != source:
                        out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Generic cheap slip: relax a strict '<' to '<='.
# ---------------------------------------------------------------------------

def _lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
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
                name="carry_over_before_output",
                apply=_carry_over_before_output,
                symptoms=("wrong",),
            ),
            Rule(
                name="inch_from_full_base_not_remainder",
                apply=_fix_inch_uses_full_base,
                symptoms=("wrong",),
            ),
            Rule(
                name="round_half_applied_at_foot_level",
                apply=_fix_round_half_foot_first,
                symptoms=("wrong",),
            ),
            Rule(
                name="print_single_combined_expr",
                apply=_fix_print_single_sum,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_rounding_addend_uses_remainder",
                apply=_fix_add_remainder_not_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="selfname_compare_bug",
                apply=_fix_selfname_compare,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]