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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _safe(fn):
    def wrapped(source):
        try:
            out = fn(source)
        except Exception:
            return []
        seen = []
        for c in out:
            if isinstance(c, str) and c != source and c not in seen:
                seen.append(c)
        return seen
    return wrapped


# ---------------------------------------------------------------------------
# 1. toggle strictness of a relational comparison (< <-> <=, > <-> >=)
# ---------------------------------------------------------------------------
_STRICT_SWAP = {ast.Lt: '<=', ast.LtE: '<', ast.Gt: '>=', ast.GtE: '>'}


@_safe
def _toggle_strict(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _STRICT_SWAP:
            new_op = _STRICT_SWAP[type(node.ops[0])]
            new_text = f"{_text(source, node.left)} {new_op} {_text(source, node.comparators[0])}"
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# 2. negate a relational comparison (< <-> >=, > <-> <=)
# ---------------------------------------------------------------------------
_NEGATE_SWAP = {ast.Lt: '>=', ast.GtE: '<', ast.Gt: '<=', ast.LtE: '>'}


@_safe
def _negate_cmp(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _NEGATE_SWAP:
            new_op = _NEGATE_SWAP[type(node.ops[0])]
            new_text = f"{_text(source, node.left)} {new_op} {_text(source, node.comparators[0])}"
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# 3. `for i in len(seq)` / `for i in len(range(seq))` -> `for i in range(len(seq))`
# ---------------------------------------------------------------------------
@_safe
def _fix_malformed_range_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == 'len' and len(it.args) == 1:
                inner = it.args[0]
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == 'range' and len(inner.args) == 1:
                    coll = inner.args[0]
                else:
                    coll = inner
                new_text = f"range(len({_text(source, coll)}))"
                out.append(_splice(source, it, new_text))
    return out


# ---------------------------------------------------------------------------
# 4. `name == value` used as a statement -> `name = value`  (typo for `=`)
# ---------------------------------------------------------------------------
@_safe
def _fix_double_equals(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq) and isinstance(cmp.left, ast.Name):
                new_text = f"{_text(source, cmp.left)} = {_text(source, cmp.comparators[0])}"
                out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# 5. `seq == () or []` (truthiness bug) -> `seq == () or seq == []`
# ---------------------------------------------------------------------------
@_safe
def _fix_truthy_or(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            compare_var = None
            parts = []
            changed = False
            for v in node.values:
                if isinstance(v, ast.Compare) and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq) and isinstance(v.left, ast.Name):
                    compare_var = v.left
                    parts.append(_text(source, v))
                elif isinstance(v, (ast.Tuple, ast.List)) and compare_var is not None:
                    parts.append(f"{compare_var.id} == {_text(source, v)}")
                    changed = True
                else:
                    parts.append(_text(source, v))
            if changed:
                out.append(_splice(source, node, " or ".join(parts)))
    return out


# ---------------------------------------------------------------------------
# 6. `return x` (the search value) inside a loop -> `return <loop var>`
# ---------------------------------------------------------------------------
@_safe
def _return_param_to_loopvar(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args:
            continue
        params = {a.arg for a in fn.args.args}
        for node in ast.walk(fn):
            if isinstance(node, ast.For):
                loop_vars = []
                if isinstance(node.target, ast.Name):
                    loop_vars = [node.target.id]
                elif isinstance(node.target, ast.Tuple):
                    loop_vars = [e.id for e in node.target.elts if isinstance(e, ast.Name)]
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Name) and sub.value.id in params:
                        for lv in loop_vars:
                            if lv != sub.value.id:
                                out.append(_splice(source, sub.value, lv))
    return out


# ---------------------------------------------------------------------------
# 7. comparing x directly to a bare loop index instead of seq[index]
# ---------------------------------------------------------------------------
@_safe
def _bare_index_to_subscript(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args:
            continue
        params = [a.arg for a in fn.args.args]
        seqparam = params[1] if len(params) > 1 else 'seq'
        for node in ast.walk(fn):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                idx = node.target.id
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Compare):
                        for operand in [sub.left] + list(sub.comparators):
                            if isinstance(operand, ast.Name) and operand.id == idx:
                                out.append(_splice(source, operand, f"{seqparam}[{idx}]"))
    return out


# ---------------------------------------------------------------------------
# 8. a for/while loop is the whole function body -> missing fallback return
# ---------------------------------------------------------------------------
@_safe
def _append_return_len_seq(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.body:
            last = fn.body[-1]
            if isinstance(last, (ast.For, ast.While)):
                params = [a.arg for a in fn.args.args]
                seqparam = params[1] if len(params) > 1 else 'seq'
                s, e = _span(source, last)
                line_start = source.rfind('\n', 0, s) + 1
                indent = source[line_start:s]
                insertion = f"\n{indent}return len({seqparam})"
                out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# 9. loop body = [If(..returns..), unconditional Return]  (fires 1st iter)
#    -> drop the stray unconditional return so the loop can keep iterating
# ---------------------------------------------------------------------------
@_safe
def _remove_premature_loop_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)) and len(node.body) >= 2:
            last = node.body[-1]
            prev = node.body[-2]
            if isinstance(last, ast.Return) and isinstance(prev, ast.If) and not prev.orelse:
                if prev.body and isinstance(prev.body[-1], ast.Return):
                    s, e = _span(source, last)
                    pre = source.rfind('\n', 0, s)
                    if pre != -1:
                        out.append(source[:pre] + source[e:])
    return out


# ---------------------------------------------------------------------------
# 10. off-by-one on a returned index: `return i+1` <-> `return i`
# ---------------------------------------------------------------------------
@_safe
def _strip_plus_minus_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp)
                and isinstance(node.value.op, (ast.Add, ast.Sub))
                and isinstance(node.value.right, ast.Constant) and node.value.right.value == 1
                and isinstance(node.value.left, ast.Name)):
            out.append(_splice(source, node.value, node.value.left.id))
    return out


