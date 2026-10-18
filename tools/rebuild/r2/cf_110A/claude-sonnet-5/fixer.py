import ast

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def _span(source, node):
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _apply_edits(source, edits):
    # edits: list of (start, end, new_text); apply rightmost first
    uniq = {}
    for s, e, t in edits:
        uniq[(s, e)] = t
    items = sorted(uniq.items(), key=lambda kv: kv[0][0], reverse=True)
    out = source
    for (s, e), t in items:
        out = out[:s] + t + out[e:]
    return out


def _finalize(source, edits):
    if not edits:
        return []
    new_source = _apply_edits(source, edits)
    if new_source == source:
        return []
    return [new_source]


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _is_input_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'input')


def _is_len_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'len')


def _collect_str_vars(tree):
    str_vars = set()
    list_vars = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            val = node.value
            if _is_input_call(val):
                str_vars.add(node.targets[0].id)
            elif (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                  and val.func.id == 'str' and len(val.args) == 1
                  and _is_input_call(val.args[0])):
                str_vars.add(node.targets[0].id)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                    and val.func.id == 'list' and len(val.args) == 1):
                arg = val.args[0]
                if _is_input_call(arg) or (isinstance(arg, ast.Name) and arg.id in str_vars):
                    list_vars.add(node.targets[0].id)
    return str_vars, list_vars


def _all_blocks(tree):
    blocks = []
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            val = getattr(node, field, None)
            if isinstance(val, list) and val and isinstance(val[0], ast.stmt):
                blocks.append(val)
    return blocks


def _is_counter_increment_stmt(stmt):
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
        return True
    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, ast.Add)):
        t = stmt.targets[0].id
        if (isinstance(stmt.value.left, ast.Name) and stmt.value.left.id == t) or \
           (isinstance(stmt.value.right, ast.Name) and stmt.value.right.id == t):
            return True
    return False


def _has_counter_incr(stmts):
    return any(_is_counter_increment_stmt(s) for s in stmts)


# ---------------------------------------------------------------------------
# Rule 1: normalize "Yes"/"yes"/"si"/"No"/"no" literals to "YES"/"NO"
# ---------------------------------------------------------------------------

def _r_yes_no_case(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            low = node.value.lower()
            target = None
            if low in ('yes', 'si'):
                target = 'YES'
            elif low == 'no':
                target = 'NO'
            if target is not None and node.value != target:
                s, e = _span(source, node)
                edits.append((s, e, repr(target)))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 2: comparing a character (from a string input) to int 4/7 instead of
# the string '4'/'7'
# ---------------------------------------------------------------------------

def _r_str_digit_compare(source):
    tree = _parse(source)
    if tree is None:
        return []
    str_vars, list_vars = _collect_str_vars(tree)
    char_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            it = node.iter
            if _is_input_call(it) or (isinstance(it, ast.Name) and
                                       (it.id in str_vars or it.id in list_vars)):
                char_vars.add(node.target.id)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            for a, b in ((node.left, node.comparators[0]), (node.comparators[0], node.left)):
                if isinstance(b, ast.Constant) and isinstance(b.value, int) and not isinstance(b.value, bool) \
                        and b.value in (4, 7):
                    is_char = False
                    if isinstance(a, ast.Name) and a.id in char_vars:
                        is_char = True
                    elif isinstance(a, ast.Subscript) and isinstance(a.value, ast.Name) and \
                            a.value.id in (str_vars | list_vars):
                        is_char = True
                    if is_char:
                        s, e = _span(source, b)
                        edits.append((s, e, repr(str(b.value))))
                    break
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 3: `count == len(x)` (checks ALL digits lucky) -> `count == 4 or count == 7`
# ---------------------------------------------------------------------------

def _r_count_eq_len(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            count_node = None
            if _is_len_call(right) and not _is_len_call(left):
                count_node = left
            elif _is_len_call(left) and not _is_len_call(right):
                count_node = right
            if count_node is not None:
                ctext = _text(source, count_node)
                new_text = "(%s == 4 or %s == 7)" % (ctext, ctext)
                s, e = _span(source, node)
                edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 4: `count % 4 == 0 or count % 7 == 0` -> `count == 4 or count == 7`
# ---------------------------------------------------------------------------

def _match_mod_eq_zero(source, node):
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
        left, right = node.left, node.comparators[0]
        if isinstance(right, ast.Constant) and right.value == 0 and \
                isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod) and \
                isinstance(left.right, ast.Constant) and left.right.value in (4, 7):
            return (_text(source, left.left), left.right.value)
    return None


def _r_mod_check_to_eq(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            m0 = _match_mod_eq_zero(source, node.values[0])
            m1 = _match_mod_eq_zero(source, node.values[1])
            if m0 and m1 and m0[0] == m1[0] and {m0[1], m1[1]} == {4, 7}:
                xtext = m0[0]
                new_text = "(%s == 4 or %s == 7)" % (xtext, xtext)
                s, e = _span(source, node)
                edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 5: `x == 4 or 7` / `x == 4 and 7` (bare trailing constant, truthy bug)
# ---------------------------------------------------------------------------

def _r_bare_constant_boolop(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):
            var_text = None
            for v in node.values:
                if isinstance(v, ast.Compare) and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq):
                    var_text = _text(source, v.left)
                    break
            if var_text is None:
                continue
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, int) and not isinstance(v.value, bool):
                    s, e = _span(source, v)
                    edits.append((s, e, "%s == %s" % (var_text, v.value)))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 6: `x == (4 or 7)` -> `x == 4 or x == 7`
