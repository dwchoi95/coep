import ast

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# Generic helpers
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


def _slice_value(s):
    return s.value if isinstance(s, ast.Index) else s


def _const_index(slice_node):
    s = _slice_value(slice_node)
    if isinstance(s, ast.Constant) and isinstance(s.value, int):
        return s.value
    return None


_OP_TEXT = {ast.Lt: '<', ast.Gt: '>', ast.LtE: '<=', ast.GtE: '>='}
_OP_FLIP = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}


def _safe(fn):
    def wrapper(source):
        try:
            results = fn(source)
        except Exception:
            return []
        out = []
        for r in results:
            if isinstance(r, str) and r != source and r not in out:
                out.append(r)
        return out
    return wrapper


def _apply_edits(source, edits):
    """edits: list of (start, end, replacement_text), applied left to right."""
    edits = sorted(edits, key=lambda x: x[0])
    new_source = source
    offset = 0
    for s, e, rep in edits:
        new_source = new_source[:s + offset] + rep + new_source[e + offset:]
        offset += len(rep) - (e - s)
    return new_source


# ---------------------------------------------------------------------------
# Rule 1: inside a "for x in lst: if cmp(track, x): <assign>" loop, the body
# assignment that should set track = loopvar is wrong (undefined name, typo,
# swapped target/value, or not even an assignment).
# ---------------------------------------------------------------------------

def _fix_extremum_assignment(source):
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in ast.walk(func):
            if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
                continue
            loopvar = node.target.id
            for stmt in node.body:
                if not isinstance(stmt, ast.If):
                    continue
                cond = stmt.test
                if not (isinstance(cond, ast.Compare) and len(cond.ops) == 1):
                    continue
                left, right = cond.left, cond.comparators[0]

                def subscript_name(n):
                    if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
                        return n.value.id
                    return None

                ln, rn = subscript_name(left), subscript_name(right)
                if ln is None or rn is None:
                    continue
                if (ln == loopvar) == (rn == loopvar):
                    continue
                track = rn if ln == loopvar else ln
                if len(stmt.body) != 1:
                    continue
                target_stmt = stmt.body[0]
                expected = f"{track} = {loopvar}"
                s, e = _span(source, target_stmt)
                cur_text = source[s:e]
                if cur_text.strip() != expected:
                    out.append(source[:s] + expected + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 2: function has exactly one accumulator variable initialised as `[]`,
# but append()/return reference an undefined name instead of that
# accumulator.
# ---------------------------------------------------------------------------

def _fix_accumulator_misuse(source):
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = set(a.arg for a in func.args.args)
        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                defined.add(n.target.id)

        acc_candidates = []
        for stmt in func.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.List) and not stmt.value.elts:
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        acc_candidates.append(t.id)
        if len(acc_candidates) != 1:
            continue
        acc = acc_candidates[0]

        edits = []
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'append':
                if isinstance(n.func.value, ast.Name) and n.func.value.id != acc \
                        and n.func.value.id not in defined:
                    edits.append(n.func.value)
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) \
                    and n.value.id != acc and n.value.id not in defined:
                edits.append(n.value)
        if not edits:
            continue
        spans = [(*_span(source, nd), acc) for nd in edits]
        out.append(_apply_edits(source, spans))
    return out


# ---------------------------------------------------------------------------
# Rule 3: the accumulator list is correctly built but never (or wrongly)
# returned: missing return, printed instead, or returning the wrong name.
# ---------------------------------------------------------------------------

