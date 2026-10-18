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
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Rule: lowercase / wrong-cased "yes"/"no" string literals -> "YES"/"NO"
# ---------------------------------------------------------------------------

def fix_yesno_case(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            low = node.value.lower()
            if low == "yes" and node.value != "YES":
                targets.append((node, "YES"))
            elif low == "no" and node.value != "NO":
                targets.append((node, "NO"))
    if not targets:
        return []
    targets.sort(key=lambda t: _span(source, t[0])[0], reverse=True)
    out = source
    for node, rep in targets:
        s, e = _span(source, node)
        out = out[:s] + '"' + rep + '"' + out[e:]
    return [out]


# ---------------------------------------------------------------------------
# Rule: special "si" token meaning YES (seen in a few submissions)
# ---------------------------------------------------------------------------

def fix_si_literal(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    targets = [n for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and n.value == "si"]
    if not targets:
        return []
    targets.sort(key=lambda n: _span(source, n)[0], reverse=True)
    out = source
    for n in targets:
        s, e = _span(source, n)
        out = out[:s] + '"YES"' + out[e:]
    return [out]


# ---------------------------------------------------------------------------
# Rule: comparing a character (from a string/loop over string) to an int
# literal 4 / 7 instead of the string '4' / '7'
# ---------------------------------------------------------------------------

def _is_string_expr(node, string_vars):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in ("input", "str"):
                return True
            if node.func.id == "list" and node.args:
                return _is_string_expr(node.args[0], string_vars)
    if isinstance(node, ast.Name):
        return node.id in string_vars
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    return False


def _collect_string_vars(tree):
    string_vars = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name not in string_vars and _is_string_expr(node.value, string_vars):
                    string_vars.add(name)
                    changed = True
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                if node.target.id not in string_vars and _is_string_expr(node.iter, string_vars):
                    string_vars.add(node.target.id)
                    changed = True
    return string_vars


def _looks_like_char(node, string_vars):
    if isinstance(node, ast.Name):
        return node.id in string_vars
    if isinstance(node, ast.Subscript):
        val = node.value
        if isinstance(val, ast.Name) and val.id in string_vars:
            return True
        return _is_string_expr(val, string_vars)
    return False


def fix_digit_str_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    string_vars = _collect_string_vars(tree)
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if isinstance(right, ast.Constant) and right.value in (4, 7) \
                    and not isinstance(right.value, bool) and _looks_like_char(left, string_vars):
                targets.append(right)
            elif isinstance(left, ast.Constant) and left.value in (4, 7) \
                    and not isinstance(left.value, bool) and _looks_like_char(right, string_vars):
                targets.append(left)
    if not targets:
        return []
    targets.sort(key=lambda n: _span(source, n)[0], reverse=True)
    out = source
    for t in targets:
        s, e = _span(source, t)
        out = out[:s] + "'" + str(t.value) + "'" + out[e:]
    return [out]


# ---------------------------------------------------------------------------
# Rule: while-loop digit extraction mix-up: `a = n % 10` computed but the
# following `if` still compares `n` (the whole number) instead of `a`.
# ---------------------------------------------------------------------------

def fix_while_digit_mixup(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        mod_var = orig_var = None
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                    and isinstance(stmt.targets[0], ast.Name):
                val = stmt.value
                if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mod) \
                        and isinstance(val.left, ast.Name) \
                        and isinstance(val.right, ast.Constant) and val.right.value == 10:
                    mod_var = stmt.targets[0].id
                    orig_var = val.left.id
                    break
        if not mod_var or mod_var == orig_var:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                bad_names = []
                for n2 in ast.walk(stmt.test):
                    if isinstance(n2, ast.Compare):
                        sides = [n2.left] + n2.comparators
                        has_const = any(isinstance(s, ast.Constant) and s.value in (4, 7)
                                         for s in sides)
                        if has_const:
                            for s in sides:
                                if isinstance(s, ast.Name) and s.id == orig_var:
                                    bad_names.append(s)
                if bad_names:
                    bad_names.sort(key=lambda n: _span(source, n)[0], reverse=True)
                    new_source = source
                    for bn in bad_names:
                        s, e = _span(source, bn)
                        new_source = new_source[:s] + mod_var + new_source[e:]
                    out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule: `count =+ 1` typo for `count += 1`
# ---------------------------------------------------------------------------

def fix_unary_augassign_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.UnaryOp) and isinstance(val.op, ast.UAdd):
                ts, te = _span(source, node.targets[0])
                target_text = source[ts:te]
                os_, oe = _span(source, val.operand)
                operand_text = source[os_:oe]
                replacement = f"{target_text} += {operand_text}"
                out.append(_splice(source, node, replacement))
    return out


# ---------------------------------------------------------------------------
# Rule: `x == 4 or 7` (missing left operand on the second comparison)
# ---------------------------------------------------------------------------

def fix_or_bare_literal(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            cmp_node = lit_node = None
            order_ab = True
            if isinstance(a, ast.Compare) and len(a.ops) == 1 and isinstance(a.ops[0], ast.Eq) \
                    and isinstance(b, ast.Constant):
                cmp_node, lit_node = a, b
                order_ab = True
            elif isinstance(b, ast.Compare) and len(b.ops) == 1 and isinstance(b.ops[0], ast.Eq) \
                    and isinstance(a, ast.Constant):
                cmp_node, lit_node = b, a
                order_ab = False
            if cmp_node is not None:
                ls, le = _span(source, cmp_node.left)
                left_text = source[ls:le]
                cs, ce = _span(source, cmp_node.comparators[0])
                comp_text = source[cs:ce]
                lits, lite = _span(source, lit_node)
                lit_text = source[lits:lite]
                if order_ab:
                    new_text = f"{left_text} == {comp_text} or {left_text} == {lit_text}"
                else:
                    new_text = f"{left_text} == {lit_text} or {left_text} == {comp_text}"
                out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: `x == (4 or 7)` chained-literal mistake
# ---------------------------------------------------------------------------

def fix_compare_boolop_comparator(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            comp = node.comparators[0]
            if isinstance(comp, ast.BoolOp) and isinstance(comp.op, ast.Or) \
                    and len(comp.values) == 2 and all(isinstance(v, ast.Constant) for v in comp.values):
                ls, le = _span(source, node.left)
                left_text = source[ls:le]
                v1s, v1e = _span(source, comp.values[0])
                v1_text = source[v1s:v1e]
                v2s, v2e = _span(source, comp.values[1])
                v2_text = source[v2s:v2e]
                new_text = f"{left_text} == {v1_text} or {left_text} == {v2_text}"
                out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: `c % 4 == 0 or c % 7 == 0` divisibility confusion -> `c == 4 or c == 7`
# ---------------------------------------------------------------------------

def fix_mod_divisibility(source):
    tree = _safe_parse(source)
    if tree is None:
        return []

    def is_mod_eq0(n, k):
        return (isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Eq)
                and isinstance(n.left, ast.BinOp) and isinstance(n.left.op, ast.Mod)
                and isinstance(n.left.right, ast.Constant) and n.left.right.value == k
                and isinstance(n.comparators[0], ast.Constant) and n.comparators[0].value == 0)

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if is_mod_eq0(a, 4) and is_mod_eq0(b, 7):
                vs, ve = _span(source, a.left.left)
                var_text = source[vs:ve]
                out.append(_splice(source, node, f"{var_text} == 4 or {var_text} == 7"))
            elif is_mod_eq0(a, 7) and is_mod_eq0(b, 4):
                vs, ve = _span(source, a.left.left)
                var_text = source[vs:ve]
                out.append(_splice(source, node, f"{var_text} == 7 or {var_text} == 4"))
    return out


# ---------------------------------------------------------------------------
# Rule: `x != 4 or x != 7` (always true) -> `x != 4 and x != 7`
# ---------------------------------------------------------------------------

def fix_demorgan_or_to_and(source):
    tree = _safe_parse(source)
    if tree is None:
        return []

    def is_ne(n):
        return isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.NotEq)

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if is_ne(a) and is_ne(b):
                a_s, a_e = _span(source, a)
                a_text = source[a_s:a_e]
                b_s, b_e = _span(source, b)
                b_text = source[b_s:b_e]
                out.append(_splice(source, node, f"{a_text} and {b_text}"))
    return out


# ---------------------------------------------------------------------------
# Rule: using len(...) where a count of lucky digits is meant
# ---------------------------------------------------------------------------

def _is_len_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "len" and len(node.args) == 1)