# ---------------------------------------------------------------------------

def _r_paren_or_comparator(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            comp = node.comparators[0]
            if isinstance(comp, ast.BoolOp) and len(comp.values) == 2 and \
                    all(isinstance(v, ast.Constant) for v in comp.values):
                var_text = _text(source, node.left)
                c1, c2 = comp.values[0].value, comp.values[1].value
                new_text = "(%s == %r or %s == %r)" % (var_text, c1, var_text, c2)
                s, e = _span(source, node)
                edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 7: digit extracted into a variable (`a = n % 10`) but the following
# `if` still compares the original dividend `n` instead of `a`
# ---------------------------------------------------------------------------

def _r_digit_var_confusion(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for block in _all_blocks(tree):
        for i in range(len(block) - 1):
            stmt = block[i]
            nxt = block[i + 1]
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, ast.Mod)
                    and isinstance(stmt.value.left, ast.Name)
                    and isinstance(stmt.value.right, ast.Constant)
                    and stmt.value.right.value == 10):
                digit_name = stmt.targets[0].id
                n_name = stmt.value.left.id
                if digit_name == n_name:
                    continue
                if isinstance(nxt, ast.If):
                    for sub in ast.walk(nxt.test):
                        if isinstance(sub, ast.Name) and sub.id == n_name:
                            s, e = _span(source, sub)
                            edits.append((s, e, digit_name))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 8: `if cond: count += 1 else: break` (or reversed) early-exits the
# counting loop; the break should just be skipped
# ---------------------------------------------------------------------------

def _r_break_counter(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            body_break = len(node.body) == 1 and isinstance(node.body[0], ast.Break)
            orelse_break = len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Break)
            target = None
            if body_break and node.orelse and not orelse_break and _has_counter_incr(node.orelse):
                target = node.body[0]
            elif orelse_break and node.body and not body_break and _has_counter_incr(node.body):
                target = node.orelse[0]
            if target is not None:
                s, e = _span(source, target)
                edits.append((s, e, 'pass'))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 9: `len(x) == '4'`/`'7'` type mismatch (int compared to str digit)
# ---------------------------------------------------------------------------

