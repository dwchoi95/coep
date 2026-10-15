import ast
import re

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


def _replace_spans(source, replacements):
    for s, e, t in sorted(replacements, key=lambda x: -x[0]):
        source = source[:s] + t + source[e:]
    return source


def _insert_before_stmt(source, stmt_node, lines):
    s, _e = _span(source, stmt_node)
    line_start = source.rfind('\n', 0, s) + 1
    indent = source[line_start:s]
    insertion = "".join(indent + ln + "\n" for ln in lines)
    return source[:line_start] + insertion + source[line_start:]


def _find_print_candidates(tree):
    """Module-level (not inside def/class) `print(...)` statements."""
    found = []

    def walk(body):
        for node in body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == 'print':
                    found.append(node)
            if isinstance(node, (ast.If, ast.For, ast.While)):
                walk(node.body)
                walk(node.orelse)

    walk(tree.body)
    return found


def _extract_two_exprs(call):
    """Try to find the two 'value' sub-expressions (feet-like, inch-like)
    embedded in a print call, regardless of formatting style."""
    if len(call.args) == 2:
        return call.args[0], call.args[1]
    if len(call.args) == 1:
        arg = call.args[0]
        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) \
           and arg.func.attr == 'format' and len(arg.args) == 2:
            return arg.args[0], arg.args[1]
        if isinstance(arg, ast.JoinedStr):
            fvs = [v for v in arg.values if isinstance(v, ast.FormattedValue)]
            if len(fvs) == 2:
                return fvs[0].value, fvs[1].value
        if isinstance(arg, ast.BinOp):
            calls = [n for n in ast.walk(arg)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                     and n.func.id == 'str' and len(n.args) == 1]
            if len(calls) == 2:
                calls.sort(key=lambda n: (n.lineno, n.col_offset))
                return calls[0].args[0], calls[1].args[0]
    return None, None


def _carry_fix(source):
    """Insert an inch->foot carry check before the final two-value print,
    fixing the 'compute feet first, round remainder second' misconception
    (which can produce an inch value of 12)."""
    if '_a, _b =' in source:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    candidates = _find_print_candidates(tree)
    if not candidates:
        return []
    stmt = candidates[-1]
    call = stmt.value
    e1, e2 = _extract_two_exprs(call)
    if e1 is None or e2 is None:
        return []
    s1, en1 = _span(source, e1)
    s2, en2 = _span(source, e2)
    if s1 == s2:
        return []
    e1_text = source[s1:en1]
    e2_text = source[s2:en2]
    new_src = _replace_spans(source, [(s1, en1, "_a"), (s2, en2, "_b")])
    lines = [
        "_a, _b = (%s), (%s)" % (e1_text, e2_text),
        "if _b >= 12:",
        "    _a += _b // 12",
        "    _b %= 12",
    ]
    result = _insert_before_stmt(new_src, stmt, lines)
    if result == source:
        return []
    return [result]


def _missing_round(source):
    """A bare `X // 3` used directly as a printed value, with no rounding
    logic (comparison to 2 mod 3) present anywhere in the program."""
    if re.search(r'%\s*3\s*(==|>=)\s*2', source):
        return []
    if 'round(' in source or 'ceil(' in source:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    candidates = _find_print_candidates(tree)
    out = []
    for stmt in candidates:
        call = stmt.value
        e1, e2 = _extract_two_exprs(call)
        for e in (e1, e2):
            if e is None:
                continue
            if isinstance(e, ast.BinOp) and isinstance(e.op, ast.FloorDiv) \
               and isinstance(e.right, ast.Constant) and e.right.value == 3:
                num_s, num_e = _span(source, e.left)
                numer = source[num_s:num_e]
                replacement = "(%s // 3 + (1 if %s %% 3 == 2 else 0))" % (numer, numer)
                out.append(_splice(source, e, replacement))
    return out


def _typo_mod26_to_36(source):
    """`X % 26` (or `X // 26`) is almost certainly a mistyped 36 in this
    feet/inch domain."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.FloorDiv)):
            right = node.right
            if isinstance(right, ast.Constant) and right.value == 26:
                s, e = _span(source, right)
                out.append(source[:s] + "36" + source[e:])
    return out


def _plus2_to_plus1_div3(source):
    """`(X + 2) // 3` should be `(X + 1) // 3` for round-to-nearest-inch."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv) \
           and isinstance(node.right, ast.Constant) and node.right.value == 3:
            left = node.left
            if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add):
                r = left.right
                if isinstance(r, ast.Constant) and r.value == 2:
                    s, e = _span(source, r)
                    out.append(source[:s] + "1" + source[e:])
    return out


