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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source)
        except Exception:
            return []
    wrapped.__name__ = getattr(fn, "__name__", "rule")
    return wrapped


# ---------------------------------------------------------------------------
# Rule: function uses "si"/"no" (or other non-standard literals) in a print
# ternary instead of "YES"/"NO".
# ---------------------------------------------------------------------------
def _fix_ternary_strings(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            for arg in node.args:
                if (isinstance(arg, ast.IfExp)
                        and isinstance(arg.body, ast.Constant) and isinstance(arg.body.value, str)
                        and isinstance(arg.orelse, ast.Constant) and isinstance(arg.orelse.value, str)):
                    if arg.body.value == "YES" and arg.orelse.value == "NO":
                        continue
                    bs, be = _span(source, arg.body)
                    os_, oe = _span(source, arg.orelse)
                    new_source = source[:os_] + '"NO"' + source[oe:]
                    new_source = new_source[:bs] + '"YES"' + new_source[be:]
                    if new_source != source:
                        out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule: digit-check loop stores the increment into an undefined name while a
# properly initialized ("x = 0") counter sits unused nearby.
# ---------------------------------------------------------------------------
def _fix_undefined_counter(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    stores = []
    zero_inits = []
    increments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            pos = (node.lineno, node.col_offset)
            if isinstance(node.value, ast.Constant) and node.value.value == 0:
                zero_inits.append((name, pos))
            if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                l, r = node.value.left, node.value.right
                if isinstance(l, ast.Name) and l.id == name and isinstance(r, ast.Constant) and r.value == 1:
                    increments.append((name, pos))
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
            if isinstance(node.value, ast.Constant) and node.value.value == 1:
                increments.append((node.target.id, (node.lineno, node.col_offset)))
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            stores.append((node.id, (node.lineno, node.col_offset)))

    undefined = []
    for name, pos in increments:
        earlier = [p for (n, p) in stores if n == name and p < pos]
        if not earlier:
            undefined.append((name, pos))

    orphans = []
    for name, pos in zero_inits:
        later = [p for (n, p) in stores if n == name and p > pos]
        if not later:
            orphans.append((name, pos))

    out = []
    if len(undefined) == 1 and len(orphans) == 1:
        bad_name, bad_pos = undefined[0]
        good_name, good_pos = orphans[0]
        if good_pos < bad_pos and good_name != bad_name:
            pattern = re.compile(r"\b" + re.escape(bad_name) + r"\b")
            new_source = pattern.sub(good_name, source)
            if new_source != source:
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule: `X % 4 == 0 or X % 7 == 0` used instead of `X == 4 or X == 7`.
# ---------------------------------------------------------------------------
def _fix_mod_zero_equality(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    replacements = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            info = []
            ok = True
            for c in (a, b):
                if (isinstance(c, ast.Compare) and len(c.ops) == 1 and isinstance(c.ops[0], ast.Eq)
                        and isinstance(c.left, ast.BinOp) and isinstance(c.left.op, ast.Mod)
                        and isinstance(c.left.right, ast.Constant) and c.left.right.value in (4, 7)
                        and isinstance(c.comparators[0], ast.Constant) and c.comparators[0].value == 0):
                    info.append((c.left.left, c.left.right.value))
                else:
                    ok = False
                    break
            if ok and len(info) == 2 and {info[0][1], info[1][1]} == {4, 7}:
                t1 = _text(source, info[0][0]).strip()
                t2 = _text(source, info[1][0]).strip()
                if t1 == t2:
                    replacements.append((node, f"{t1} == 4 or {t1} == 7"))
    if not replacements:
        return []
    spans = [(_span(source, n), t) for n, t in replacements]
    spans.sort(key=lambda x: -x[0][0])
    new_source = source
    for (s, e), t in spans:
        new_source = new_source[:s] + t + new_source[e:]
    return [new_source] if new_source != source else []


# ---------------------------------------------------------------------------
# Rule: `count == 4 or 7` (bare truthy literal) instead of `count == 4 or count == 7`.
# ---------------------------------------------------------------------------
def _fix_truthy_or_literal(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            cmp_node = lit_node = None
            if isinstance(a, ast.Compare) and isinstance(b, ast.Constant):
                cmp_node, lit_node = a, b
            elif isinstance(b, ast.Compare) and isinstance(a, ast.Constant):
                cmp_node, lit_node = b, a
            if cmp_node is not None and len(cmp_node.ops) == 1 and isinstance(cmp_node.ops[0], ast.Eq):
                if isinstance(lit_node.value, int) and lit_node.value in (4, 7):
                    other = cmp_node.comparators[0]
                    if isinstance(other, ast.Constant) and other.value in (4, 7) and other.value != lit_node.value:
                        left_text = _text(source, cmp_node.left)
                        new_text = f"{left_text} == {other.value} or {left_text} == {lit_node.value}"
                        cand = _splice(source, node, new_text)
                        if cand != source:
                            out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule: float division (`/=`, `x = x/10`) used for digit stripping.
# ---------------------------------------------------------------------------
def _fix_float_div(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
            s, e = _span(source, node)
            text = source[s:e]
            if "/=" in text and "//=" not in text:
                new_text = text.replace("/=", "//=", 1)
                cand = source[:s] + new_text + source[e:]
                if cand != source:
                    out.append(cand)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            tgt = node.targets[0].id
            val = node.value
            if (isinstance(val, ast.BinOp) and isinstance(val.op, ast.Div)
                    and isinstance(val.left, ast.Name) and val.left.id == tgt):
                vs, ve = _span(source, val)
                text = source[vs:ve]
                idx = text.find("/")
                if idx != -1 and (idx == len(text) - 1 or text[idx + 1] != "/"):
                    new_text = text[:idx] + "//" + text[idx + 1:]
                    cand = source[:vs] + new_text + source[ve:]
                    if cand != source:
                        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule: `for i in range(len(seq)): if '4' in seq or '7' in seq:` should index
# seq[i] rather than testing membership on the whole sequence each time.
# ---------------------------------------------------------------------------
def _fix_range_len_membership(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            idx = node.target.id
            it = node.iter
            if (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"
                    and len(it.args) == 1):
                arg = it.args[0]
                if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "len"
                        and len(arg.args) == 1 and isinstance(arg.args[0], ast.Name)):
                    seq = arg.args[0].id
                    for stmt in ast.walk(node):
                        if (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.BoolOp)
                                and isinstance(stmt.test.op, ast.Or) and len(stmt.test.values) == 2):
                            a, b = stmt.test.values
                            consts = []
                            ok = True
                            for c in (a, b):
                                if (isinstance(c, ast.Compare) and len(c.ops) == 1 and isinstance(c.ops[0], ast.In)
                                        and isinstance(c.left, ast.Constant)
                                        and isinstance(c.comparators[0], ast.Name) and c.comparators[0].id == seq):
                                    consts.append(c.left.value)
                                else:
                                    ok = False
                                    break
                            if ok and len(consts) == 2 and set(consts) == {"4", "7"}:
                                new_text = f"{seq}[{idx}] == {consts[0]!r} or {seq}[{idx}] == {consts[1]!r}"
                                cand = _splice(source, stmt.test, new_text)
                                if cand != source:
                                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule: `'4' in X or '7' in X` as a substitute for actually counting digits.
# ---------------------------------------------------------------------------
def _fix_membership_to_count(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            info = []
            ok = True
            for c in (a, b):
                if (isinstance(c, ast.Compare) and len(c.ops) == 1 and isinstance(c.ops[0], ast.In)
                        and isinstance(c.left, ast.Constant) and isinstance(c.left.value, str)
                        and len(c.left.value) == 1):
                    container_text = _text(source, c.comparators[0]).strip()
                    info.append((c.left.value, container_text))
                else:
                    ok = False
                    break
            if ok and len(info) == 2 and {info[0][0], info[1][0]} == {"4", "7"} and info[0][1] == info[1][1]:
                container = info[0][1]
                new_text = f"({container}.count('4') + {container}.count('7')) in (4, 7)"
                cand = _splice(source, node, new_text)
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule: a digit-stripping while loop with the step and the return nested
# inside the "lucky digit" if, instead of unconditional step + post-loop
# return.
# ---------------------------------------------------------------------------
def _fix_misplaced_step_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and len(node.body) == 1 and isinstance(node.body[0], ast.If):
            if_node = node.body[0]
            aug = None
            ret = None
            others = []
            for stmt in if_node.body:
                if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, (ast.FloorDiv, ast.Div)):
                    aug = stmt
                elif isinstance(stmt, ast.Return):
                    ret = stmt
                else:
                    others.append(stmt)
            if aug is None or ret is None or not others:
                continue
            indent_while = " " * node.col_offset
            body_indent = indent_while + "    "
            inner_indent = body_indent + "    "
            while_test_text = _text(source, node.test)
            if_test_text = _text(source, if_node.test)
            other_lines = [inner_indent + _text(source, s) for s in others]
            aug_text = _text(source, aug)
            ret_text = _text(source, ret)
            new_block = (
                "while " + while_test_text + ":\n"
                + body_indent + "if " + if_test_text + ":\n"
                + "\n".join(other_lines) + "\n"
                + body_indent + aug_text + "\n"
                + indent_while + ret_text
            )
            start, end = _span(source, node)
            cand = source[:start] + new_block + source[end:]
            if cand != source:
                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule: helper that returns True vacuously for 0 (empty loop) when checking
# "all digits are lucky", used on a digit-count that can legitimately be 0.
# ---------------------------------------------------------------------------
def _fix_vacuous_true_on_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef):
            body = fn.body
            for i, stmt in enumerate(body):
                if isinstance(stmt, ast.While) and i + 1 < len(body):
                    nxt = body[i + 1]
                    if (isinstance(nxt, ast.Return) and isinstance(nxt.value, ast.Constant)
                            and nxt.value.value is True):
                        test = stmt.test
                        subject = None
                        if isinstance(test, ast.Compare) and len(test.ops) == 1:
                            if (isinstance(test.ops[0], ast.Gt) and isinstance(test.comparators[0], ast.Constant)
                                    and test.comparators[0].value == 0):
                                subject = test.left
                            elif (isinstance(test.ops[0], ast.Lt) and isinstance(test.left, ast.Constant)
                                    and test.left.value == 0):
                                subject = test.comparators[0]
                        if subject is not None:
                            subj_text = _text(source, subject).strip()
                            indent = " " * stmt.col_offset
                            insert = f"if {subj_text} == 0:\n{indent}    return False\n{indent}"
                            s_start, _ = _span(source, stmt)
                            cand = source[:s_start] + insert + source[s_start:]
                            if cand != source:
                                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule: general "wrong final condition" fixer.  Detects a loop (or a couple
# of flat `.count('4') / .count('7')` assignments) that computes the number
# of lucky digits, then rewrites whatever subsequent `if` makes the final
# decision to the canonical `count == 4 or count == 7`.
# ---------------------------------------------------------------------------
def _const_identity(node):
    if isinstance(node, ast.Constant) and node.value in (4, 7, "4", "7"):
        return str(node.value)
    return None


def _lucky_subject(test, source):
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or) and len(test.values) == 2:
        a, b = test.values
        if (isinstance(a, ast.Compare) and isinstance(b, ast.Compare)
                and len(a.ops) == 1 and len(b.ops) == 1
                and isinstance(a.ops[0], ast.Eq) and isinstance(b.ops[0], ast.Eq)):
            ca = _const_identity(a.comparators[0])
            cb = _const_identity(b.comparators[0])
            if ca and cb and {ca, cb} == {"4", "7"}:
                la = _text(source, a.left).strip()
                lb = _text(source, b.left).strip()
                if la == lb:
                    return la
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.In):
        comp = test.comparators[0]
        if isinstance(comp, ast.Constant) and isinstance(comp.value, str) and set(comp.value) == {"4", "7"}:
            return _text(source, test.left).strip()
    return None


def _find_count_update(if_body):
    for stmt in if_body:
        if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) and isinstance(stmt.op, ast.Add):
            if isinstance(stmt.value, ast.Constant) and stmt.value.value == 1:
                return stmt.target.id, "name"
            return stmt.target.id, "len"
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            name = stmt.targets[0].id
            val = stmt.value
            if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add) and isinstance(val.left, ast.Name) and val.left.id == name:
                if isinstance(val.right, ast.Constant) and val.right.value == 1:
                    return name, "name"
                return name, "len"
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and isinstance(call.func.value, ast.Name):
                return call.func.value.id, "len"
    return None


