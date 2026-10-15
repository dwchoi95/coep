"""
Repair module for the "Unique dates and months" assignment.

Targets common, well-defined misconceptions seen across buggy submissions:
  - using a free/undefined identifier instead of the function's own parameter
  - typo'd helper-function names (unique_date -> unique_day)
  - off-by-one / inclusive-exclusive uniqueness-count comparisons
  - tuple accumulation missing the trailing comma that makes a 1-tuple
  - using `.append` on a tuple literal instead of a list
  - returning False on the first non-matching loop iteration instead of
    continuing to scan (and missing the final `return False`)
  - counters / boolean accumulators used before being initialized
  - `<=` where `<` was intended against `len(...)` in a while loop
  - bare lowercase `true`/`false` identifiers
  - functions missing a trailing `return False` fallback
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


def _apply_edits(source, edits):
    """edits: list of (start, end, replacement text)."""
    if not edits:
        return None
    uniq = {}
    for s, e, rep in edits:
        uniq[(s, e)] = rep
    ordered = sorted(uniq.items(), key=lambda kv: kv[0][0], reverse=True)
    new_source = source
    for (s, e), rep in ordered:
        new_source = new_source[:s] + rep + new_source[e:]
    return new_source if new_source != source else None


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Rule 1: free identifier that should be the function's own parameter.
# ---------------------------------------------------------------------------

def _own_load_names(func):
    """Name(Load) nodes that belong to `func`'s own scope (not nested defs,
    not Call targets, which are handled separately)."""
    results = []

    def visit(node):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                visit(node.func)
            else:
                for kw_part in ():
                    pass
            for a in node.args:
                visit(a)
            for kw in node.keywords:
                visit(kw.value)
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                results.append(child)
            visit(child)

    visit(func)
    return results


def _fix_undefined_names(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        import builtins
        BUILTINS = set(dir(builtins))
        top_funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        edits = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            params = [a.arg for a in func.args.args]
            if not params:
                continue
            target_param = params[0]
            bound = set(params)
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    bound.add(node.id)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    bound.add(node.name)
                elif isinstance(node, ast.Lambda):
                    bound |= {a.arg for a in node.args.args}
                elif isinstance(node, ast.ExceptHandler) and node.name:
                    bound.add(node.name)
            allowed = bound | top_funcs | BUILTINS
            for node in _own_load_names(func):
                if node.id not in allowed and node.id != target_param:
                    s, e = _span(source, node)
                    edits.append((s, e, target_param))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 2: typo'd helper call unique_date(...) -> unique_day(...)
# ---------------------------------------------------------------------------

def _fix_unique_date_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        if 'unique_day' not in defined:
            return []
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
               and node.func.id == 'unique_date':
                s, e = _span(source, node.func)
                edits.append((s, e, 'unique_day'))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 3: wrong threshold/operator for "exactly one" uniqueness checks.
# ---------------------------------------------------------------------------

def _fix_uniqueness_threshold(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Compare) \
               and len(node.value.ops) == 1 and len(node.value.comparators) == 1:
                cmp = node.value
                op = cmp.ops[0]
                comparator = cmp.comparators[0]
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, int) \
                   and not isinstance(comparator.value, bool):
                    n = comparator.value
                    bad = (
                        (isinstance(op, ast.LtE) and n == 1) or
                        (isinstance(op, ast.GtE) and n == 2) or
                        (isinstance(op, ast.Lt) and n == 2) or
                        (isinstance(op, ast.Gt) and n == 1)
                    )
                    if bad:
                        ls, le = _span(source, cmp.left)
                        left_text = source[ls:le]
                        s, e = _span(source, cmp)
                        edits.append((s, e, f"{left_text} == 1"))

            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
               and len(node.test.ops) == 1 and len(node.test.comparators) == 1 \
               and len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                cmp = node.test
                op = cmp.ops[0]
                comparator = cmp.comparators[0]
                ret_val = node.body[0].value
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, int) \
                   and not isinstance(comparator.value, bool) \
                   and isinstance(ret_val, ast.Constant) and isinstance(ret_val.value, bool):
                    n = comparator.value
                    ls, le = _span(source, cmp.left)
                    left_text = source[ls:le]
                    if ret_val.value is False and (
                        (isinstance(op, ast.Gt) and n == 1) or
                        (isinstance(op, ast.GtE) and n == 2)
                    ):
                        s, e = _span(source, cmp)
                        edits.append((s, e, f"{left_text} != 1"))
                    elif ret_val.value is True and (
                        (isinstance(op, ast.LtE) and n == 1) or
                        (isinstance(op, ast.Lt) and n == 2)
                    ):
                        s, e = _span(source, cmp)
                        edits.append((s, e, f"{left_text} == 1"))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 4: tuple accumulation missing the trailing comma (x = x + i).
# ---------------------------------------------------------------------------

def _fix_tuple_concat_comma(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        tuple_inits = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
               and isinstance(node.targets[0], ast.Name) \
               and isinstance(node.value, ast.Tuple) and len(node.value.elts) == 0:
                tuple_inits.add(node.targets[0].id)

        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
               and isinstance(node.targets[0], ast.Name):
                target_name = node.targets[0].id
                if target_name not in tuple_inits:
                    continue
                val = node.value
                if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                    left = val.left
                    right = val.right
                    if isinstance(left, ast.Name) and left.id == target_name \
                       and not isinstance(right, ast.Tuple):
                        s, e = _span(source, right)
                        right_text = source[s:e]
                        edits.append((s, e, f"({right_text},)"))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 5: `.append` used on a tuple literal -> should be a list.
# ---------------------------------------------------------------------------

def _fix_tuple_append(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        edits = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            empties = {}
            for node in ast.walk(func):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                   and isinstance(node.targets[0], ast.Name) \
                   and isinstance(node.value, ast.Tuple) and len(node.value.elts) == 0:
                    empties[node.targets[0].id] = node.value
            appended = set()
            for node in ast.walk(func):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                   and node.func.attr == 'append' and isinstance(node.func.value, ast.Name):
                    appended.add(node.func.value.id)
            for name, tup_node in empties.items():
                if name in appended:
                    s, e = _span(source, tup_node)
                    edits.append((s, e, "[]"))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 6: returning False on the first non-matching loop iteration instead
# of continuing to scan the rest of the list.
# ---------------------------------------------------------------------------

def _fix_early_false_return_in_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        edits = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            for node in ast.walk(func):
                if isinstance(node, ast.For) and len(node.body) == 1 \
                   and isinstance(node.body[0], ast.If):
                    ifnode = node.body[0]
                    if ifnode.orelse and len(ifnode.orelse) == 1 \
                       and isinstance(ifnode.orelse[0], ast.Return) \
                       and isinstance(ifnode.orelse[0].value, ast.Constant) \
                       and ifnode.orelse[0].value.value is False:
                        has_success_return = any(
                            isinstance(n2, ast.Return)
                            for stmt in ifnode.body
                            for n2 in ast.walk(stmt)
                        )
                        if has_success_return:
                            s, e = _span(source, ifnode.orelse[0])
                            edits.append((s, e, "continue"))
                            if func.body and func.body[-1] is node:
                                fs, fe = _span(source, node)
                                indent = ' ' * node.col_offset
                                edits.append((fe, fe, f"\n{indent}return False"))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 7: a counter/boolean accumulator used (via += or self-referential
# `x = x or ...`) without ever being initialized.
# ---------------------------------------------------------------------------

def _fix_missing_var_init(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        insertions = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            params = {a.arg for a in func.args.args}
            assigned_plain = set()
            self_ref = {}
            for node in ast.walk(func):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                   and isinstance(node.targets[0], ast.Name):
                    tgt = node.targets[0].id
                    val = node.value
                    names_in_val = {n.id for n in ast.walk(val) if isinstance(n, ast.Name)}
                    if tgt in names_in_val:
                        kind = 'bool' if isinstance(val, ast.BoolOp) else 'num'
                        self_ref.setdefault(tgt, kind)
                    else:
                        assigned_plain.add(tgt)
                elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                    self_ref.setdefault(node.target.id, 'num')
            if not func.body:
                continue
            first_stmt = func.body[0]
            indent = ' ' * first_stmt.col_offset
            s, _e = _span(source, first_stmt)
            for name, kind in self_ref.items():
                if name in assigned_plain or name in params:
                    continue
                init_val = 'False' if kind == 'bool' else '0'
                insertions.append((s, s, f"{name} = {init_val}\n{indent}"))
        new_source = _apply_edits(source, insertions)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 8: off-by-one `while i <= len(seq)` index bound.
# ---------------------------------------------------------------------------

def _fix_while_len_off_by_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) \
               and len(node.test.ops) == 1 and len(node.test.comparators) == 1:
                op = node.test.ops[0]
                comp = node.test.comparators[0]
                if isinstance(op, ast.LtE) and isinstance(comp, ast.Call) \
                   and isinstance(comp.func, ast.Name) and comp.func.id == 'len':
                    ls, le = _span(source, node.test.left)
                    cs, ce = _span(source, comp)
                    left_text = source[ls:le]
                    comp_text = source[cs:ce]
                    s, e = _span(source, node.test)
                    edits.append((s, e, f"{left_text} < {comp_text}"))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 9: bare lowercase `true`/`false` identifiers.
# ---------------------------------------------------------------------------

def _fix_lowercase_bool(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) \
               and node.id in ('true', 'false'):
                s, e = _span(source, node)
                edits.append((s, e, 'True' if node.id == 'true' else 'False'))
        new_source = _apply_edits(source, edits)
        return [new_source] if new_source else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Rule 10: function body falls off the end without a boolean fallback.
# ---------------------------------------------------------------------------

def _append_missing_return_false(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        target_names = {'unique_day', 'unique_month', 'contains_unique_day'}
        insertions = []
        for func in [n for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef) and n.name in target_names]:
            if not func.body:
                continue
            last = func.body[-1]
            needs = False
            if isinstance(last, ast.For) and not last.orelse:
                needs = True
            elif isinstance(last, ast.If) and not last.orelse:
                needs = True
            if needs:
                _s, e = _span(source, last)
                indent = ' ' * last.col_offset
                insertions.append((e, e, f"\n{indent}return False"))
        new_source = _apply_edits(source, insertions)
        return [new_source] if new_source else []
    except Exception:
        return []


class Fixer:
    def rules(self):
        return [
            Rule(
                name="undefined_name_should_be_param",
                apply=_fix_undefined_names,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="unique_date_typo",
                apply=_fix_unique_date_typo,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="uniqueness_threshold_off_by_one",
                apply=_fix_uniqueness_threshold,
                symptoms=("wrong",),
            ),
            Rule(
                name="tuple_concat_missing_comma",
                apply=_fix_tuple_concat_comma,
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="tuple_should_be_list_for_append",
                apply=_fix_tuple_append,
                symptoms=("err:AttributeError",),
            ),
            Rule(
                name="early_false_return_should_continue",
                apply=_fix_early_false_return_in_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_accumulator_init",
                apply=_fix_missing_var_init,
                symptoms=("err:NameError", "err:UnboundLocalError", "wrong"),
            ),
            Rule(
                name="while_len_off_by_one",
                apply=_fix_while_len_off_by_one,
                symptoms=("err:IndexError", "timeout"),
            ),
            Rule(
                name="lowercase_true_false",
                apply=_fix_lowercase_bool,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="missing_trailing_return_false",
                apply=_append_missing_return_false,
                symptoms=("wrong",),
            ),
        ]