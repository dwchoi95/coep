"""
Repair module for the "unique_day / unique_month / contains_unique_day"
assignment.

Each rule below targets one recurring misconception observed across the
worked repairs, located via a structural AST pattern (not literal source
text) and applied as a minimal source-span splice.
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


def _apply_edits(source, edits):
    """edits: list of (start, end, text) non-overlapping offsets into source."""
    edits = sorted(edits, key=lambda x: -x[0])
    new_src = source
    for s, e, text in edits:
        new_src = new_src[:s] + text + new_src[e:]
    return new_src


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


VOCAB = {"day", "days", "month", "months", "date", "dates"}


# ----------------------------------------------------------------------
# Rule: undefined day/month/date reference mismatched with parameter name
# ----------------------------------------------------------------------

def _undefined_vocab_name(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if func.name not in ("unique_day", "unique_month"):
            continue
        if not func.args.args:
            continue
        P = func.args.args[0].arg

        bound = {P}
        shadowed = False
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                bound.add(n.id)
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                bound.add(n.target.id)
                if n.target.id == P:
                    shadowed = True
        if shadowed:
            continue  # handled by the shadow-specific rule

        free_nodes = []
        free_ids = set()
        for n in ast.walk(func):
            if (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                    and n.id in VOCAB and n.id != P and n.id not in bound):
                free_nodes.append(n)
                free_ids.add(n.id)
        if len(free_ids) != 1:
            continue
        F = next(iter(free_ids))

        # Candidate A: rename the undefined references to the parameter name
        edits_a = [(*_span(source, n), P) for n in free_nodes]
        src_a = _apply_edits(source, edits_a)
        if src_a != source:
            out.append(src_a)

        # Candidate B: rename the parameter to the name actually used in body
        edits_b = []
        arg0 = func.args.args[0]
        edits_b.append((*_span(source, arg0), F))
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and n.id == P:
                edits_b.append((*_span(source, n), F))
        src_b = _apply_edits(source, edits_b)
        if src_b != source:
            out.append(src_b)
    return out


# ----------------------------------------------------------------------
# Rule: parameter shadowed by a `for <param> in ...` loop plus an
# undefined day/month reference inside that loop
# ----------------------------------------------------------------------

def _shadowed_param_undefined(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if func.name not in ("unique_day", "unique_month"):
            continue
        if not func.args.args:
            continue
        P = func.args.args[0].arg

        bound = {P}
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                bound.add(n.id)

        shadow_for = None
        for node in ast.walk(func):
            if (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                    and node.target.id == P):
                shadow_for = node
                break
        if shadow_for is None:
            continue

        free_ids = set()
        for n in ast.walk(shadow_for):
            if (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                    and n.id in VOCAB and n.id != P and n.id not in bound):
                free_ids.add(n.id)
        if len(free_ids) != 1:
            continue
        F = next(iter(free_ids))

        new_name = "_item" if "_item" not in bound else "_item2"
        edits = []
        for n in ast.walk(shadow_for):
            if isinstance(n, ast.Name):
                if n.id == P:
                    edits.append((*_span(source, n), new_name))
                elif n.id == F:
                    edits.append((*_span(source, n), P))
        if not edits:
            continue
        new_src = _apply_edits(source, edits)
        if new_src != source:
            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: counter initialised to 0 is compared against itself instead of
# the parameter, and a separate (undefined) variable is incremented
# instead of the counter
# ----------------------------------------------------------------------

def _counter_selfcompare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if func.name not in ("unique_day", "unique_month"):
            continue
        if not func.args.args:
            continue
        P = func.args.args[0].arg

        counter_name = None
        for stmt in func.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value == 0):
                counter_name = stmt.targets[0].id
                break
        if counter_name is None or counter_name == P:
            continue

        edits = []
        found = False
        for node in ast.walk(func):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                    and isinstance(node.ops[0], ast.Eq):
                cands = [node.left] + list(node.comparators)
                for c in cands:
                    if isinstance(c, ast.Name) and c.id == counter_name:
                        edits.append((*_span(source, c), P))
                        found = True
        if not found:
            continue

        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.BinOp)
                    and isinstance(node.value.op, ast.Add)):
                tgt = node.targets[0]
                left = node.value.left
                if (isinstance(left, ast.Name) and left.id == tgt.id
                        and tgt.id != counter_name and tgt.id != P):
                    edits.append((*_span(source, tgt), counter_name))
                    edits.append((*_span(source, left), counter_name))

        new_src = _apply_edits(source, edits)
        if new_src != source:
            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: uniqueness threshold uses >,>=,<,<= against 1/2 instead of == 1
# ----------------------------------------------------------------------

def _fix_uniqueness_threshold(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    bad_ops = (ast.Gt, ast.GtE, ast.Lt, ast.LtE)

    def is_bool_const(node, want):
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return node.value is want
        if isinstance(node, ast.Name):
            return node.id.lower() == str(want).lower()
        return False

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if func.name not in ("unique_day", "unique_month"):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Compare):
                cmp = node.value
                if (len(cmp.ops) == 1 and isinstance(cmp.ops[0], bad_ops)
                        and isinstance(cmp.comparators[0], ast.Constant)
                        and isinstance(cmp.comparators[0].value, int)
                        and not isinstance(cmp.comparators[0].value, bool)):
                    ls, le = _span(source, cmp.left)
                    left_text = source[ls:le]
                    new_src = _splice(source, cmp, left_text + " == 1")
                    if new_src != source:
                        out.append(new_src)

            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                cmp = node.test
                if not (len(cmp.ops) == 1 and isinstance(cmp.ops[0], bad_ops)
                        and isinstance(cmp.comparators[0], ast.Constant)
                        and isinstance(cmp.comparators[0].value, int)
                        and not isinstance(cmp.comparators[0].value, bool)):
                    continue
                body_is_false = (len(node.body) == 1
                                  and isinstance(node.body[0], ast.Return)
                                  and node.body[0].value is not None
                                  and is_bool_const(node.body[0].value, False))
                if not body_is_false:
                    continue
                ok = False
                if node.orelse:
                    ok = (len(node.orelse) == 1
                          and isinstance(node.orelse[0], ast.Return)
                          and node.orelse[0].value is not None
                          and is_bool_const(node.orelse[0].value, True))
                else:
                    ok = True  # assume fallthrough `return True`
                if ok:
                    ls, le = _span(source, cmp.left)
                    left_text = source[ls:le]
                    new_src = _splice(source, cmp, left_text + " != 1")
                    if new_src != source:
                        out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: contains_unique_day counts matches and requires counter == 1
# (should be "at least one")
# ----------------------------------------------------------------------

def _fix_contains_counter_eq(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != "contains_unique_day":
            continue
        calls_unique_day = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "unique_day" for n in ast.walk(func))
        if not calls_unique_day:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                cmp = node.test
                if (len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq)
                        and isinstance(cmp.left, ast.Name)
                        and isinstance(cmp.comparators[0], ast.Constant)
                        and cmp.comparators[0].value == 1):
                    counter_name = cmp.left.id
                    incremented = any(
                        isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
                        and n.target.id == counter_name for n in ast.walk(func))
                    if incremented:
                        ls, le = _span(source, cmp.left)
                        left_text = source[ls:le]
                        new_src = _splice(source, cmp, left_text + " >= 1")
                        if new_src != source:
                            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: loop body returns True/False on the very first element instead
# of continuing to the next one
# ----------------------------------------------------------------------

def _fix_early_loop_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []

    def is_bool_const(node, want):
        if node is None:
            return False
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return node.value is want
        if isinstance(node, ast.Name):
            return node.id.lower() == str(want).lower()
        return False

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != "contains_unique_day":
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.For):
                continue
            body = node.body
            if len(body) != 1 or not isinstance(body[0], ast.If):
                continue
            ifn = body[0]
            if not (len(ifn.body) == 1 and isinstance(ifn.body[0], ast.Return)
                    and is_bool_const(ifn.body[0].value, True)):
                continue
            if not (len(ifn.orelse) == 1 and isinstance(ifn.orelse[0], ast.Return)
                    and is_bool_const(ifn.orelse[0].value, False)):
                continue
            ret_false_node = ifn.orelse[0]
            s_rf, e_rf = _span(source, ret_false_node)
            fs, fe = _span(source, node)
            indent = " " * node.col_offset
            insertion = "\n" + indent + "return False"
            edits = [
                (s_rf, e_rf, "continue"),
                (fe, fe, insertion),
            ]
            new_src = _apply_edits(source, edits)
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: tuple accumulator appended via `x = x + item` instead of
# `x = x + (item,)`
# ----------------------------------------------------------------------

def _fix_tuple_append_wrap(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        tuple_vars = set()
        for n in ast.walk(func):
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.Tuple) and len(n.value.elts) == 0):
                tuple_vars.add(n.targets[0].id)
        if not tuple_vars:
            continue
        for n in ast.walk(func):
            target_name = None
            value_node = None
            if (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
                    and isinstance(n.op, ast.Add)):
                target_name = n.target.id
                value_node = n.value
            elif (isinstance(n, ast.Assign) and len(n.targets) == 1
                  and isinstance(n.targets[0], ast.Name)
                  and isinstance(n.value, ast.BinOp) and isinstance(n.value.op, ast.Add)
                  and isinstance(n.value.left, ast.Name)
                  and n.value.left.id == n.targets[0].id):
                target_name = n.targets[0].id
                value_node = n.value.right
            if target_name and target_name in tuple_vars and value_node is not None:
                if not isinstance(value_node, ast.Tuple):
                    s, e = _span(source, value_node)
                    text = source[s:e]
                    new_src = source[:s] + "(" + text + ",)" + source[e:]
                    if new_src != source:
                        out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: call to a misspelled helper (e.g. unique_date) instead of
# unique_day
# ----------------------------------------------------------------------

def _fix_typo_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    if "unique_day" not in defined:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fid = node.func.id
            if fid != "unique_day" and fid not in defined and fid.startswith("unique_"):
                new_src = _splice(source, node.func, "unique_day")
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: flag variable toggled inside the loop, but the function ends
# with a hard-coded `return True` instead of returning the flag
# ----------------------------------------------------------------------

def _fix_flag_return_true(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("unique_day", "unique_month"):
            continue
        if not func.body:
            continue
        flagname = None
        for stmt in func.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value in (False, 0)):
                flagname = stmt.targets[0].id
                break
        if flagname is None:
            continue
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue
        toggled = any(
            isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id == flagname
            for n in ast.walk(func))
        if not toggled:
            continue
        new_src = _splice(source, last.value, flagname)
        if new_src != source:
            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: boolean accumulator used via `x = x or expr` without being
# initialised first
# ----------------------------------------------------------------------

def _fix_missing_flag_init(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != "contains_unique_day":
            continue
        bound_before = {a.arg for a in func.args.args}
        for stmt in func.body:
            if isinstance(stmt, ast.For):
                for n in ast.walk(stmt):
                    if (isinstance(n, ast.Assign) and len(n.targets) == 1
                            and isinstance(n.targets[0], ast.Name)
                            and isinstance(n.value, ast.BoolOp)):
                        tname = n.targets[0].id
                        uses_self = any(isinstance(v, ast.Name) and v.id == tname
                                        for v in n.value.values)
                        if uses_self and tname not in bound_before:
                            fs, fe = _span(source, stmt)
                            indent = " " * stmt.col_offset
                            insertion = f"{tname} = False\n{indent}"
                            new_src = source[:fs] + insertion + source[fs:]
                            if new_src != source:
                                out.append(new_src)
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                bound_before.add(stmt.targets[0].id)
    return out


# ----------------------------------------------------------------------
# Rule: a premature top-level `return <expr>` leaves correct logic
# unreachable right below it
# ----------------------------------------------------------------------

def _remove_premature_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if func.name not in ("unique_day", "unique_month", "contains_unique_day"):
            continue
        body = func.body
        if len(body) < 2:
            continue
        for stmt in body[:-1]:
            if isinstance(stmt, ast.Return) and stmt.value is not None \
                    and not isinstance(stmt.value, ast.Compare):
                s = starts[stmt.lineno - 1]
                e = starts[stmt.end_lineno]
                new_src = source[:s] + source[e:]
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="undefined_vocab_name_vs_param",
                apply=_undefined_vocab_name,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="shadowed_param_undefined_name",
                apply=_shadowed_param_undefined,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="counter_selfcompare_and_wrong_increment",
                apply=_counter_selfcompare,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="uniqueness_threshold_should_be_eq_1",
                apply=_fix_uniqueness_threshold,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_counter_should_be_any_not_eq1",
                apply=_fix_contains_counter_eq,
                symptoms=("wrong",),
            ),
            Rule(
                name="early_loop_return_should_continue",
                apply=_fix_early_loop_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="tuple_accumulator_missing_singleton_wrap",
                apply=_fix_tuple_append_wrap,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="typo_call_to_unique_day",
                apply=_fix_typo_call,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="flag_toggle_but_hardcoded_return_true",
                apply=_fix_flag_return_true,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_flag_initialization",
                apply=_fix_missing_flag_init,
                symptoms=("err:UnboundLocalError", "err:NameError"),
            ),
            Rule(
                name="premature_return_hides_correct_logic",
                apply=_remove_premature_return,
                symptoms=("wrong",),
            ),
        ]