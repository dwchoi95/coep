"""
Repair rules for the "Sorting Tuples" (sort_age) assignment.

Each rule is a small, local, AST-located source-span splice targeting one
specific misconception observed in buggy student submissions.  Rules never
rewrite whole functions; they only touch the smallest span of source that
carries the bug.
"""

import ast
import builtins as _builtins_mod

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


def _parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _clean(source, candidates):
    out = []
    seen = set()
    for c in candidates:
        if not c or c == source or c in seen:
            continue
        if _parse(c) is None:
            continue
        seen.add(c)
        out.append(c)
    return out[:12]


def _slice_value(slice_node):
    # py<3.9 wraps constant slices in ast.Index
    if isinstance(slice_node, ast.Index):
        return slice_node.value
    return slice_node


def _target_names(target):
    names = set()
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names |= _target_names(elt)
    elif isinstance(target, ast.Starred):
        names |= _target_names(target.value)
    return names


def _collect_defined(tree):
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                defined |= _target_names(t)
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            defined |= _target_names(node.target)
        elif isinstance(node, ast.AugAssign):
            defined |= _target_names(node.target)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            defined |= _target_names(node.target)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                defined.add(a.arg)
            if node.args.vararg:
                defined.add(node.args.vararg.arg)
            if node.args.kwarg:
                defined.add(node.args.kwarg.arg)
        elif isinstance(node, ast.Lambda):
            for a in node.args.args:
                defined.add(a.arg)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in node.generators:
                defined |= _target_names(gen.target)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    defined |= _target_names(item.optional_vars)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                defined.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined.add(alias.asname or alias.name)
    return defined


def _build_parents(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _enclosing_for(node, parents):
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, (ast.For, ast.AsyncFor)) and isinstance(cur.target, ast.Name):
            return cur
        cur = parents.get(cur)
    return None


def _lev(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            tmp = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = tmp
    return dp[lb]


_OPSTR = {
    ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
    ast.Eq: "==", ast.NotEq: "!=",
}
_FLIP = {ast.Lt: ">", ast.LtE: ">=", ast.Gt: "<", ast.GtE: "<="}


def _refers(node, name):
    if isinstance(node, ast.Name) and node.id == name:
        return True
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == name:
        return True
    return False


# ----------------------------------------------------------------------
# Rule 1: rename a Name that is never assigned (NameError) to a plausible
# local variable: the function parameter, an empty-list accumulator, the
# target of an enclosing for-loop, or a close typo match.
# ----------------------------------------------------------------------

def _rename_undefined(source):
    tree = _parse(source)
    if tree is None:
        return []
    defined = _collect_defined(tree)
    builtins_set = set(dir(_builtins_mod)) | {"True", "False", "None", "self"}
    parents = _build_parents(tree)

    undefined = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined and node.id not in builtins_set:
                undefined.setdefault(node.id, []).append(node)
    if not undefined:
        return []

    params = []
    list_lits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef,)):
            for a in node.args.args:
                if a.arg not in params:
                    params.append(a.arg)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            if (isinstance(v, ast.List) and len(v.elts) == 0) or \
               (isinstance(v, ast.Tuple) and len(v.elts) == 0) or \
               (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "list" and not v.args):
                nm = node.targets[0].id
                if nm not in list_lits:
                    list_lits.append(nm)

    all_locals = sorted(defined - builtins_set)

    out = []
    for uid, nodes in undefined.items():
        candidates = []
        for n in nodes:
            fr = _enclosing_for(n, parents)
            if fr is not None and fr.target.id not in candidates:
                candidates.append(fr.target.id)
        for nm in list_lits:
            if nm not in candidates:
                candidates.append(nm)
        for p in params:
            if p not in candidates:
                candidates.append(p)
        close = sorted(
            (nm for nm in all_locals if nm != uid and _lev(nm, uid) <= 2),
            key=lambda nm: _lev(nm, uid),
        )
        for nm in close:
            if nm not in candidates:
                candidates.append(nm)

        for cand in candidates[:6]:
            spans = sorted((_span(source, n) for n in nodes), key=lambda x: -x[0])
            tmp = source
            for s, e in spans:
                tmp = tmp[:s] + cand + tmp[e:]
            out.append(tmp)
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 2: `list[0]` where `list` shadows the builtin instead of the real
# list parameter.
# ----------------------------------------------------------------------

def _fix_list_builtin_shadow(source):
    tree = _parse(source)
    if tree is None:
        return []
    defined = _collect_defined(tree)
    if "list" in defined:
        return []
    params = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.args.args:
            params.append(node.args.args[0].arg)
    if not params:
        return []
    param = params[0]
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "list":
            out.append(_splice(source, node.value, param))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 3: inside `for LOOPVAR in ...: if ...: LOOPVAR = EXTREMUM` should be
