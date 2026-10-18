"""
Repair rules for the Top-K assignment.

Each rule inspects the AST of a submission, looks for a narrowly-scoped
structural pattern tied to a known misconception, and emits one or more
textually-spliced candidate sources (never a full rewrite).
"""

import ast
import builtins

from src.core.repair import Rule


# ----------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------

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


def _names_in_target(t):
    out = []
    if isinstance(t, ast.Name):
        out.append(t.id)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for el in t.elts:
            out.extend(_names_in_target(el))
    return out


def _assigned_names(fd):
    names = set()
    for n in ast.walk(fd):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                names.update(_names_in_target(t))
        elif isinstance(n, ast.AugAssign):
            names.update(_names_in_target(n.target))
        elif isinstance(n, ast.For):
            names.update(_names_in_target(n.target))
        elif isinstance(n, ast.arg):
            names.add(n.arg)
    return names


def _find_accumulator(fd):
    """A local var initialised to [] and later appended to -- the result list."""
    candidates = []
    appended = set()
    for n in ast.walk(fd):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if isinstance(n.value, ast.List) and len(n.value.elts) == 0:
                candidates.append(n.targets[0].id)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append":
            if isinstance(n.func.value, ast.Name):
                appended.add(n.func.value.id)
    good = [c for c in candidates if c in appended]
    good = list(dict.fromkeys(good))
    if len(good) == 1:
        return good[0]
    return None


def _sub_slice(node):
    sl = node.slice
    if isinstance(sl, ast.Index):  # pragma: no cover (old pythons)
        sl = sl.value
    return sl


def _subscript_assign_parts(source, stmt):
    if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
        return None
    t = stmt.targets[0]
    v = stmt.value
    if not (isinstance(t, ast.Subscript) and isinstance(v, ast.Subscript)):
        return None
    tv_s, tv_e = _span(source, t.value)
    vv_s, vv_e = _span(source, v.value)
    if source[tv_s:tv_e] != source[vv_s:vv_e]:
        return None
    t_idx = _sub_slice(t)
    v_idx = _sub_slice(v)
    if isinstance(t_idx, ast.Slice) or isinstance(v_idx, ast.Slice):
        return None
    ti_s, ti_e = _span(source, t_idx)
    vi_s, vi_e = _span(source, v_idx)
    return source[tv_s:tv_e], source[ti_s:ti_e], source[vi_s:vi_e]


def _match_simple_call(stmt, attr):
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and call.func.attr == attr and len(call.args) == 1:
            return call.func.value, call.args[0]
    return None


def _node_text_eq(source, n1, n2):
    s1, e1 = _span(source, n1)
    s2, e2 = _span(source, n2)
    return source[s1:e1] == source[s2:e2]


def _kparam_of(fd):
    params = [a.arg for a in fd.args.args]
    return params[-1] if len(params) >= 2 else None


# ----------------------------------------------------------------------
# Rule: off-by-one loop bound `<= k` -> `< k`
# ----------------------------------------------------------------------

def _le_k_to_lt(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef):
                continue
            kparam = _kparam_of(fd)
            if not kparam:
                continue
            for node in ast.walk(fd):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
                    right = node.comparators[0]
                    if isinstance(right, ast.Name) and right.id == kparam:
                        left = node.left
                        ls, le = _span(source, left)
                        rs, re_ = _span(source, right)
                        new_cmp = source[ls:le] + " < " + source[rs:re_]
                        out.append(_splice(source, node, new_cmp))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `k >= 0` -> `k > 0`
# ----------------------------------------------------------------------