def fix_len_inline_as_count(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            sides = [node.left, node.comparators[0]]
            has47 = any(isinstance(s, ast.Constant) and s.value in (4, 7) for s in sides)
            if not has47:
                continue
            for s in sides:
                if _is_len_call(s):
                    found.append(s)
    if not found:
        return []
    found.sort(key=lambda n: _span(source, n)[0], reverse=True)
    out = source
    for call in found:
        s, e = _span(source, call)
        arg = call.args[0]
        a_s, a_e = _span(source, arg)
        arg_text = source[a_s:a_e]
        replacement = f"({arg_text}.count('4')+{arg_text}.count('7'))"
        out = out[:s] + replacement + out[e:]
    return [out]


def fix_len_var_as_count(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    assigns = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            if _is_len_call(node.value):
                assigns.append((node, node.targets[0].id, node.value))
    if not assigns:
        return []
    out = []
    for node, varname, val in assigns:
        used = False
        for n2 in ast.walk(tree):
            if isinstance(n2, ast.Compare):
                sides = [n2.left] + n2.comparators
                has_var = any(isinstance(s, ast.Name) and s.id == varname for s in sides)
                has47 = any(isinstance(s, ast.Constant) and s.value in (4, 7) for s in sides)
                if has_var and has47:
                    used = True
                    break
        if not used:
            continue
        arg = val.args[0]
        a_s, a_e = _span(source, arg)
        arg_text = source[a_s:a_e]
        replacement = f"({arg_text}.count('4')+{arg_text}.count('7'))"
        vs, ve = _span(source, val)
        out.append(source[:vs] + replacement + source[ve:])
    return out


def fix_count_eq_len(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            cnt_node = None
            if isinstance(left, ast.Name) and _is_len_call(right):
                cnt_node = left
            elif isinstance(right, ast.Name) and _is_len_call(left):
                cnt_node = right
            if cnt_node is not None:
                found.append((node, cnt_node))
    if not found:
        return []
    found.sort(key=lambda t: _span(source, t[0])[0], reverse=True)
    out = source
    for node, cnt_node in found:
        s, e = _span(source, node)
        cs, ce = _span(source, cnt_node)
        cnt_text = source[cs:ce]
        replacement = f"{cnt_text} == 4 or {cnt_text} == 7"
        out = out[:s] + replacement + out[e:]
    return [out]


# ---------------------------------------------------------------------------
# Rule: two consecutive `x = s.count("4")` assignments (second should be '7')
# ---------------------------------------------------------------------------

def _dup_count_fix(source, s1, s2):
    if not (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)):
        return None
    if len(s1.targets) != 1 or len(s2.targets) != 1:
        return None
    v1, v2 = s1.value, s2.value
    if not (isinstance(v1, ast.Call) and isinstance(v1.func, ast.Attribute) and v1.func.attr == "count"):
        return None
    if not (isinstance(v2, ast.Call) and isinstance(v2.func, ast.Attribute) and v2.func.attr == "count"):
        return None
    if len(v1.args) != 1 or len(v2.args) != 1:
        return None
    if not (isinstance(v1.args[0], ast.Constant) and isinstance(v2.args[0], ast.Constant)):
        return None
    if v1.args[0].value != "4" or v2.args[0].value != "4":
        return None
    b1s, b1e = _span(source, v1.func.value)
    b2s, b2e = _span(source, v2.func.value)
    if source[b1s:b1e] != source[b2s:b2e]:
        return None
    arg_s, arg_e = _span(source, v2.args[0])
    return source[:arg_s] + "'7'" + source[arg_e:]


def fix_duplicate_count_arg(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        for attr in ("body", "orelse", "finalbody"):
            body = getattr(node, attr, None)
            if not isinstance(body, list):
                continue
            for i in range(len(body) - 1):
                rep = _dup_count_fix(source, body[i], body[i + 1])
                if rep:
                    out.append(rep)
    return out


# ---------------------------------------------------------------------------
# Rule: `.isdigit()` misused where '4'/'7' membership was meant
# ---------------------------------------------------------------------------

def fix_isdigit_misuse(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "isdigit" and not node.args:
            base = node.func.value
            bs, be = _span(source, base)
            base_text = source[bs:be]
            replacement = f"({base_text} == '4' or {base_text} == '7')"
            out.append(_splice(source, node, replacement))
    return out


# ---------------------------------------------------------------------------
# Rule: off-by-one on range bound: range(0, s - 1) -> range(0, s)
# ---------------------------------------------------------------------------

def fix_range_off_by_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            args = node.args
            target = None
            if len(args) == 1:
                target = args[0]
            elif len(args) == 2:
                target = args[1]
            if isinstance(target, ast.BinOp) and isinstance(target.op, ast.Sub) \
                    and isinstance(target.right, ast.Constant) and target.right.value == 1:
                base = target.left
                bs, be = _span(source, base)
                base_text = source[bs:be]
                out.append(_splice(source, target, base_text))
    return out


# ---------------------------------------------------------------------------
# Rule: stray debug print of a raw variable alongside the real answer print
# ---------------------------------------------------------------------------

def remove_debug_print(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    prints = [n for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]
    if len(prints) < 2:
        return []

    def call_text(call):
        s, e = _span(source, call)
        return source[s:e]

    def mentions_answer(call):
        t = call_text(call).lower()
        return "yes" in t or "no" in t

    debug_calls = [c for c in prints if not mentions_answer(c)]
    answer_calls = [c for c in prints if mentions_answer(c)]
    if not debug_calls or not answer_calls:
        return []
    debug_calls.sort(key=lambda c: _span(source, c)[0], reverse=True)
    out = source
    for call in debug_calls:
        s, e = _span(source, call)
        out = out[:s] + "0" + out[e:]
    return [out]


class Fixer:
    def rules(self):
        return [
            Rule(name="fix_yesno_case", apply=fix_yesno_case, symptoms=("wrong",)),
            Rule(name="fix_si_literal", apply=fix_si_literal, symptoms=("wrong",)),
            Rule(name="fix_digit_str_compare", apply=fix_digit_str_compare, symptoms=("wrong",)),
            Rule(name="fix_while_digit_mixup", apply=fix_while_digit_mixup, symptoms=("wrong",)),
            Rule(name="fix_unary_augassign_typo", apply=fix_unary_augassign_typo, symptoms=("wrong",)),
            Rule(name="fix_or_bare_literal", apply=fix_or_bare_literal, symptoms=("wrong",)),
            Rule(name="fix_compare_boolop_comparator", apply=fix_compare_boolop_comparator, symptoms=("wrong",)),
            Rule(name="fix_mod_divisibility", apply=fix_mod_divisibility, symptoms=("wrong",)),
            Rule(name="fix_demorgan_or_to_and", apply=fix_demorgan_or_to_and, symptoms=("wrong",)),
            Rule(name="fix_len_inline_as_count", apply=fix_len_inline_as_count, symptoms=("wrong",)),
            Rule(name="fix_len_var_as_count", apply=fix_len_var_as_count, symptoms=("wrong",)),
            Rule(name="fix_count_eq_len", apply=fix_count_eq_len, symptoms=("wrong",)),
            Rule(name="fix_duplicate_count_arg", apply=fix_duplicate_count_arg, symptoms=("wrong",)),
            Rule(name="fix_isdigit_misuse", apply=fix_isdigit_misuse, symptoms=("wrong",)),
            Rule(name="fix_range_off_by_one", apply=fix_range_off_by_one, symptoms=("wrong",)),
            Rule(name="remove_debug_print", apply=remove_debug_print, symptoms=("wrong",)),
        ]