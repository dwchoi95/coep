"""
Repair module for the "Nearly Lucky Number" assignment.

Targets the recurring misconceptions found in buggy submissions:
  - wrong output literals instead of "YES"/"NO"
  - comparing a string-typed digit/char against an int literal 4/7
  - the `=+` augmented-assignment typo
  - misuse of the bare builtin name `len` instead of calling it
  - checking "all digits are lucky" (count == len(...)) instead of
    "count of lucky digits is itself lucky" (count == 4 or count == 7)
  - `X == (4 or 7)` always-true-constant trap
  - `if cond1 or <bare constant>` missing the second comparison
  - `or` used where `and` was intended for two NotEq checks sharing a
    left operand
  - `X % C == 0` used instead of `X == C`
  - counting every character in a loop instead of only lucky ones
  - a single `var == 4` (or `== 7`) check missing its complement
  - an int count compared against a string literal ('4'/'7') instead of
    the int literal
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


def _seg(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _apply_all(source, edits):
    if not edits:
        return source
    edits_sorted = sorted(edits, key=lambda ne: _span(source, ne[0])[0], reverse=True)
    result = source
    for node, text in edits_sorted:
        result = _splice(result, node, text)
    return result


def _call_name(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _is_int_const(n, allowed=None):
    if not isinstance(n, ast.Constant) or not isinstance(n.value, int) or isinstance(n.value, bool):
        return False
    if allowed is not None and n.value not in allowed:
        return False
    return True


def _is_len_call(n):
    return isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'len'


def _is_stringy_call(val):
    if not isinstance(val, ast.Call):
        return False
    fname = _call_name(val)
    if fname == 'input':
        return True
    if fname in ('str', 'list') and val.args:
        return _is_stringy_call(val.args[0])
    return False


def _collect_string_vars(tree):
    string_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if _is_stringy_call(node.value):
                string_vars.add(node.targets[0].id)
    return string_vars


def _collect_loop_char_vars(tree, string_vars):
    loop_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            it = node.iter
            if _call_name(it) == 'input':
                loop_vars.add(node.target.id)
            elif isinstance(it, ast.Name) and it.id in string_vars:
                loop_vars.add(node.target.id)
            elif isinstance(it, ast.Call) and _call_name(it) == 'list' and it.args and _call_name(it.args[0]) == 'input':
                loop_vars.add(node.target.id)
    return loop_vars


# ---------------------------------------------------------------------------
# Rule 1: wrong "YES"/"NO" literal strings
# ---------------------------------------------------------------------------

_WRONG_LITERALS = {"si": "YES", "Yes": "YES", "yes": "YES", "no": "NO", "No": "NO"}


def fix_output_literals(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    lines = source.splitlines()
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in _WRONG_LITERALS:
            line = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
            if "print" in line:
                quote = _seg(source, node)[0]
                new_val = _WRONG_LITERALS[node.value]
                edits.append((node, f"{quote}{new_val}{quote}"))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 2: char-vs-int comparison (n[i]==4 instead of n[i]=='4')
# ---------------------------------------------------------------------------

def fix_char_int_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    string_vars = _collect_string_vars(tree)
    loop_vars = _collect_loop_char_vars(tree, string_vars)

    def is_charlike(n):
        if isinstance(n, ast.Name) and n.id in loop_vars:
            return True
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in string_vars:
            return True
        return False

    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            left, right = node.left, node.comparators[0]
            op_txt = " == " if isinstance(node.ops[0], ast.Eq) else " != "
            if is_charlike(left) and _is_int_const(right, (4, 7)):
                new_text = _seg(source, left) + op_txt + f"'{right.value}'"
                edits.append((node, new_text))
            elif is_charlike(right) and _is_int_const(left, (4, 7)):
                new_text = f"'{left.value}'" + op_txt + _seg(source, right)
                edits.append((node, new_text))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 3: `count =+ 1` typo for `count += 1`
# ---------------------------------------------------------------------------

def fix_plus_equal_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
           and isinstance(node.value, ast.UnaryOp) and isinstance(node.value.op, ast.UAdd):
            target_src = _seg(source, node.targets[0])
            operand_src = _seg(source, node.value.operand)
            new_text = f"{target_src} += {operand_src}"
            edits.append((node, new_text))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 4: bare `len` name used instead of calling it
# ---------------------------------------------------------------------------

def fix_bare_len(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    len_arg_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'len' and len(node.args) == 1:
            len_arg_src = _seg(source, node.args[0])
            break
    if len_arg_src is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for opnd in [node.left] + list(node.comparators):
                if isinstance(opnd, ast.Name) and opnd.id == 'len':
                    edits.append((opnd, f"len({len_arg_src})"))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 5: "all digits lucky" (count == len(...)) instead of (count==4 or ==7)
# ---------------------------------------------------------------------------

def fix_len_equals_count(source):
    tree = _safe_parse(source)
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
            elif _is_int_const(right) and right.value == 0 and isinstance(left, ast.BinOp) and isinstance(left.op, ast.Sub):
                if _is_len_call(left.right) and not _is_len_call(left.left):
                    count_node = left.left
                elif _is_len_call(left.left) and not _is_len_call(left.right):
                    count_node = left.right
            if count_node is not None:
                count_src = _seg(source, count_node)
                edits.append((node, f"{count_src} == 4 or {count_src} == 7"))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 6: `n == (4 or 7)` always-true-constant trap
# ---------------------------------------------------------------------------

def fix_or_constant_rhs(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            right = node.comparators[0]
            if isinstance(right, ast.BoolOp) and isinstance(right.op, ast.Or) and \
               all(isinstance(v, ast.Constant) for v in right.values):
                left_src = _seg(source, node.left)
                parts = " or ".join(f"{left_src} == {v.value!r}" for v in right.values)
                edits.append((node, parts))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 7: `cond or <bare constant>` missing the other comparison
# ---------------------------------------------------------------------------

def fix_bare_constant_in_or(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            compares = [v for v in node.values
                        if isinstance(v, ast.Compare) and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq)]
            bares = [v for v in node.values if _is_int_const(v)]
            if compares and bares:
                left_src = _seg(source, compares[0].left)
                for b in bares:
                    edits.append((b, f"{left_src} == {b.value}"))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 8: `or` should be `and` for two NotEq checks with same left operand
# ---------------------------------------------------------------------------

def fix_or_should_be_and(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if isinstance(a, ast.Compare) and isinstance(b, ast.Compare) and \
               len(a.ops) == 1 and len(b.ops) == 1 and \
               isinstance(a.ops[0], ast.NotEq) and isinstance(b.ops[0], ast.NotEq):
                if _seg(source, a.left) == _seg(source, b.left):
                    new_text = _seg(source, a) + " and " + _seg(source, b)
                    edits.append((node, new_text))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 9: `X % C == 0` used instead of `X == C`
# ---------------------------------------------------------------------------

def fix_mod_eq_zero(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if _is_int_const(right) and right.value == 0 and isinstance(left, ast.BinOp) and \
               isinstance(left.op, ast.Mod) and _is_int_const(left.right, (4, 7)):
                a_src = _seg(source, left.left)
                c = left.right.value
                edits.append((node, f"{a_src} == {c}"))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 10: loop counts every character instead of only lucky ones
# ---------------------------------------------------------------------------

def fix_count_all_chars(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    string_vars = _collect_string_vars(tree)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            it = node.iter
            is_str_iter = (_call_name(it) == 'input') or (isinstance(it, ast.Name) and it.id in string_vars)
            if not is_str_iter or len(node.body) != 1:
                continue
            stmt = node.body[0]
            is_counter = False
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add) and isinstance(stmt.target, ast.Name):
                is_counter = True
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) \
                 and isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, ast.Add):
                tgt_name = stmt.targets[0].id
                if (isinstance(stmt.value.left, ast.Name) and stmt.value.left.id == tgt_name) or \
                   (isinstance(stmt.value.right, ast.Name) and stmt.value.right.id == tgt_name):
                    is_counter = True
            if not is_counter:
                continue
            loopvar = node.target.id
            stmt_src = _seg(source, stmt)
            indent = ' ' * stmt.col_offset
            new_text = f"if {loopvar} == '4' or {loopvar} == '7':\n{indent}    {stmt_src}"
            edits.append((stmt, new_text))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 11: single `var == 4` (or `== 7`) missing its complement
# ---------------------------------------------------------------------------

def fix_missing_complement(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                right = test.comparators[0]
                if _is_int_const(right, (4, 7)):
                    present = right.value
                    missing = 7 if present == 4 else 4
                    left_src = _seg(source, test.left)
                    new_text = f"{left_src} == {present} or {left_src} == {missing}"
                    edits.append((test, new_text))
    if not edits:
        return []
    return [_apply_all(source, edits)]


# ---------------------------------------------------------------------------
# Rule 12: int count compared against string literal '4'/'7'
# ---------------------------------------------------------------------------

def fix_int_count_vs_str_literal(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    count_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == 'count':
                count_vars.add(node.targets[0].id)

    def is_intlike(n):
        if isinstance(n, ast.Name) and n.id in count_vars:
            return True
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            return True
        return False

    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if is_intlike(left) and isinstance(right, ast.Constant) and right.value in ('4', '7'):
                edits.append((right, right.value))
            elif is_intlike(right) and isinstance(left, ast.Constant) and left.value in ('4', '7'):
                edits.append((left, left.value))
    if not edits:
        return []
    return [_apply_all(source, edits)]


class Fixer:
    def rules(self):
        return [
            Rule(name="fix_output_literals", apply=fix_output_literals,
                 symptoms=("wrong",)),
            Rule(name="fix_char_int_compare", apply=fix_char_int_compare,
                 symptoms=("wrong",)),
            Rule(name="fix_plus_equal_typo", apply=fix_plus_equal_typo,
                 symptoms=("wrong",)),
            Rule(name="fix_bare_len", apply=fix_bare_len,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_len_equals_count", apply=fix_len_equals_count,
                 symptoms=("wrong",)),
            Rule(name="fix_or_constant_rhs", apply=fix_or_constant_rhs,
                 symptoms=("wrong",)),
            Rule(name="fix_bare_constant_in_or", apply=fix_bare_constant_in_or,
                 symptoms=("wrong",)),
            Rule(name="fix_or_should_be_and", apply=fix_or_should_be_and,
                 symptoms=("wrong",)),
            Rule(name="fix_mod_eq_zero", apply=fix_mod_eq_zero,
                 symptoms=("wrong",)),
            Rule(name="fix_count_all_chars", apply=fix_count_all_chars,
                 symptoms=("wrong",)),
            Rule(name="fix_missing_complement", apply=fix_missing_complement,
                 symptoms=("wrong",)),
            Rule(name="fix_int_count_vs_str_literal", apply=fix_int_count_vs_str_literal,
                 symptoms=("wrong",)),
        ]