def _k_ge_zero(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and right.value == 0:
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    new_cmp = source[ls:le] + " > " + source[rs:re_]
                    out.append(_splice(source, node, new_cmp))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `x.append[v]` / `x.remove[v]` / `x.pop[v]` -> call syntax
# ----------------------------------------------------------------------

def _bracket_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
               and node.value.attr in ("append", "remove", "pop"):
                sl = _sub_slice(node)
                if isinstance(sl, ast.Slice):
                    continue
                val_s, val_e = _span(source, node.value)
                arg_s, arg_e = _span(source, sl)
                new_text = source[val_s:val_e] + "(" + source[arg_s:arg_e] + ")"
                out.append(_splice(source, node, new_text))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: remove-then-append-of-max swapped order
# ----------------------------------------------------------------------

def _swap_remove_append(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for i in range(len(body) - 1):
                s1, s2 = body[i], body[i + 1]
                r1 = _match_simple_call(s1, "remove")
                r2 = _match_simple_call(s2, "append")
                if r1 is None or r2 is None:
                    continue
                _, arg1 = r1
                _, arg2 = r2
                if _node_text_eq(source, arg1, arg2):
                    s1s, s1e = _span(source, s1)
                    s2s, s2e = _span(source, s2)
                    text1 = source[s1s:s1e]
                    text2 = source[s2s:s2e]
                    indent = ' ' * s1.col_offset
                    new_region = text2 + "\n" + indent + text1
                    out.append(source[:s1s] + new_region + source[s2e:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: function never returns, but builds a clear accumulator
# ----------------------------------------------------------------------

def _missing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef):
                continue
            has_return = any(isinstance(n, ast.Return) for n in ast.walk(fd))
            if has_return:
                continue
            acc = _find_accumulator(fd)
            if acc is None or not fd.body:
                continue
            last = fd.body[-1]
            _, end = _span(source, last)
            indent = ' ' * fd.body[0].col_offset
            insertion = "\n" + indent + "return " + acc
            out.append(source[:end] + insertion + source[end:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: hard-coded / off-by-one slice bound instead of bare `k`
# ----------------------------------------------------------------------

def _slice_bound_to_k(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef):
                continue
            kparam = _kparam_of(fd)
            if not kparam:
                continue
            for node in ast.walk(fd):
                if isinstance(node, ast.Subscript):
                    sl = _sub_slice(node)
                    if isinstance(sl, ast.Slice) and sl.lower is None and sl.step is None and sl.upper is not None:
                        upper = sl.upper
                        if isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                            out.append(_splice(source, upper, kparam))
                        elif isinstance(upper, ast.BinOp) and isinstance(upper.op, (ast.Add, ast.Sub)) \
                                and isinstance(upper.left, ast.Name) and upper.left.id == kparam \
                                and isinstance(upper.right, ast.Constant) and isinstance(upper.right.value, int):
                            out.append(_splice(source, upper, kparam))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: max-scan `if a > track: WRONG = a` -- wrong assignment target
# ----------------------------------------------------------------------

def _if_update_wrong_target(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and len(node.body) == 1 and isinstance(node.body[0], ast.Assign):
                test = node.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], (ast.Gt, ast.Lt)):
                    left, right = test.left, test.comparators[0]
                    assign = node.body[0]
                    if len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name) \
                            and isinstance(assign.value, ast.Name) \
                            and isinstance(left, ast.Name) and isinstance(right, ast.Name):
                        target = assign.targets[0]
                        value = assign.value
                        if value.id == left.id and target.id != right.id:
                            out.append(_splice(source, target, right.id))
                        elif value.id == right.id and target.id != left.id:
                            out.append(_splice(source, target, left.id))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: linear scan finds minimum but task needs maximum
# ----------------------------------------------------------------------

def _min_should_be_max(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and len(node.body) == 1 and isinstance(node.body[0], ast.Assign):
                test = node.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Lt):
                    left, right = test.left, test.comparators[0]
                    assign = node.body[0]
                    if len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name) \
                            and isinstance(assign.value, ast.Name) \
                            and isinstance(left, ast.Name) and isinstance(right, ast.Name) \
                            and assign.targets[0].id == right.id and assign.value.id == left.id:
                        ls, le = _span(source, left)
                        rs, re_ = _span(source, right)
                        new_cmp = source[ls:le] + " > " + source[rs:re_]
                        out.append(_splice(source, test, new_cmp))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `.append(...)`/`.remove(...)` called on an undefined container name
# ----------------------------------------------------------------------

def _undefined_container(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    builtin_names = set(dir(builtins))
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef):
                continue
            assigned = _assigned_names(fd)
            params = {a.arg for a in fd.args.args}
            emptylist_vars = [
                n.targets[0].id for n in ast.walk(fd)
                if isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.List) and len(n.value.elts) == 0
            ]
            uniq = list(dict.fromkeys(emptylist_vars))
            if len(uniq) != 1:
                continue
            acc = uniq[0]
            undefined_targets = set()
            for n in ast.walk(fd):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                        and n.func.attr in ("append", "remove"):
                    v = n.func.value
                    if isinstance(v, ast.Name) and v.id not in assigned and v.id not in params \
                            and v.id not in builtin_names and v.id != fd.name:
                        undefined_targets.add(v.id)
            for bad in undefined_targets:
                if bad == acc:
                    continue
                occurrences = [n for n in ast.walk(fd) if isinstance(n, ast.Name) and n.id == bad]
                occurrences.sort(key=lambda n: _span(source, n)[0], reverse=True)
                new_source = source
                for occ in occurrences:
                    new_source = _splice(new_source, occ, acc)
                out.append(new_source)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `v = max(x)` then `.append(wrong_arg)` / `.remove(wrong_arg)`
# ----------------------------------------------------------------------

def _max_var_mismatch(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for idx, stmt in enumerate(body):
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                        and isinstance(stmt.targets[0], ast.Name) \
                        and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) \
                        and stmt.value.func.id == "max":
                    vname = stmt.targets[0].id
                    replacements = []
                    for later in body[idx + 1:]:
                        for call in ast.walk(later):
                            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) \
                                    and call.func.attr in ("append", "remove") and len(call.args) == 1:
                                arg = call.args[0]
                                if isinstance(arg, ast.Name) and arg.id != vname:
                                    replacements.append(arg)
                    if replacements:
                        replacements.sort(key=lambda n: _span(source, n)[0], reverse=True)
                        new_source = source
                        for arg in replacements:
                            new_source = _splice(new_source, arg, vname)
                        out.append(new_source)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `acc.append(lst.remove(max(lst)))` -> split into two statements