def _fix_missing_or_wrong_return(source):
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        body = func.body
        if not body:
            continue
        acc_candidates = []
        for stmt in body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.List) and not stmt.value.elts:
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        acc_candidates.append(t.id)
        if len(acc_candidates) != 1:
            continue
        acc = acc_candidates[0]

        used = False
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and n.func.attr == 'append' and isinstance(n.func.value, ast.Name) \
                    and n.func.value.id == acc:
                used = True
                break
        if not used:
            continue

        last = body[-1]
        if isinstance(last, ast.Return):
            if isinstance(last.value, ast.Name):
                if last.value.id != acc:
                    out.append(_splice(source, last.value, acc))
            continue
        if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
            call = last.value
            if isinstance(call.func, ast.Name) and call.func.id == 'print':
                out.append(_splice(source, last, f"return {acc}"))
            continue
        indent = ' ' * last.col_offset
        s, e = _span(source, last)
        out.append(source[:e] + f"\n{indent}return {acc}" + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 4: a duplicate "acc.append(x)" statement right after the while loop
# that already appends every selected element inside its body.
# ---------------------------------------------------------------------------

def _remove_duplicate_trailing_append(source):
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        body = func.body
        for i, stmt in enumerate(body):
            if not isinstance(stmt, ast.While) or not stmt.body:
                continue
            last_in_while = stmt.body[-1]
            if not (isinstance(last_in_while, ast.Expr) and isinstance(last_in_while.value, ast.Call)):
                continue
            c1 = last_in_while.value
            if not (isinstance(c1.func, ast.Attribute) and c1.func.attr == 'append'
                    and isinstance(c1.func.value, ast.Name) and c1.args
                    and isinstance(c1.args[0], ast.Name)):
                continue
            acc_name, arg_name = c1.func.value.id, c1.args[0].id
            if i + 1 >= len(body):
                continue
            nxt = body[i + 1]
            if not (isinstance(nxt, ast.Expr) and isinstance(nxt.value, ast.Call)):
                continue
            c2 = nxt.value
            if (isinstance(c2.func, ast.Attribute) and c2.func.attr == 'append'
                    and isinstance(c2.func.value, ast.Name) and c2.func.value.id == acc_name
                    and c2.args and isinstance(c2.args[0], ast.Name) and c2.args[0].id == arg_name):
                s, e = _span(source, nxt)
                out.append(source[:s] + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 5: "acc.append(lst.pop(i))" where i is a stale range()-index instead
# of the tracked extremum element -> use lst.remove(extremum) instead.
# ---------------------------------------------------------------------------

def _fix_pop_index_bug(source):
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for stmt in ast.walk(func):
            if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
                continue
            call = stmt.value
            if not (isinstance(call.func, ast.Attribute) and call.func.attr == 'append'
                    and isinstance(call.func.value, ast.Name) and call.args):
                continue
            inner = call.args[0]
            if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == 'pop' and isinstance(inner.func.value, ast.Name)
                    and inner.args and isinstance(inner.args[0], ast.Name)):
                continue
            lstvar = inner.func.value.id
            idxvar = inner.args[0].id
            accvar = call.func.value.id
            extremum = None
            for n2 in ast.walk(func):
                if isinstance(n2, ast.Assign) and len(n2.targets) == 1 and isinstance(n2.targets[0], ast.Name):
                    val = n2.value
                    if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) and val.value.id == lstvar:
                        idx_node = _slice_value(val.slice)
                        if isinstance(idx_node, ast.Name) and idx_node.id == idxvar:
                            extremum = n2.targets[0].id
            if extremum is None:
                continue
            indent = ' ' * stmt.col_offset
            replacement = f"{lstvar}.remove({extremum})\n{indent}{accvar}.append({extremum})"
            out.append(_splice(source, stmt, replacement))
    return out


# ---------------------------------------------------------------------------
# Rule 6: extremum variable initialised as a bare field (seq[0][k]) but later
# reassigned to the whole element inside the loop -> type-inconsistent
# comparisons. Fix the init to the whole element and the bare comparator to
# the matching field.
# ---------------------------------------------------------------------------

def _fix_double_subscript_init(source):
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in ast.walk(func):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                continue
            name = node.targets[0].id
            val = node.value
            if not (isinstance(val, ast.Subscript) and isinstance(val.value, ast.Subscript)):
                continue
            inner = val.value
            outer_idx = _const_index(val.slice)
            if outer_idx is None or not isinstance(inner.value, ast.Name):
                continue
            for n2 in ast.walk(func):
                if not (isinstance(n2, ast.For) and isinstance(n2.target, ast.Name)):
                    continue
                loopvar = n2.target.id
                for s in n2.body:
                    if not isinstance(s, ast.If):
                        continue
                    reassigns = [s2 for s2 in s.body if isinstance(s2, ast.Assign)
                                 and len(s2.targets) == 1 and isinstance(s2.targets[0], ast.Name)
                                 and s2.targets[0].id == name
                                 and isinstance(s2.value, ast.Name) and s2.value.id == loopvar]
                    if not reassigns:
                        continue
                    cond = s.test
                    if not (isinstance(cond, ast.Compare) and len(cond.ops) == 1):
                        continue
                    left, right = cond.left, cond.comparators[0]
                    bare = None
                    if isinstance(left, ast.Name) and left.id == name:
                        bare = left
                    elif isinstance(right, ast.Name) and right.id == name:
                        bare = right
                    if bare is None:
                        continue
                    outer_s, outer_e = _span(source, val)
                    inner_s, inner_e = _span(source, inner)
                    new_init = source[inner_s:inner_e]
                    bare_s, bare_e = _span(source, bare)
                    edits = [(outer_s, outer_e, new_init), (bare_s, bare_e, f"{name}[{outer_idx}]")]
                    out.append(_apply_edits(source, edits))
    return out