def _gather_loop_counts(tree, source):
    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            for stmt in node.body:
                if isinstance(stmt, ast.If):
                    subj = _lucky_subject(stmt.test, source)
                    if subj:
                        cu = _find_count_update(stmt.body)
                        if cu:
                            name, kind = cu
                            expr = name if kind == "name" else f"len({name})"
                            results.append((stmt, expr))
    return results


def _is_count_call(node, char):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "count"
            and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value == char)


def _gather_flat_counts(tree, source):
    results = []
    assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
    for a in assigns:
        if len(a.targets) == 1 and isinstance(a.targets[0], ast.Name) and isinstance(a.value, ast.BinOp) and isinstance(a.value.op, ast.Add):
            l, r = a.value.left, a.value.right
            if (_is_count_call(l, "4") and _is_count_call(r, "7")) or (_is_count_call(l, "7") and _is_count_call(r, "4")):
                results.append(a.targets[0].id)
    for a in assigns:
        if len(a.targets) == 1 and isinstance(a.targets[0], ast.Tuple) and isinstance(a.value, ast.Tuple):
            tnames = a.targets[0].elts
            vvals = a.value.elts
            if len(tnames) == 2 and len(vvals) == 2 and all(isinstance(t, ast.Name) for t in tnames):
                if (_is_count_call(vvals[0], "4") and _is_count_call(vvals[1], "7")) or (_is_count_call(vvals[0], "7") and _is_count_call(vvals[1], "4")):
                    results.append(f"({tnames[0].id}+{tnames[1].id})")
    name4 = name7 = None
    for a in assigns:
        if len(a.targets) == 1 and isinstance(a.targets[0], ast.Name):
            if _is_count_call(a.value, "4"):
                name4 = a.targets[0].id
            elif _is_count_call(a.value, "7"):
                name7 = a.targets[0].id
    if name4 and name7:
        results.append(f"({name4}+{name7})")
    return results