# ----------------------------------------------------------------------

def _append_wraps_remove(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and len(call.args) == 1:
                    inner = call.args[0]
                    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) \
                            and inner.func.attr == "remove" and len(inner.args) == 1:
                        acc_s, acc_e = _span(source, call.func.value)
                        lst_s, lst_e = _span(source, inner.func.value)
                        arg_s, arg_e = _span(source, inner.args[0])
                        acc_text = source[acc_s:acc_e]
                        lst_text = source[lst_s:lst_e]
                        arg_text = source[arg_s:arg_e]
                        indent = ' ' * node.col_offset
                        new_text = f"{acc_text}.append({arg_text})\n{indent}{lst_text}.remove({arg_text})"
                        out.append(_splice(source, node, new_text))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: trailing `return` trapped inside the function's final loop
# ----------------------------------------------------------------------

def _dedent_trailing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef) or not fd.body:
                continue
            last = fd.body[-1]
            if isinstance(last, (ast.While, ast.For)) and last.body and isinstance(last.body[-1], ast.Return):
                ret = last.body[-1]
                rs, re_ = _span(source, ret)
                line_start = source.rfind('\n', 0, rs) + 1
                indent = ' ' * fd.body[0].col_offset
                new_source = source[:line_start] + indent + source[rs:re_] + source[re_:]
                out.append(new_source)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `return <original_param>[:k]` instead of the built accumulator
# ----------------------------------------------------------------------

def _return_wrong_var(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef):
                continue
            acc = _find_accumulator(fd)
            if acc is None:
                continue
            for node in ast.walk(fd):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                    sub = node.value
                    if isinstance(sub.value, ast.Name) and sub.value.id != acc:
                        out.append(_splice(source, sub.value, acc))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `lst.pop(value)` instead of `lst.pop(lst.index(value))`
# ----------------------------------------------------------------------

def _pop_value_as_index(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "pop" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Constant):
                    continue
                list_s, list_e = _span(source, node.func.value)
                list_text = source[list_s:list_e]
                arg_s, arg_e = _span(source, arg)
                arg_text = source[arg_s:arg_e]
                if arg_text.strip().startswith(f"{list_text}.index("):
                    continue
                new_arg = f"{list_text}.index({arg_text})"
                out.append(_splice(source, arg, new_arg))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `range(k - 1)` -> `range(k)`
# ----------------------------------------------------------------------

def _range_k_minus_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef):
                continue
            kparam = _kparam_of(fd)
            if not kparam:
                continue
            for node in ast.walk(fd):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" \
                        and len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) \
                            and isinstance(arg.left, ast.Name) and arg.left.id == kparam \
                            and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                        out.append(_splice(source, arg, kparam))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: failed manual swap (overwrite-before-swap) -> tuple swap
# ----------------------------------------------------------------------

