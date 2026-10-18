import ast
import builtins as _builtins

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

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


def _apply_edits(source, edits):
    """edits: list of (start, end, replacement). Applied right-to-left."""
    if not edits:
        return None
    edits = sorted(edits, key=lambda e: e[0], reverse=True)
    out = source
    for s, e, rep in edits:
        out = out[:s] + rep + out[e:]
    return out


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _subscript_slice_node(node):
    sl = node.slice
    if isinstance(sl, ast.Index):  # py < 3.9
        return sl.value
    return sl


_BUILTIN_NAMES = set(dir(_builtins)) | {"True", "False", "None"}


# ---------------------------------------------------------------------------
# Rule 1: parameter/body name mismatch (NameError) for day/date/month words
# ---------------------------------------------------------------------------

_CONFUSABLE = {"day", "date", "month"}


def _rename_undefined_confusable(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        params = [a.arg for a in node.args.args]
        if not params:
            continue
        first_param = params[0]
        local_names = set(params)
        try:
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    local_names.add(n.id)
                if isinstance(n, ast.arg):
                    local_names.add(n.arg)
        except Exception:
            continue

        bad_words = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id in _CONFUSABLE and n.id not in local_names and n.id != first_param:
                    bad_words.add(n.id)

        if len(bad_words) != 1:
            continue
        bad = next(iter(bad_words))

        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == bad:
                s, e = _span(source, n)
                edits.append((s, e, first_param))

    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 2: lowercase true/false used as identifiers
# ---------------------------------------------------------------------------

def _fix_lowercase_bool(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in ("true", "false"):
            s, e = _span(source, n)
            edits.append((s, e, "True" if n.id == "true" else "False"))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 3: contains_unique_day missing a trailing `return False`
# ---------------------------------------------------------------------------

def _append_return_false(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "contains_unique_day":
            continue
        if not node.body:
            continue
        last = node.body[-1]
        if isinstance(last, ast.Return):
            continue
        indent = " " * node.body[0].col_offset
        _, insert_pos = _span(source, last)
        new_src = source[:insert_pos] + "\n" + indent + "return False" + source[insert_pos:]
        out.append(new_src)
    return out


# ---------------------------------------------------------------------------
# Rule 4: premature `else: return False` inside a for-loop's if, should
# continue scanning instead of bailing out on the first mismatch.
# ---------------------------------------------------------------------------

def _loop_else_return_to_continue(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and len(node.body) == 1 and isinstance(node.body[0], ast.If):
            ifnode = node.body[0]
            if len(ifnode.orelse) == 1 and isinstance(ifnode.orelse[0], ast.Return):
                retnode = ifnode.orelse[0]
                s, e = _span(source, retnode)
                edits.append((s, e, "continue"))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 5: `counter <= 1` should be `counter == 1`
# ---------------------------------------------------------------------------

def _lte1_to_eq1(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            right = node.comparators[0]
            if isinstance(op, ast.LtE) and isinstance(right, ast.Constant) and right.value == 1:
                ls, le = _span(source, node.left)
                rs, re_ = _span(source, right)
                new_text = source[ls:le] + " == " + source[rs:re_]
                s, e = _span(source, node)
                edits.append((s, e, new_text))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 6: wrong tuple index used when comparing against month/day parameter
# ---------------------------------------------------------------------------

def _fix_swapped_index(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            pairs = [(node.left, node.comparators[0]), (node.comparators[0], node.left)]
            for a, b in pairs:
                if isinstance(a, ast.Name) and isinstance(b, ast.Subscript):
                    sl = _subscript_slice_node(b)
                    if not isinstance(sl, ast.Constant) or not isinstance(sl.value, int):
                        continue
                    if a.id == "month" and sl.value != 0:
                        s, e = _span(source, sl)
                        edits.append((s, e, "0"))
                    elif a.id in ("day", "date") and sl.value != 1:
                        s, e = _span(source, sl)
                        edits.append((s, e, "1"))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 7: call to a misspelled helper function (unique_date -> unique_day)
# ---------------------------------------------------------------------------

def _fix_typo_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "unique_day" not in defined or "unique_date" in defined:
        return []
    edits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "unique_date":
            s, e = _span(source, n.func)
            edits.append((s, e, "unique_day"))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 8: appending a raw element instead of a singleton tuple to a tuple
# accumulator (count = count + i  ->  count = count + (i,))
# ---------------------------------------------------------------------------

def _fix_tuple_concat(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        tuple_vars = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                if isinstance(n.value, ast.Tuple) and len(n.value.elts) == 0:
                    tuple_vars.add(n.targets[0].id)

        for n in ast.walk(node):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                target_name = n.targets[0].id
                if target_name not in tuple_vars:
                    continue
                val = n.value
                if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                    if isinstance(val.left, ast.Name) and val.left.id == target_name:
                        right = val.right
                        if isinstance(right, ast.Name):
                            s, e = _span(source, right)
                            text = source[s:e]
                            edits.append((s, e, "(" + text + ",)"))
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                target_name = n.target.id
                if target_name not in tuple_vars:
                    continue
                if isinstance(n.op, ast.Add) and isinstance(n.value, ast.Name):
                    s, e = _span(source, n.value)
                    text = source[s:e]
                    edits.append((s, e, "(" + text + ",)"))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 9: contains_unique_day calls unique_day without ever checking the
# month, so it returns True for a unique day in the wrong month.
# ---------------------------------------------------------------------------

def _fix_missing_month_check(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "contains_unique_day":
            continue
        params = [a.arg for a in node.args.args]
        if not params:
            continue
        month_param = params[0]
        s0, e0 = _span(source, node)
        body_text = source[s0:e0]
        if (month_param + " ==") in body_text or ("== " + month_param) in body_text \
           or (month_param + " in") in body_text or ("in " + month_param) in body_text:
            continue

        edits = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.For) and isinstance(sub.target, ast.Name):
                loopvar = sub.target.id
                for sn in ast.walk(sub):
                    if isinstance(sn, ast.If):
                        test = sn.test
                        if isinstance(test, ast.Call) and isinstance(test.func, ast.Name) \
                           and test.func.id == "unique_day":
                            s, e = _span(source, test)
                            test_text = source[s:e]
                            new_test = "{}[0] == {} and ({})".format(loopvar, month_param, test_text)
                            edits.append((s, e, new_test))
        patched = _apply_edits(source, edits)
        if patched is not None:
            out.append(patched)
    return out


# ---------------------------------------------------------------------------
# Rule 10: a stub function whose only statement is a bare `return`
# ---------------------------------------------------------------------------

def _bare_return_to_false(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.body:
            continue
        last = node.body[-1]
        if isinstance(last, ast.Return) and last.value is None:
            s, e = _span(source, last)
            edits.append((s, e, "return False"))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------
# Rule 11: generic strict/non-strict comparator relaxation (cheap fallback)
# ---------------------------------------------------------------------------

def _relax_strict_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            right = node.comparators[0]
            if isinstance(right, ast.Constant) and isinstance(right.value, int):
                new_op = None
                if isinstance(op, ast.Lt):
                    new_op = "<="
                elif isinstance(op, ast.Gt):
                    new_op = ">="
                if new_op is not None:
                    ls, le = _span(source, node.left)
                    rs, re_ = _span(source, right)
                    new_text = source[ls:le] + " " + new_op + " " + source[rs:re_]
                    s, e = _span(source, node)
                    edits.append((s, e, new_text))
    patched = _apply_edits(source, edits)
    return [patched] if patched is not None else []


# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="rename_undefined_confusable_param",
                apply=_rename_undefined_confusable,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="lowercase_bool_literal",
                apply=_fix_lowercase_bool,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="append_missing_return_false",
                apply=_append_return_false,
                symptoms=("wrong",),
            ),
            Rule(
                name="loop_else_return_to_continue",
                apply=_loop_else_return_to_continue,
                symptoms=("wrong",),
            ),
            Rule(
                name="lte1_counter_to_eq1",
                apply=_lte1_to_eq1,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_swapped_tuple_index",
                apply=_fix_swapped_index,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_typo_function_call",
                apply=_fix_typo_call,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="fix_tuple_concat_missing_comma",
                apply=_fix_tuple_concat,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_missing_month_check",
                apply=_fix_missing_month_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_return_to_false",
                apply=_bare_return_to_false,
                symptoms=("wrong",),
            ),
            Rule(
                name="relax_strict_compare",
                apply=_relax_strict_compare,
                symptoms=("wrong",),
            ),
        ]