# `EXTREMUM = LOOPVAR` (the classic swapped assignment misconception).
# ----------------------------------------------------------------------

def _swap_if_assign(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for inner in ast.walk(node):
                if isinstance(inner, ast.If) and len(inner.body) == 1 and isinstance(inner.body[0], ast.Assign):
                    assign = inner.body[0]
                    if len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name) \
                            and isinstance(assign.value, ast.Name):
                        tgt = assign.targets[0].id
                        val = assign.value.id
                        if tgt == loopvar and val != loopvar:
                            new_text = "%s = %s" % (val, tgt)
                            out.append(_splice(source, assign, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 4: flip a min-selecting comparison to a max-selecting one, since
# this task always needs the maximum-age element picked, unless the
# program later reverses the result (in which case min-select + reverse
# is also valid and must be left alone).
# ----------------------------------------------------------------------

def _flip_minmax(source):
    if "reverse" in source or "[::-1]" in source or "reversed(" in source:
        return []
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for inner in node.body:
                if isinstance(inner, ast.If) and isinstance(inner.test, ast.Compare) and len(inner.test.ops) == 1:
                    body = inner.body
                    if len(body) == 1 and isinstance(body[0], ast.Assign) and len(body[0].targets) == 1 \
                            and isinstance(body[0].targets[0], ast.Name) and isinstance(body[0].value, ast.Name):
                        tgt = body[0].targets[0].id
                        val = body[0].value.id
                        if val == loopvar and tgt != loopvar:
                            extremum = tgt
                            cmp = inner.test
                            left, right = cmp.left, cmp.comparators[0]
                            op = cmp.ops[0]
                            left_loop = _refers(left, loopvar)
                            right_loop = _refers(right, loopvar)
                            left_extr = _refers(left, extremum)
                            right_extr = _refers(right, extremum)
                            is_min = False
                            if left_loop and right_extr and isinstance(op, (ast.Lt, ast.LtE)):
                                is_min = True
                            if left_extr and right_loop and isinstance(op, (ast.Gt, ast.GtE)):
                                is_min = True
                            if is_min and type(op) in _FLIP:
                                ls, le = _span(source, left)
                                rs, re_ = _span(source, right)
                                new_text = source[ls:le] + " " + _FLIP[type(op)] + " " + source[rs:re_]
                                out.append(_splice(source, cmp, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 5: after the selection for-loop, `.remove()`/`.append()` should use
# the tracked extremum variable, not the raw (last) loop variable.
# ----------------------------------------------------------------------

def _use_tracked_extremum(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for block in ast.walk(tree):
        body = getattr(block, "body", None)
        if not isinstance(body, list) or len(body) < 2:
            continue
        first = body[0]
        if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)):
            continue
        extremum = first.targets[0].id
        for stmt in body:
            if isinstance(stmt, (ast.For, ast.AsyncFor)) and isinstance(stmt.target, ast.Name):
                loopvar = stmt.target.id
                if loopvar == extremum:
                    continue
                for sib in body:
                    if sib is stmt or sib is first:
                        continue
                    for n in ast.walk(sib):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                                and n.func.attr in ("remove", "append"):
                            for a in n.args:
                                if isinstance(a, ast.Name) and a.id == loopvar:
                                    out.append(_splice(source, a, extremum))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 6: bare `X.reverse` statement (missing call parens).
# ----------------------------------------------------------------------

def _fix_reverse_no_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute) and node.value.attr == "reverse":
            os_, oe = _span(source, node.value)
            new_text = source[os_:oe] + "()"
            out.append(_splice(source, node.value, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 7: `return X.reverse()` / `return X.reverse` discards the sorted
# list (reverse() returns None in-place).
# ----------------------------------------------------------------------

def _fix_return_reverse(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            val = node.value
            target = None
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
                    and val.func.attr == "reverse" and isinstance(val.func.value, ast.Name):
                target = val.func.value.id
            elif isinstance(val, ast.Attribute) and val.attr == "reverse" and isinstance(val.value, ast.Name):
                target = val.value.id
            if target:
                indent = " " * node.col_offset
                new_text = "%s.reverse()\n%sreturn %s" % (target, indent, target)
                out.append(_splice(source, node, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 8: `helper(lst).reverse` -> call helper for effect, then reverse
# the actual list argument.
# ----------------------------------------------------------------------

def _fix_helper_call_reverse(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute) \
                and node.value.attr == "reverse" and isinstance(node.value.value, ast.Call):
            call = node.value.value
            if len(call.args) == 1 and isinstance(call.args[0], ast.Name):
                argname = call.args[0].id
                cs, ce = _span(source, call)
                call_text = source[cs:ce]
                indent = " " * node.col_offset
                new_text = "%s\n%s%s.reverse()" % (call_text, indent, argname)
                out.append(_splice(source, node, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 9: `X = X.append(y)` / `X = X.sort(...)` etc. — in-place list
# methods return None, so the reassignment destroys X.
# ----------------------------------------------------------------------

_INPLACE_METHODS = {"append", "sort", "reverse", "insert", "remove", "extend"}


def _fix_self_inplace_reassign(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            tgt = node.targets[0].id
            v = node.value
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr in _INPLACE_METHODS \
                    and isinstance(v.func.value, ast.Name) and v.func.value.id == tgt:
                vs, ve = _span(source, v)
                out.append(_splice(source, node, source[vs:ve]))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 10: `max(lst)` / `min(lst)` on a list of tuples compares whole
# tuples; needs `key=lambda p: p[1]`.
# ----------------------------------------------------------------------

def _add_key_minmax(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("max", "min") \
                and len(node.args) == 1 and not node.keywords:
            as_, ae = _span(source, node.args[0])
            arg_text = source[as_:ae]
            new_text = "%s(%s, key=lambda p: p[1])" % (node.func.id, arg_text)
            out.append(_splice(source, node, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 11: `lst.pop[i]` should be `lst.pop(i)`.
# ----------------------------------------------------------------------

def _fix_pop_bracket(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "pop":
            os_, oe = _span(source, node.value)
            obj_text = source[os_:oe]
            idx = _slice_value(node.slice)
            is_, ie = _span(source, idx)
            idx_text = source[is_:ie]
            new_text = "%s(%s)" % (obj_text, idx_text)
            out.append(_splice(source, node, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 12: function has no `return` anywhere -> append one using the
# empty-list accumulator or the list parameter.
# ----------------------------------------------------------------------

def _insert_missing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != "sort_age":
            continue
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        if not func.body:
            continue
        list_lits = []
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                if isinstance(n.value, ast.List) and len(n.value.elts) == 0:
                    if n.targets[0].id not in list_lits:
                        list_lits.append(n.targets[0].id)
        params = [a.arg for a in func.args.args]
        candidates = []
        for c in list_lits + params:
            if c not in candidates:
                candidates.append(c)
        if not candidates:
            continue
        last_stmt = func.body[-1]
        _, e = _span(source, last_stmt)
        indent = " " * last_stmt.col_offset
        for cand in candidates[:4]:
            insert_text = "\n%sreturn %s" % (indent, cand)
            out.append(source[:e] + insert_text + source[e:])
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 13: `X.append(...)` used but X was never assigned anywhere ->
# insert `X = []` as the function's first statement.
# ----------------------------------------------------------------------

def _insert_missing_accumulator(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef,)):
            continue
        if not func.body:
            continue
        assigned = _collect_defined(func)
        params = {a.arg for a in func.args.args}
        seen_names = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append" \
                    and isinstance(n.func.value, ast.Name):
                name = n.func.value.id
                if name not in assigned and name not in params and name not in seen_names:
                    seen_names.add(name)
                    indent = " " * func.body[0].col_offset
                    insert_text = "%s%s = []\n" % (indent, name)
                    s, _ = _span(source, func.body[0])
                    out.append(source[:s] + insert_text + source[s:])
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 14: a `return` statement is the last line *inside* a `while` loop
# body, so the loop only ever runs once. Dedent it to loop-level.
# ----------------------------------------------------------------------

def _dedent_return_from_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.While, ast.For)) and len(node.body) >= 2 and isinstance(node.body[-1], ast.Return):
            ret = node.body[-1]
            rs, re_ = _span(source, ret)
            line_start = source.rfind("\n", 0, rs) + 1
            ret_text = source[rs:re_]
            new_indent = " " * node.col_offset
            new_src = source[:line_start] + new_indent + ret_text + source[re_:]
            out.append(new_src)
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 15: bare-name comparison missing the `[1]` age index.
# ----------------------------------------------------------------------

def _age_holding_names(tree):
    ages = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            if isinstance(v, ast.Subscript):
                idx = _slice_value(v.slice)
                if isinstance(idx, ast.Constant) and idx.value == 1:
                    ages.add(node.targets[0].id)
    return ages


def _add_missing_age_index(source):
    tree = _parse(source)
    if tree is None:
        return []
    ages = _age_holding_names(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for inner in ast.walk(node):
                if isinstance(inner, ast.Compare) and len(inner.ops) == 1:
                    left, right = inner.left, inner.comparators[0]
                    left_has_idx = isinstance(left, ast.Subscript) and isinstance(_slice_value(left.slice), ast.Constant) \
                        and _slice_value(left.slice).value == 1
                    right_has_idx = isinstance(right, ast.Subscript) and isinstance(_slice_value(right.slice), ast.Constant) \
                        and _slice_value(right.slice).value == 1
                    for operand, other_has_idx in ((left, right_has_idx), (right, left_has_idx)):
                        if isinstance(operand, ast.Name) and operand.id not in ages:
                            qualifies = operand.id == loopvar or other_has_idx
                            if qualifies:
                                os_, oe = _span(source, operand)
                                new_text = source[os_:oe] + "[1]"
                                out.append(_splice(source, operand, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 16: `EXTREMUM = LOOPVAR[1]` when EXTREMUM should hold the whole
# tuple (it was initialised from a full element, e.g. `lst[0]`).
# ----------------------------------------------------------------------

def _fix_assign_drops_index(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for inner in ast.walk(node):
                if isinstance(inner, ast.If):
                    for stmt in inner.body:
                        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                                and isinstance(stmt.targets[0], ast.Name):
                            val = stmt.value
                            if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) \
                                    and val.value.id == loopvar:
                                idx = _slice_value(val.slice)
                                if isinstance(idx, ast.Constant) and idx.value == 1:
                                    out.append(_splice(source, val, loopvar))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 17: `newlst += current` where `current` is a bare tuple-holding
# name should be `newlst += (current,)` (list.__iadd__ flattens iterables).
# ----------------------------------------------------------------------

def _fix_augassign_tuple_wrap(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.value, ast.Name):
            vs, ve = _span(source, node.value)
            new_text = "(%s,)" % source[vs:ve]
            out.append(_splice(source, node.value, new_text))
    return _clean(source, out)


# ----------------------------------------------------------------------
# Rule 18: `range(1, len(lst) + 1)` style off-by-one that overruns list
# indices; drop the stray `+ 1`.
# ----------------------------------------------------------------------

def _fix_range_off_by_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and node.args:
            last = node.args[-1]
            if isinstance(last, ast.BinOp) and isinstance(last.op, ast.Add) \
                    and isinstance(last.left, ast.Call) and isinstance(last.left.func, ast.Name) \
                    and last.left.func.id == "len" \
                    and isinstance(last.right, ast.Constant) and last.right.value == 1:
                ls, le = _span(source, last.left)
                out.append(_splice(source, last, source[ls:le]))
    return _clean(source, out)


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="rename_undefined_names", apply=_rename_undefined,
                 symptoms=("err:NameError",)),
            Rule(name="fix_list_builtin_shadow", apply=_fix_list_builtin_shadow,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="swap_assignment_target_value", apply=_swap_if_assign,
                 symptoms=("wrong",)),
            Rule(name="flip_selection_comparison", apply=_flip_minmax,
                 symptoms=("wrong",)),
            Rule(name="use_tracked_extremum_in_remove_append", apply=_use_tracked_extremum,
                 symptoms=("wrong",)),
            Rule(name="fix_reverse_no_call", apply=_fix_reverse_no_call,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="fix_return_reverse_call", apply=_fix_return_reverse,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="fix_helper_call_reverse", apply=_fix_helper_call_reverse,
                 symptoms=("err:AttributeError", "wrong")),
            Rule(name="fix_self_inplace_reassign", apply=_fix_self_inplace_reassign,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="add_key_to_minmax", apply=_add_key_minmax,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_pop_bracket", apply=_fix_pop_bracket,
                 symptoms=("err:TypeError",)),
            Rule(name="insert_missing_return", apply=_insert_missing_return,
                 symptoms=("wrong",)),
            Rule(name="insert_missing_accumulator_init", apply=_insert_missing_accumulator,
                 symptoms=("err:NameError",)),
            Rule(name="dedent_return_from_loop", apply=_dedent_return_from_loop,
                 symptoms=("wrong",)),
            Rule(name="add_missing_age_index", apply=_add_missing_age_index,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_assign_drops_index", apply=_fix_assign_drops_index,
                 symptoms=("err:ValueError", "wrong")),
            Rule(name="fix_augassign_tuple_wrap", apply=_fix_augassign_tuple_wrap,
                 symptoms=("wrong",)),
            Rule(name="fix_range_off_by_one", apply=_fix_range_off_by_one,
                 symptoms=("err:IndexError",)),
        ]