def _fake_swap(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for i in range(len(body) - 1):
                s1, s2 = body[i], body[i + 1]
                p1 = _subscript_assign_parts(source, s1)
                p2 = _subscript_assign_parts(source, s2)
                if not p1 or not p2:
                    continue
                var1, tgt_idx1, src_idx1 = p1
                var2, tgt_idx2, src_idx2 = p2
                if var1 != var2 or tgt_idx1 == tgt_idx2:
                    continue
                if tgt_idx1 == src_idx2 and tgt_idx2 == src_idx1:
                    s1s, _ = _span(source, s1)
                    _, s2e = _span(source, s2)
                    new_stmt = f"{var1}[{tgt_idx1}], {var1}[{tgt_idx2}] = {var1}[{tgt_idx2}], {var1}[{tgt_idx1}]"
                    out.append(source[:s1s] + new_stmt + source[s2e:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: single-pass bubble (no outer pass loop) -> wrap with range(len())
# ----------------------------------------------------------------------

def _wrap_single_pass_bubble(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fd in ast.walk(tree):
            if not isinstance(fd, ast.FunctionDef):
                continue
            for node in fd.body:
                if not isinstance(node, ast.For):
                    continue
                has_swap = False
                listname = None
                for n in ast.walk(node):
                    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Tuple):
                        tgt = n.targets[0]
                        if isinstance(n.value, ast.Tuple) and len(tgt.elts) == 2 and len(n.value.elts) == 2 \
                                and all(isinstance(e, ast.Subscript) for e in list(tgt.elts) + list(n.value.elts)):
                            has_swap = True
                            v = tgt.elts[0].value
                            vs, ve = _span(source, v)
                            listname = source[vs:ve]
                if not has_swap or listname is None:
                    continue
                ns, ne = _span(source, node)
                line_start = source.rfind('\n', 0, ns) + 1
                block_full = source[line_start:ne]
                lines = block_full.split('\n')
                reindented = '\n'.join(('    ' + ln) if ln.strip() != '' else ln for ln in lines)
                indent = ' ' * node.col_offset
                new_text = indent + f"for _tk in range(len({listname})):\n" + reindented
                out.append(source[:line_start] + new_text + source[ne:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: index variable compared directly instead of `lst[i]`
# ----------------------------------------------------------------------

def _index_var_used_as_value(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name) \
                    and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) \
                    and node.iter.func.id == "range" and len(node.iter.args) == 1:
                rng_arg = node.iter.args[0]
                if isinstance(rng_arg, ast.Call) and isinstance(rng_arg.func, ast.Name) \
                        and rng_arg.func.id == "len" and len(rng_arg.args) == 1 \
                        and isinstance(rng_arg.args[0], ast.Name):
                    listname = rng_arg.args[0].id
                    idxname = node.target.id
                    for n in ast.walk(node):
                        if isinstance(n, ast.Compare) and len(n.ops) == 1:
                            if isinstance(n.left, ast.Name) and n.left.id == idxname:
                                out.append(_splice(source, n.left, f"{listname}[{idxname}]"))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: while-counter loop body never increments its counter
# ----------------------------------------------------------------------

def _missing_counter_increment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 \
                    and isinstance(node.test.ops[0], (ast.Lt, ast.LtE)) and isinstance(node.test.left, ast.Name):
                counter = node.test.left.id
                if not node.body:
                    continue
                incremented = False
                for n in node.body:
                    if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == counter:
                        incremented = True
                    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                            and n.targets[0].id == counter:
                        incremented = True
                if incremented:
                    continue
                last = node.body[-1]
                _, end = _span(source, last)
                indent = ' ' * last.col_offset
                insertion = "\n" + indent + f"{counter} += 1"
                out.append(source[:end] + insertion + source[end:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="le_k_to_lt_k", apply=_le_k_to_lt, symptoms=("wrong",)),
            Rule(name="k_ge_zero_to_gt_zero", apply=_k_ge_zero, symptoms=("wrong", "timeout")),
            Rule(name="bracket_call_to_paren", apply=_bracket_call,
                 symptoms=("err:TypeError",)),
            Rule(name="swap_remove_append_order", apply=_swap_remove_append, symptoms=("wrong",)),
            Rule(name="missing_return_add", apply=_missing_return, symptoms=("wrong",)),
            Rule(name="hardcoded_slice_bound_to_k", apply=_slice_bound_to_k, symptoms=("wrong",)),
            Rule(name="if_update_wrong_target", apply=_if_update_wrong_target, symptoms=("wrong",)),
            Rule(name="min_should_be_max", apply=_min_should_be_max, symptoms=("wrong",)),
            Rule(name="undefined_container_append", apply=_undefined_container,
                 symptoms=("err:NameError",)),
            Rule(name="max_var_mismatch", apply=_max_var_mismatch, symptoms=("wrong", "err:NameError")),
            Rule(name="append_wraps_remove", apply=_append_wraps_remove, symptoms=("wrong",)),
            Rule(name="dedent_trailing_return", apply=_dedent_trailing_return, symptoms=("wrong",)),
            Rule(name="return_wrong_var", apply=_return_wrong_var, symptoms=("wrong",)),
            Rule(name="pop_value_as_index", apply=_pop_value_as_index, symptoms=("err:ValueError", "wrong")),
            Rule(name="range_k_minus_one", apply=_range_k_minus_one, symptoms=("wrong",)),
            Rule(name="fake_swap_to_tuple_swap", apply=_fake_swap, symptoms=("wrong",)),
            Rule(name="wrap_single_pass_bubble", apply=_wrap_single_pass_bubble, symptoms=("wrong",)),
            Rule(name="index_var_used_as_value", apply=_index_var_used_as_value, symptoms=("wrong",)),
            Rule(name="missing_counter_increment", apply=_missing_counter_increment,
                 symptoms=("timeout", "wrong")),
        ]