@_safe
def _add_plus_one_to_return_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            out.append(_splice(source, node.value, f"{node.value.id} + 1"))
    return out


# ---------------------------------------------------------------------------
# 11. `pos += pos` (self add) -> `pos += 1`
# ---------------------------------------------------------------------------
@_safe
def _fix_self_aug_assign(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name)
                and node.target.id == node.value.id):
            out.append(_splice(source, node.value, "1"))
    return out


# ---------------------------------------------------------------------------
# 12. `x == ()` where x was reassigned via `x = list(...)` -> `x == []`
# ---------------------------------------------------------------------------
@_safe
def _fix_tuple_to_list_check(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        list_cast_vars = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'list'):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        list_cast_vars.add(t.id)
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Name) and left.id in list_cast_vars \
                        and isinstance(right, ast.Tuple) and len(right.elts) == 0:
                    out.append(_splice(source, right, "[]"))
    return out


# ---------------------------------------------------------------------------
# 13. a name used (e.g. `newseq[-1]`) before its own `newseq = list(seq)`
#     assignment -> replace the premature uses with the source variable
# ---------------------------------------------------------------------------
@_safe
def _swap_undefined_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        assigned = {}
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'list'
                    and len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Name)):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned.setdefault(t.id, (node, node.value.args[0].id))
        for var, (assign_node, source_name) in assigned.items():
            assign_s, _ = _span(source, assign_node)
            targets = []
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and node.id == var and isinstance(node.ctx, ast.Load):
                    ns, ne = _span(source, node)
                    if ns < assign_s:
                        targets.append((ns, ne))
            if not targets:
                continue
            targets.sort(reverse=True)
            cand = source
            for ns, ne in targets:
                cand = cand[:ns] + source_name + cand[ne:]
            out.append(cand)
    return out


# ---------------------------------------------------------------------------
# 14. `seq(i)` (call typo) -> `seq[i]` (subscript)
# ---------------------------------------------------------------------------
@_safe
def _fix_call_to_subscript(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = [a.arg for a in fn.args.args]
        seqparam = params[1] if len(params) > 1 else 'seq'
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == seqparam and len(node.args) == 1 and not node.keywords):
                out.append(_splice(source, node, f"{seqparam}[{_text(source, node.args[0])}]"))
    return out