def _is_name_main_guard(test):
    return isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == "__name__"


def _fix_final_count_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    loop_results = _gather_loop_counts(tree, source)
    flat_results = _gather_flat_counts(tree, source)
    if not loop_results and not flat_results:
        return []

    exclude_ifs = {id(stmt) for stmt, _ in loop_results}
    all_ifs = [n for n in ast.walk(tree) if isinstance(n, ast.If)]
    decision_candidates = [n for n in all_ifs if id(n) not in exclude_ifs and not _is_name_main_guard(n.test)]
    if not decision_candidates:
        return []
    decision = max(decision_candidates, key=lambda n: _span(source, n)[0])

    exprs = [expr for _, expr in loop_results] + flat_results
    out = []
    cur_text = _text(source, decision.test)
    for expr in exprs:
        new_test = f"{expr} == 4 or {expr} == 7"
        if cur_text.replace(" ", "") == new_test.replace(" ", ""):
            continue
        cand = _splice(source, decision.test, new_test)
        if cand != source:
            out.append(cand)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="final_condition_should_be_count_eq_4_or_7",
                apply=_safe(_fix_final_count_condition),
                symptoms=("wrong",),
            ),
            Rule(
                name="membership_whole_seq_instead_of_count",
                apply=_safe(_fix_membership_to_count),
                symptoms=("wrong",),
            ),
            Rule(
                name="range_len_membership_should_index",
                apply=_safe(_fix_range_len_membership),
                symptoms=("wrong",),
            ),
            Rule(
                name="mod_zero_should_be_equality",
                apply=_safe(_fix_mod_zero_equality),
                symptoms=("wrong",),
            ),
            Rule(
                name="truthy_or_literal_instead_of_second_compare",
                apply=_safe(_fix_truthy_or_literal),
                symptoms=("wrong",),
            ),
            Rule(
                name="float_div_should_be_floordiv",
                apply=_safe(_fix_float_div),
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="misplaced_loop_step_and_return",
                apply=_safe(_fix_misplaced_step_return),
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="vacuous_true_on_zero_digits",
                apply=_safe(_fix_vacuous_true_on_zero),
                symptoms=("wrong",),
            ),
            Rule(
                name="ternary_output_strings_should_be_YES_NO",
                apply=_safe(_fix_ternary_strings),
                symptoms=("wrong",),
            ),
            Rule(
                name="undefined_counter_should_use_initialized_var",
                apply=_safe(_fix_undefined_counter),
                symptoms=("err:NameError", "err:UnboundLocalError", "wrong"),
            ),
        ]