def _remainder_added_instead_of_one(source):
    """`X // 3 + X % 3` should be `X // 3 + 1` (only a flat +1 rounds up)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = node.left, node.right
            if isinstance(left, ast.BinOp) and isinstance(left.op, ast.FloorDiv) \
               and isinstance(left.right, ast.Constant) and left.right.value == 3 \
               and isinstance(right, ast.BinOp) and isinstance(right.op, ast.Mod) \
               and isinstance(right.right, ast.Constant) and right.right.value == 3:
                ls, le = _span(source, left.left)
                rs, re_ = _span(source, right.left)
                if source[ls:le].strip() == source[rs:re_].strip():
                    new_text = source[ls:le] + " // 3 + 1"
                    out.append(_splice(source, node, new_text))
    return out


def _ceil_div3_wrong_rounding(source):
    """`ceil(X / 3)` over-rounds (e.g. remainder 1cm should stay 0 inches);
    replace with the domain's actual round-up-only-on-remainder-2 rule."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_ceil = (isinstance(func, ast.Name) and func.id == 'ceil') or \
                  (isinstance(func, ast.Attribute) and func.attr == 'ceil')
        if not is_ceil or len(node.args) != 1:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div) \
           and isinstance(arg.right, ast.Constant) and arg.right.value == 3:
            num_s, num_e = _span(source, arg.left)
            numer = source[num_s:num_e]
            replacement = "(%s // 3 + (1 if %s %% 3 == 2 else 0))" % (numer, numer)
            out.append(_splice(source, node, replacement))
    return out


def _fix_single_expr_sum_print(source):
    """print(X//36 + (X%36)/3) never splits feet/inches nor rounds."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'print' and len(node.args) == 1):
            continue
        arg = node.args[0]
        if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)):
            continue
        left, right = arg.left, arg.right
        if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.FloorDiv)
                and isinstance(left.right, ast.Constant) and left.right.value == 36):
            continue
        if not (isinstance(right, ast.BinOp) and isinstance(right.op, ast.Div)
                and isinstance(right.right, ast.Constant) and right.right.value == 3):
            continue
        rem = right.left
        if not (isinstance(rem, ast.BinOp) and isinstance(rem.op, ast.Mod)
                and isinstance(rem.right, ast.Constant) and rem.right.value == 36):
            continue
        xs, xe = _span(source, left.left)
        xtext = source[xs:xe]
        rem_s, rem_e = _span(source, rem)
        rem_text = source[rem_s:rem_e]
        inch_expr = "((%s) // 3 + (1 if (%s) %% 3 == 2 else 0))" % (rem_text, rem_text)
        new_args = "%s // 36 + %s // 12, %s %% 12" % (xtext, inch_expr, inch_expr)
        out.append(_splice(source, node, "print(%s)" % new_args))
    return out


def _half_foot_threshold_removal(source):
    """Detects `if remainder % 36 >= ~18: <round whole foot>` guarding a
    correct else-branch; the threshold-based whole-foot rounding is wrong,
    only the else branch's per-inch logic is right."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and node.orelse):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Gt, ast.GtE))):
            continue
        left = test.left
        comp = test.comparators[0]
        if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod)
                and isinstance(left.right, ast.Constant) and left.right.value == 36):
            continue
        if not isinstance(comp, ast.Constant):
            continue
        thresh = comp.value
        if not (isinstance(thresh, (int, float)) and 17 <= thresh <= 19):
            continue
        s, e = _span(source, node)
        indent = source[source.rfind('\n', 0, s) + 1:s]
        parts = []
        for st in node.orelse:
            ss, ee = _span(source, st)
            parts.append(source[ss:ee])
        new_text = ("\n" + indent).join(parts)
        out.append(_splice(source, node, new_text))
    return out


def _self_name_instead_of_param(source):
    """A helper function erroneously compares its own name (instead of its
    parameter) inside its body, e.g. `if roundI == 1:` inside def roundI(inch)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    call_funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            call_funcs.add(id(node.func))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        fname = node.name
        params = [a.arg for a in node.args.args]
        if not params:
            continue
        first_param = params[0]
        for inner in ast.walk(node):
            if isinstance(inner, ast.Name) and inner.id == fname \
               and inner.id != first_param and id(inner) not in call_funcs:
                s, e = _span(source, inner)
                out.append(source[:s] + first_param + source[e:])
    return out


def _eq_to_le_small_const(source):
    """Generic slip: `X == k` (k small int) may need to be `X <= k`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Eq):
            comp = node.comparators[0]
            if isinstance(comp, ast.Constant) and isinstance(comp.value, int) \
               and 0 <= comp.value <= 2:
                left = node.left
                ls, le = _span(source, left)
                rs, re_ = _span(source, comp)
                new_cmp = source[ls:le] + " <= " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="carry_fix_two_value_print",
                apply=_carry_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_round_bare_floordiv3",
                apply=_missing_round,
                symptoms=("wrong",),
            ),
            Rule(
                name="typo_mod26_to_36",
                apply=_typo_mod26_to_36,
                symptoms=("wrong",),
            ),
            Rule(
                name="plus2_to_plus1_before_div3",
                apply=_plus2_to_plus1_div3,
                symptoms=("wrong",),
            ),
            Rule(
                name="remainder_added_instead_of_one",
                apply=_remainder_added_instead_of_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="ceil_div3_wrong_rounding",
                apply=_ceil_div3_wrong_rounding,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_single_expr_sum_print",
                apply=_fix_single_expr_sum_print,
                symptoms=("wrong",),
            ),
            Rule(
                name="half_foot_threshold_removal",
                apply=_half_foot_threshold_removal,
                symptoms=("wrong",),
            ),
            Rule(
                name="self_name_instead_of_param",
                apply=_self_name_instead_of_param,
                symptoms=("wrong",),
            ),
            Rule(
                name="eq_to_le_small_const",
                apply=_eq_to_le_small_const,
                symptoms=("wrong",),
            ),
        ]