def _r_len_vs_str_digit(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            for a, b in ((left, right), (right, left)):
                if _is_len_call(a) and isinstance(b, ast.Constant) and isinstance(b.value, str) \
                        and b.value in ('4', '7'):
                    s, e = _span(source, b)
                    edits.append((s, e, b.value))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 10: `count =+ 1` typo (should be `count += 1`)
# ---------------------------------------------------------------------------

def _r_uadd_typo(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.UnaryOp) and isinstance(val.op, ast.UAdd):
                target_name = node.targets[0].id
                operand_text = _text(source, val.operand)
                new_text = "%s += %s" % (target_name, operand_text)
                s, e = _span(source, node)
                edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 11: unconditional counter increment in a char loop (no lucky check at
# all) -> wrap with `if ch in '47':`
# ---------------------------------------------------------------------------

def _r_missing_guard(source):
    tree = _parse(source)
    if tree is None:
        return []
    str_vars, list_vars = _collect_str_vars(tree)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            it = node.iter
            is_char_iter = _is_input_call(it) or (isinstance(it, ast.Name) and
                                                    (it.id in str_vars or it.id in list_vars))
            if not is_char_iter:
                continue
            if len(node.body) == 1 and _is_counter_increment_stmt(node.body[0]):
                var_name = node.target.id
                stmt = node.body[0]
                s, e = _span(source, stmt)
                stmt_text = source[s:e]
                new_text = "if %s in '47': %s" % (var_name, stmt_text)
                edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 12: `ch.isdigit()` used instead of checking membership in '47'
# ---------------------------------------------------------------------------

def _r_isdigit_to_lucky(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                node.func.attr == 'isdigit' and not node.args:
            base = node.func.value
            if isinstance(base, ast.Name):
                new_text = "%s in '47'" % base.id
                s, e = _span(source, node)
                edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 13: `if ch not in ['4','7']: count += 1` (inverted membership test)
# ---------------------------------------------------------------------------

def _r_notin_to_in(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
            comparator = node.comparators[0]
            if isinstance(comparator, (ast.List, ast.Tuple, ast.Set)):
                vals = set()
                ok = True
                for el in comparator.elts:
                    if isinstance(el, ast.Constant) and isinstance(el.value, str):
                        vals.add(el.value)
                    else:
                        ok = False
                        break
                if ok and vals == {'4', '7'}:
                    left_text = _text(source, node.left)
                    comp_text = _text(source, comparator)
                    new_text = "%s in %s" % (left_text, comp_text)
                    s, e = _span(source, node)
                    edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 14: `x != 4 or x != 7` (always true, De Morgan slip) -> `and`
# ---------------------------------------------------------------------------

def _r_or_to_and_negation(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            v0, v1 = node.values
            if (isinstance(v0, ast.Compare) and len(v0.ops) == 1 and isinstance(v0.ops[0], ast.NotEq) and
                    isinstance(v1, ast.Compare) and len(v1.ops) == 1 and isinstance(v1.ops[0], ast.NotEq)):
                l0text = _text(source, v0.left)
                l1text = _text(source, v1.left)
                c0, c1 = v0.comparators[0], v1.comparators[0]
                if l0text == l1text and isinstance(c0, ast.Constant) and isinstance(c1, ast.Constant) \
                        and c0.value != c1.value:
                    new_text = "%s != %r and %s != %r" % (l0text, c0.value, l0text, c1.value)
                    s, e = _span(source, node)
                    edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 15: off-by-one `range(.., x - 1)` dropping the last character
# ---------------------------------------------------------------------------

def _r_range_minus_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'range':
            if node.args:
                last = node.args[-1]
                if isinstance(last, ast.BinOp) and isinstance(last.op, ast.Sub) and \
                        isinstance(last.right, ast.Constant) and last.right.value == 1:
                    s, e = _span(source, last)
                    new_text = _text(source, last.left)
                    edits.append((s, e, new_text))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 16: `if x == 4: ... elif x == 4: ...` duplicated constant (should be 7)
# ---------------------------------------------------------------------------

def _r_duplicate_elif_constant(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            elif_node = node.orelse[0]
            if (isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and
                    isinstance(node.test.ops[0], ast.Eq) and
                    isinstance(elif_node.test, ast.Compare) and len(elif_node.test.ops) == 1 and
                    isinstance(elif_node.test.ops[0], ast.Eq)):
                l0 = _text(source, node.test.left)
                l1 = _text(source, elif_node.test.left)
                c0 = node.test.comparators[0]
                c1 = elif_node.test.comparators[0]
                if (l0 == l1 and isinstance(c0, ast.Constant) and isinstance(c1, ast.Constant)
                        and c0.value == c1.value and c0.value in (4, 7)):
                    other = 7 if c0.value == 4 else 4
                    s, e = _span(source, c1)
                    edits.append((s, e, str(other)))
    return _finalize(source, edits)


# ---------------------------------------------------------------------------
# Rule 17: two consecutive `.count('4')` calls assigned to different
# variables (copy-paste forgot to change the digit to '7')
# ---------------------------------------------------------------------------

def _r_duplicate_count_arg(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for block in _all_blocks(tree):
        for i in range(len(block) - 1):
            a, b = block[i], block[i + 1]
            info_a = _match_count_call(a)
            info_b = _match_count_call(b)
            if info_a and info_b:
                name_a, call_a, digit_a = info_a
                name_b, call_b, digit_b = info_b
                if name_a != name_b and digit_a == digit_b and digit_a in ('4', '7'):
                    other = '7' if digit_a == '4' else '4'
                    const_node = call_b.args[0]
                    s, e = _span(source, const_node)
                    edits.append((s, e, repr(other)))
    return _finalize(source, edits)


def _match_count_call(stmt):
    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr == 'count'
            and len(stmt.value.args) == 1
            and isinstance(stmt.value.args[0], ast.Constant)
            and isinstance(stmt.value.args[0].value, str)):
        return stmt.targets[0].id, stmt.value, stmt.value.args[0].value
    return None


# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="yes_no_case_normalize", apply=_r_yes_no_case, symptoms=("wrong",)),
            Rule(name="str_digit_int_compare", apply=_r_str_digit_compare, symptoms=("wrong",)),
            Rule(name="count_eq_len_to_lucky", apply=_r_count_eq_len, symptoms=("wrong",)),
            Rule(name="mod_check_to_eq", apply=_r_mod_check_to_eq, symptoms=("wrong",)),
            Rule(name="bare_constant_in_boolop", apply=_r_bare_constant_boolop, symptoms=("wrong",)),
            Rule(name="paren_or_comparator", apply=_r_paren_or_comparator, symptoms=("wrong",)),
            Rule(name="digit_var_confusion", apply=_r_digit_var_confusion, symptoms=("wrong",)),
            Rule(name="break_on_nonlucky", apply=_r_break_counter, symptoms=("wrong",)),
            Rule(name="len_vs_str_digit_mismatch", apply=_r_len_vs_str_digit, symptoms=("wrong",)),
            Rule(name="uadd_typo_augassign", apply=_r_uadd_typo, symptoms=("wrong",)),
            Rule(name="missing_lucky_guard", apply=_r_missing_guard, symptoms=("wrong",)),
            Rule(name="isdigit_should_be_lucky", apply=_r_isdigit_to_lucky, symptoms=("wrong",)),
            Rule(name="notin_lucky_should_be_in", apply=_r_notin_to_in, symptoms=("wrong",)),
            Rule(name="or_to_and_negation", apply=_r_or_to_and_negation, symptoms=("wrong",)),
            Rule(name="range_minus_one_offbyone", apply=_r_range_minus_one, symptoms=("wrong",)),
            Rule(name="duplicate_elif_constant", apply=_r_duplicate_elif_constant, symptoms=("wrong",)),
            Rule(name="duplicate_count_arg", apply=_r_duplicate_count_arg, symptoms=("wrong",)),
        ]