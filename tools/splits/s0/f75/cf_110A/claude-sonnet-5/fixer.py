"""
Repair module for the "Nearly Lucky Number" assignment.

Each rule performs a small, local, AST-span-based edit targeting one
observed misconception.  Rules never rewrite whole functions/modules;
they only splice a narrow replacement into the original source text.
"""

import ast
from src.core.repair import Rule


# ----------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------

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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapped


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ----------------------------------------------------------------------
# Rule 1: wrong-case / wrong-word YES/NO literals
# ----------------------------------------------------------------------

_WRONG_TO_RIGHT = {
    'yes': 'YES', 'Yes': 'YES', 'si': 'YES',
    'no': 'NO', 'No': 'NO',
}


@_safe
def _fix_wrong_case_literals(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in _WRONG_TO_RIGHT:
                edits.append((node, repr(_WRONG_TO_RIGHT[node.value])))
    if not edits:
        return []
    edits.sort(key=lambda t: _span(source, t[0])[0], reverse=True)
    new_source = source
    for node, repl in edits:
        new_source = _splice(new_source, node, repl)
    return [new_source] if new_source != source else []


# ----------------------------------------------------------------------
# Rule 2: "x =+ 1" typo (parses as Assign to UnaryOp) -> "x += 1"
# ----------------------------------------------------------------------

@_safe
def _fix_assign_plus_typo(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            val = node.value
            if isinstance(tgt, ast.Name) and isinstance(val, ast.UnaryOp) \
               and isinstance(val.op, ast.UAdd):
                tgt_src = _text(source, tgt)
                operand_src = _text(source, val.operand)
                new_stmt = f"{tgt_src} += {operand_src}"
                out.append(_splice(source, node, new_stmt))
    return out


# ----------------------------------------------------------------------
# Rule 3: float division instead of floor division when peeling digits
# ----------------------------------------------------------------------

@_safe
def _fix_float_div_augassign(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
            tgt_src = _text(source, node.target)
            val_src = _text(source, node.value)
            new_stmt = f"{tgt_src} //= {val_src}"
            out.append(_splice(source, node, new_stmt))
    return out


@_safe
def _fix_float_div_assign(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            val = node.value
            div_node = None
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
               and val.func.id == 'int' and len(val.args) == 1 \
               and isinstance(val.args[0], ast.BinOp) and isinstance(val.args[0].op, ast.Div):
                div_node = val.args[0]
            elif isinstance(val, ast.BinOp) and isinstance(val.op, ast.Div):
                div_node = val
            if div_node is not None:
                left_src = _text(source, div_node.left)
                right_src = _text(source, div_node.right)
                tgt_src = _text(source, node.targets[0])
                new_stmt = f"{tgt_src} = {left_src} // {right_src}"
                out.append(_splice(source, node, new_stmt))
    return out


# ----------------------------------------------------------------------
# Rule 4: bare builtin `len` used instead of an already-computed length var
# ----------------------------------------------------------------------

@_safe
def _fix_bare_len_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    assigned_var = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
               and val.func.id == 'len':
                assigned_var = node.targets[0].id
    if assigned_var is None:
        return []

    parent_map = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent

    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == 'len':
            parent = parent_map.get(node)
            if isinstance(parent, ast.Call) and parent.func is node:
                continue
            edits.append(node)
    if not edits:
        return []
    edits.sort(key=lambda n: _span(source, n)[0], reverse=True)
    new_source = source
    for node in edits:
        new_source = _splice(new_source, node, assigned_var)
    return [new_source] if new_source != source else []


# ----------------------------------------------------------------------
# Rule 5: "len(A) == len(B)" (purity-check) -> "X == 4 or X == 7"
# ----------------------------------------------------------------------

@_safe
def _fix_len_equality_to_count(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if isinstance(left, ast.Constant) or isinstance(right, ast.Constant):
                continue
            for operand in (left, right):
                if isinstance(operand, ast.Call) and isinstance(operand.func, ast.Name) \
                   and operand.func.id == 'len' and len(operand.args) == 1:
                    cand_src = _text(source, operand.args[0])
                else:
                    cand_src = _text(source, operand)
                new_test = f"{cand_src} == 4 or {cand_src} == 7"
                out.append(_splice(source, node, new_test))
    return out


# ----------------------------------------------------------------------
# Rule 6: De Morgan slip: "X != 4 or X != 7" -> "X != 4 and X != 7"
# ----------------------------------------------------------------------

@_safe
def _fix_demorgan_noteq(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) \
           and len(node.values) == 2:
            a, b = node.values
            if isinstance(a, ast.Compare) and isinstance(b, ast.Compare):
                if len(a.ops) == 1 and len(b.ops) == 1 \
                   and isinstance(a.ops[0], ast.NotEq) and isinstance(b.ops[0], ast.NotEq):
                    if _text(source, a.left) == _text(source, b.left):
                        new_test = f"{_text(source, a)} and {_text(source, b)}"
                        out.append(_splice(source, node, new_test))
    return out


# ----------------------------------------------------------------------
# Rule 7: counting the wrong set ("not in ['4','7']: count += 1")
# ----------------------------------------------------------------------

@_safe
def _fix_not_in_counter(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            test = node.test
            if len(test.ops) == 1 and isinstance(test.ops[0], ast.NotIn):
                comparator = test.comparators[0]
                is_lucky_container = False
                if isinstance(comparator, (ast.List, ast.Tuple, ast.Set)):
                    vals = [e.value for e in comparator.elts if isinstance(e, ast.Constant)]
                    if set(vals) == {'4', '7'}:
                        is_lucky_container = True
                if is_lucky_container and len(node.body) == 1 \
                   and isinstance(node.body[0], ast.AugAssign) \
                   and isinstance(node.body[0].op, ast.Add):
                    test_src = _text(source, test)
                    new_test = test_src.replace(' not in ', ' in ')
                    if new_test != test_src:
                        out.append(_splice(source, test, new_test))
    return out


# ----------------------------------------------------------------------
# Rule 8: misapplied double-.replace('4','').replace('7','') idiom
# ----------------------------------------------------------------------

def _unwrap_replace_chain(node):
    chars = set()
    cur = node
    for _ in range(2):
        if not (isinstance(cur, ast.Call) and isinstance(cur.func, ast.Attribute)
                and cur.func.attr == 'replace'):
            return None
        if len(cur.args) != 2:
            return None
        a0, a1 = cur.args
        if not (isinstance(a0, ast.Constant) and isinstance(a0.value, str)
                and isinstance(a1, ast.Constant) and a1.value == ''):
            return None
        chars.add(a0.value)
        cur = cur.func.value
    if chars == {'4', '7'}:
        return cur
    return None


@_safe
def _fix_double_replace_chain(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            target_len_call = None
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) \
               and left.func.id == 'len' and isinstance(right, ast.Constant) and right.value == 0:
                target_len_call = left
            elif isinstance(right, ast.Call) and isinstance(right.func, ast.Name) \
                    and right.func.id == 'len' and isinstance(left, ast.Constant) and left.value == 0:
                target_len_call = right
            if target_len_call is not None and len(target_len_call.args) == 1:
                base = _unwrap_replace_chain(target_len_call.args[0])
                if base is not None:
                    base_src = _text(source, base)
                    new_test = f"({base_src}.count('4') + {base_src}.count('7')) in (4, 7)"
                    out.append(_splice(source, node, new_test))

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            operand = node.operand
            if isinstance(operand, ast.Call) and isinstance(operand.func, ast.Name) \
               and operand.func.id == 'bool' and len(operand.args) == 1:
                base = _unwrap_replace_chain(operand.args[0])
                if base is not None:
                    base_src = _text(source, base)
                    new_expr = f"(({base_src}.count('4') + {base_src}.count('7')) in (4, 7))"
                    out.append(_splice(source, node, new_expr))
    return out


# ----------------------------------------------------------------------
# Rule 9: "count % 4 == 0 or count % 7 == 0" -> "count == 4 or count == 7"
# ----------------------------------------------------------------------

@_safe
def _fix_mod_equality(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            info = []
            ok = True
            for cmp in (a, b):
                if isinstance(cmp, ast.Compare) and len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq):
                    left = cmp.left
                    right = cmp.comparators[0]
                    if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod) \
                       and isinstance(right, ast.Constant) and right.value == 0 \
                       and isinstance(left.right, ast.Constant) and left.right.value in (4, 7):
                        info.append((left.left, left.right.value))
                        continue
                ok = False
                break
            if ok and len(info) == 2 and {info[0][1], info[1][1]} == {4, 7}:
                var_src0 = _text(source, info[0][0])
                var_src1 = _text(source, info[1][0])
                if var_src0 == var_src1:
                    new_test = f"{var_src0} == 4 or {var_src0} == 7"
                    out.append(_splice(source, node, new_test))
    return out


# ----------------------------------------------------------------------
# Rule 10: off-by-one "range(A, B - 1)" -> "range(A, B)"
# ----------------------------------------------------------------------

@_safe
def _fix_range_off_by_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'range' and len(node.args) == 2:
            second = node.args[1]
            if isinstance(second, ast.BinOp) and isinstance(second.op, ast.Sub) \
               and isinstance(second.right, ast.Constant) and second.right.value == 1:
                new_bound = _text(source, second.left)
                new_call_src = f"range({_text(source, node.args[0])}, {new_bound})"
                out.append(_splice(source, node, new_call_src))
    return out


# ----------------------------------------------------------------------
# Rule 11: comparing a string-derived char/element to int 4/7 literal
# ----------------------------------------------------------------------

def _source_is_stringy(base_name, tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name) and node.targets[0].id == base_name:
            val = node.value
            if isinstance(val, ast.Call):
                if isinstance(val.func, ast.Name) and val.func.id == 'input':
                    return True
                if isinstance(val.func, ast.Name) and val.func.id in ('list', 'str') \
                   and len(val.args) == 1:
                    inner = val.args[0]
                    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) \
                       and inner.func.id == 'input':
                        return True
    return False


def _iterable_is_stringy(iter_node, tree):
    if isinstance(iter_node, ast.Call) and isinstance(iter_node.func, ast.Name) \
       and iter_node.func.id == 'input':
        return True
    if isinstance(iter_node, ast.Name):
        return _source_is_stringy(iter_node.id, tree)
    return False


def _name_is_stringy(name_id, tree):
    if _source_is_stringy(name_id, tree):
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name) \
           and node.target.id == name_id:
            if _iterable_is_stringy(node.iter, tree):
                return True
    return False


@_safe
def _fix_int_literal_digit_compare(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            left = node.left
            right = node.comparators[0]
            base_name = None
            if isinstance(left, ast.Subscript) and isinstance(left.value, ast.Name):
                base_name = left.value.id
            elif isinstance(left, ast.Name):
                base_name = left.id
            if base_name is None:
                continue
            if isinstance(right, ast.Constant) and right.value in (4, 7):
                if _name_is_stringy(base_name, tree):
                    edits.append((right, repr(str(right.value))))
    if not edits:
        return []
    edits.sort(key=lambda t: _span(source, t[0])[0], reverse=True)
    new_source = source
    for node, repl in edits:
        new_source = _splice(new_source, node, repl)
    return [new_source] if new_source != source else []


# ----------------------------------------------------------------------
# Rule 12: "X == A or B" truthy-literal slip -> "X == A or X == B"
# ----------------------------------------------------------------------

@_safe
def _fix_bare_constant_or(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            cmp_node = const_node = None
            if isinstance(a, ast.Compare) and isinstance(b, ast.Constant):
                cmp_node, const_node = a, b
            elif isinstance(b, ast.Compare) and isinstance(a, ast.Constant):
                cmp_node, const_node = b, a
            if cmp_node is not None and len(cmp_node.ops) == 1 and isinstance(cmp_node.ops[0], ast.Eq):
                left_src = _text(source, cmp_node.left)
                const_src = _text(source, const_node)
                new_test = f"{_text(source, cmp_node)} or {left_src} == {const_src}"
                out.append(_splice(source, node, new_test))
    return out


# ----------------------------------------------------------------------
# Rule 13: "X == (4 or 7)" -> "X in (4, 7)"
# ----------------------------------------------------------------------

@_safe
def _fix_or_in_parens_compare(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            right = node.comparators[0]
            if isinstance(right, ast.BoolOp) and isinstance(right.op, ast.Or) \
               and all(isinstance(v, ast.Constant) for v in right.values):
                left_src = _text(source, node.left)
                vals = ", ".join(_text(source, v) for v in right.values)
                new_test = f"{left_src} in ({vals})"
                out.append(_splice(source, node, new_test))
    return out


# ----------------------------------------------------------------------
# Rule 14: int literal set/list {4,7} used against a string-derived set
# ----------------------------------------------------------------------

@_safe
def _fix_int_set_literal_vs_input(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            left, right = node.left, node.right

            def is_input_set(n):
                return isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                    and n.func.id == 'set' and len(n.args) == 1

            if is_input_set(left) and isinstance(right, (ast.Set, ast.List, ast.Tuple)):
                elts = right.elts
                if elts and all(isinstance(e, ast.Constant) and e.value in (4, 7) for e in elts):
                    edits = [(e, repr(str(e.value))) for e in elts]
                    edits.sort(key=lambda t: _span(source, t[0])[0], reverse=True)
                    new_source = source
                    for en, repl in edits:
                        new_source = _splice(new_source, en, repl)
                    if new_source != source:
                        out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 15: leftover debug print statements that break exact-output tests
# ----------------------------------------------------------------------

@_safe
def _remove_debug_print(source):
    tree = _parse(source)
    if tree is None:
        return []

    all_prints = []

    def visit_body(body):
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Name) and call.func.id == 'print':
                    all_prints.append(stmt)
            for _field, value in ast.iter_fields(stmt):
                if isinstance(value, list) and value and all(isinstance(v, ast.stmt) for v in value):
                    visit_body(value)

    visit_body(tree.body)

    def is_real_output(stmt):
        call = stmt.value
        if len(call.args) != 1:
            return False
        arg = call.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value in ('YES', 'NO'):
            return True
        if isinstance(arg, ast.IfExp):
            return True
        return False

    real_outputs = [p for p in all_prints if is_real_output(p)]
    if not real_outputs:
        return []
    debug_prints = [p for p in all_prints if p not in real_outputs]
    if not debug_prints:
        return []

    debug_prints.sort(key=lambda n: _span(source, n)[0], reverse=True)
    new_source = source
    for node in debug_prints:
        s, e = _span(new_source, node)
        line_start = new_source.rfind('\n', 0, s) + 1
        line_end = new_source.find('\n', e)
        line_end = len(new_source) if line_end == -1 else line_end + 1
        new_source = new_source[:line_start] + new_source[line_end:]
    return [new_source] if new_source != source else []


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="wrong_case_yes_no_literal",
                 apply=_fix_wrong_case_literals,
                 symptoms=("wrong",)),
            Rule(name="assign_plus_typo",
                 apply=_fix_assign_plus_typo,
                 symptoms=("wrong",)),
            Rule(name="float_div_augassign_should_be_floordiv",
                 apply=_fix_float_div_augassign,
                 symptoms=("wrong",)),
            Rule(name="float_div_assign_should_be_floordiv",
                 apply=_fix_float_div_assign,
                 symptoms=("wrong",)),
            Rule(name="bare_len_name_should_be_length_var",
                 apply=_fix_bare_len_name,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="len_equality_purity_check_to_count",
                 apply=_fix_len_equality_to_count,
                 symptoms=("wrong",)),
            Rule(name="demorgan_noteq_or_to_and",
                 apply=_fix_demorgan_noteq,
                 symptoms=("wrong",)),
            Rule(name="not_in_lucky_set_should_be_in",
                 apply=_fix_not_in_counter,
                 symptoms=("wrong",)),
            Rule(name="misapplied_double_replace_chain",
                 apply=_fix_double_replace_chain,
                 symptoms=("wrong",)),
            Rule(name="mod_equality_should_be_equality",
                 apply=_fix_mod_equality,
                 symptoms=("wrong",)),
            Rule(name="range_off_by_one",
                 apply=_fix_range_off_by_one,
                 symptoms=("wrong",)),
            Rule(name="int_literal_digit_compare_should_be_str",
                 apply=_fix_int_literal_digit_compare,
                 symptoms=("wrong",)),
            Rule(name="bare_constant_or_truthy_slip",
                 apply=_fix_bare_constant_or,
                 symptoms=("wrong",)),
            Rule(name="eq_or_in_parens_should_be_in_tuple",
                 apply=_fix_or_in_parens_compare,
                 symptoms=("wrong",)),
            Rule(name="int_set_literal_vs_string_input",
                 apply=_fix_int_set_literal_vs_input,
                 symptoms=("wrong",)),
            Rule(name="remove_leftover_debug_print",
                 apply=_remove_debug_print,
                 symptoms=("wrong",)),
        ]