# ---------------------------------------------------------------------------
# 15. `len[i]` typo -> `seq[i]`
# ---------------------------------------------------------------------------
@_safe
def _fix_len_subscript_typo(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = [a.arg for a in fn.args.args]
        seqparam = params[1] if len(params) > 1 else 'seq'
        for node in ast.walk(fn):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'len':
                out.append(_splice(source, node.value, seqparam))
    return out


# ---------------------------------------------------------------------------
# 16. `range(len(seq) - 1)` -> `range(len(seq))` (off-by-one loop bound)
# ---------------------------------------------------------------------------
@_safe
def _fix_range_minus_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'range' and len(node.args) == 1:
            arg = node.args[0]
            if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
                    and isinstance(arg.right, ast.Constant) and arg.right.value == 1):
                out.append(_splice(source, arg, _text(source, arg.left)))
    return out


# ---------------------------------------------------------------------------
# 17. bare `return` (no value) inside a loop -> `break`
# ---------------------------------------------------------------------------
@_safe
def _bare_return_to_break(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for loop in ast.walk(tree):
        if isinstance(loop, (ast.For, ast.While)):
            for node in ast.walk(loop):
                if isinstance(node, ast.Return) and node.value is None:
                    out.append(_splice(source, node, "break"))
    return out


# ---------------------------------------------------------------------------
# 18. undefined name used as the iterable of a for-loop / enumerate() ->
#     replace with the sequence parameter (typo'd identifier)
# ---------------------------------------------------------------------------
@_safe
def _fix_typo_iterable(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args:
            continue
        params = {a.arg for a in fn.args.args}
        assigned = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                assigned.add(node.target.id)
        known = params | assigned | {'len', 'range', 'enumerate', 'list', 'tuple',
                                      'print', 'sorted', 'max', 'min', 'True', 'False', 'None'}
        other_params = [p for p in params if fn.args.args and p != fn.args.args[0].arg]
        seqparam = other_params[0] if other_params else (fn.args.args[0].arg if fn.args.args else None)
        if seqparam is None:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.For):
                it = node.iter
                name_node = None
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == 'enumerate' \
                        and len(it.args) == 1 and isinstance(it.args[0], ast.Name):
                    name_node = it.args[0]
                elif isinstance(it, ast.Name):
                    name_node = it
                if name_node is not None and name_node.id not in known:
                    out.append(_splice(source, name_node, seqparam))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="toggle_strict_nonstrict", apply=_toggle_strict,
                 symptoms=("wrong",)),
            Rule(name="negate_comparison", apply=_negate_cmp,
                 symptoms=("wrong",)),
            Rule(name="fix_malformed_range_loop", apply=_fix_malformed_range_loop,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_double_equals_stmt", apply=_fix_double_equals,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="fix_truthy_or_container_check", apply=_fix_truthy_or,
                 symptoms=("wrong",)),
            Rule(name="return_param_to_loopvar", apply=_return_param_to_loopvar,
                 symptoms=("wrong",)),
            Rule(name="bare_index_to_subscript", apply=_bare_index_to_subscript,
                 symptoms=("wrong",)),
            Rule(name="append_return_len_seq_after_loop", apply=_append_return_len_seq,
                 symptoms=("wrong",)),
            Rule(name="remove_premature_loop_return", apply=_remove_premature_loop_return,
                 symptoms=("wrong",)),
            Rule(name="strip_plus_minus_one_on_return", apply=_strip_plus_minus_one,
                 symptoms=("wrong",)),
            Rule(name="add_plus_one_to_return_name", apply=_add_plus_one_to_return_name,
                 symptoms=("wrong",)),
            Rule(name="fix_self_aug_assign", apply=_fix_self_aug_assign,
                 symptoms=("wrong",)),
            Rule(name="fix_tuple_to_list_check", apply=_fix_tuple_to_list_check,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="swap_undefined_name_with_source", apply=_swap_undefined_name,
                 symptoms=("err:NameError",)),
            Rule(name="fix_call_to_subscript", apply=_fix_call_to_subscript,
                 symptoms=("err:TypeError",)),
            Rule(name="fix_len_subscript_typo", apply=_fix_len_subscript_typo,
                 symptoms=("err:TypeError",)),
            Rule(name="fix_range_minus_one_bound", apply=_fix_range_minus_one,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="bare_return_to_break", apply=_bare_return_to_break,
                 symptoms=("wrong",)),
            Rule(name="fix_typo_iterable_name", apply=_fix_typo_iterable,
                 symptoms=("err:NameError",)),
        ]