# ---------------------------------------------------------------------------
# Rule 7: comparison direction is inverted (ascending instead of descending
# or vice versa) when at least one operand is a subscript expression.
# ---------------------------------------------------------------------------

def _flip_subscript_comparison(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if type(op) not in _OP_FLIP:
                continue
            left, right = node.left, node.comparators[0]
            if not (isinstance(left, ast.Subscript) or isinstance(right, ast.Subscript)):
                continue
            new_op_text = _OP_TEXT[_OP_FLIP[type(op)]]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + f" {new_op_text} " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule 8: returning the result of an in-place mutator (list.sort/reverse/
# append/...) which always returns None.
# ---------------------------------------------------------------------------

def _fix_return_of_inplace_mutator(source):
    tree = ast.parse(source)
    out = []
    mutators = {'sort', 'reverse', 'append', 'insert', 'remove', 'extend', 'pop'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr in mutators \
                    and isinstance(call.func.value, ast.Name):
                varname = call.func.value.id
                indent = ' ' * node.col_offset
                cs, ce = _span(source, call)
                call_text = source[cs:ce]
                replacement = f"{call_text}\n{indent}return {varname}"
                out.append(_splice(source, node, replacement))
    return out


# ---------------------------------------------------------------------------
# Rule 9: the function builds the correct result but ends with print(x)
# instead of return x (no accumulator pattern involved).
# ---------------------------------------------------------------------------

def _fix_trailing_print_to_return(source):
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
            call = last.value
            if isinstance(call.func, ast.Name) and call.func.id == 'print' and len(call.args) == 1:
                as_, ae_ = _span(source, call.args[0])
                arg_text = source[as_:ae_]
                out.append(_splice(source, last, f"return {arg_text}"))
    return out


# ---------------------------------------------------------------------------
# Rule 10: true-division used as a list-slice/index bound (n/2) instead of
# floor division.
# ---------------------------------------------------------------------------

def _fix_index_true_division(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        slice_node = node.slice
        candidates = []
        if isinstance(slice_node, ast.Slice):
            if slice_node.lower is not None:
                candidates.append(slice_node.lower)
            if slice_node.upper is not None:
                candidates.append(slice_node.upper)
        else:
            candidates.append(_slice_value(slice_node))
        for c in candidates:
            if isinstance(c, ast.BinOp) and isinstance(c.op, ast.Div):
                ls, le = _span(source, c.left)
                rs, re_ = _span(source, c.right)
                between = source[le:rs]
                if '/' in between and '//' not in between:
                    new_between = between.replace('/', '//', 1)
                    out.append(source[:le] + new_between + source[rs:])
    return out


# ---------------------------------------------------------------------------
# Rule 11: a merge-style comparison compares the wrong (or missing) tuple
# field -- e.g. left[0] vs right[0] or left[0][0] vs right[0][0] instead of
# comparing the age field at index 1.
# ---------------------------------------------------------------------------

def _fix_compare_age_index(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
            continue
        left, right = node.left, node.comparators[0]
        edits = []
        for side in (left, right):
            if not isinstance(side, ast.Subscript):
                continue
            if isinstance(side.value, ast.Subscript):
                idx = _const_index(side.slice)
                if idx == 0:
                    sv = _slice_value(side.slice)
                    s, e = _span(source, sv)
                    edits.append((s, e, '1'))
            elif isinstance(side.value, ast.Name):
                idx = _const_index(side.slice)
                if idx == 0:
                    s, e = _span(source, side)
                    edits.append((e, e, '[1]'))
        if edits:
            out.append(_apply_edits(source, edits))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_extremum_assignment",
                apply=_safe(_fix_extremum_assignment),
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_accumulator_misuse",
                apply=_safe(_fix_accumulator_misuse),
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="fix_missing_or_wrong_return",
                apply=_safe(_fix_missing_or_wrong_return),
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="remove_duplicate_trailing_append",
                apply=_safe(_remove_duplicate_trailing_append),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_pop_index_bug",
                apply=_safe(_fix_pop_index_bug),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_double_subscript_init",
                apply=_safe(_fix_double_subscript_init),
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="flip_subscript_comparison",
                apply=_safe(_flip_subscript_comparison),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_return_of_inplace_mutator",
                apply=_safe(_fix_return_of_inplace_mutator),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_trailing_print_to_return",
                apply=_safe(_fix_trailing_print_to_return),
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_index_true_division",
                apply=_safe(_fix_index_true_division),
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_compare_age_index",
                apply=_safe(_fix_compare_age_index),
                symptoms=("wrong",),
            ),
        ]