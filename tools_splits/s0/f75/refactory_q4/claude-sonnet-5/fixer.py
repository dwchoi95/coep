import ast
from src.core.repair import Rule


# ----------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------

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


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _multi_splice(source, replacements):
    out = source
    for s, e, t in sorted(replacements, key=lambda r: -r[0]):
        out = out[:s] + t + out[e:]
    return out


def _indent_of(source, node):
    s, _ = _span(source, node)
    line_start = source.rfind('\n', 0, s) + 1
    return source[line_start:s]


def _line_bounds(source, node):
    s, e = _span(source, node)
    line_start = source.rfind('\n', 0, s) + 1
    line_end = source.find('\n', e)
    if line_end == -1:
        line_end = len(source)
    else:
        line_end += 1
    return line_start, line_end


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    tree.parent = None


def _enclosing(node, types):
    p = getattr(node, 'parent', None)
    while p is not None:
        if isinstance(p, types):
            return p
        p = getattr(p, 'parent', None)
    return None


def _safe_parse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    _add_parents(tree)
    return tree


def _functions(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _defined_names(func):
    names = {func.name}
    for n in ast.walk(func):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.add(n.id)
        if isinstance(n, ast.FunctionDef):
            names.add(n.name)
    for a in func.args.args:
        names.add(a.arg)
    return names


_BUILTINS = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))


def _find_accumulators(func):
    accs = []
    for stmt in ast.walk(func):
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.List) and len(stmt.value.elts) == 0):
            name = stmt.targets[0].id
            for n2 in ast.walk(func):
                if (isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute)
                        and n2.func.attr == 'append' and isinstance(n2.func.value, ast.Name)
                        and n2.func.value.id == name):
                    accs.append(name)
                    break
    return list(dict.fromkeys(accs))


def _body_list_of(parent, node):
    for field in ('body', 'orelse', 'finalbody'):
        blk = getattr(parent, field, None)
        if isinstance(blk, list) and node in blk:
            return blk
    return None


_FLIP = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}
_OPTXT = {ast.Lt: '<', ast.Gt: '>', ast.LtE: '<=', ast.GtE: '>='}


# ----------------------------------------------------------------------
# Rule 1: selection running-best picks min instead of max -> flip operator
# ----------------------------------------------------------------------

def _flip_selection_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for for_node in ast.walk(tree):
        if not (isinstance(for_node, ast.For) and isinstance(for_node.target, ast.Name)):
            continue
        loop_var = for_node.target.id
        for stmt in for_node.body:
            if not (isinstance(stmt, ast.If) and len(stmt.body) == 1
                    and isinstance(stmt.body[0], ast.Assign)):
                continue
            assign = stmt.body[0]
            if not (len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name)
                    and isinstance(assign.value, ast.Name)):
                continue
            if assign.value.id != loop_var or assign.targets[0].id == loop_var:
                continue
            test = stmt.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
                continue
            left, right = test.left, test.comparators[0]
            if not (isinstance(left, ast.Subscript) and isinstance(left.value, ast.Name)
                    and isinstance(right, ast.Subscript) and isinstance(right.value, ast.Name)):
                continue
            op_t = type(test.ops[0])
            if op_t not in _FLIP:
                continue
            new_op = _OPTXT[_FLIP[op_t]]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            candidate = source[:le] + ' ' + new_op + ' ' + source[rs:]
            candidate = source[:le] + f' {new_op} ' + source[rs:]
            out.append(candidate)
    return out


# ----------------------------------------------------------------------
# Rule 2: assigning back into the loop variable instead of the accumulator
# ----------------------------------------------------------------------

def _swap_backward_assign(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for ifnode in ast.walk(tree):
        if not (isinstance(ifnode, ast.If) and len(ifnode.body) == 1
                and isinstance(ifnode.body[0], ast.Assign)):
            continue
        assign = ifnode.body[0]
        if not (len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name)
                and isinstance(assign.value, ast.Name)):
            continue
        for_node = _enclosing(ifnode, ast.For)
        if for_node is None or not isinstance(for_node.target, ast.Name):
            continue
        loop_var = for_node.target.id
        target_id = assign.targets[0].id
        value_id = assign.value.id
        if target_id == loop_var and value_id != loop_var:
            new_text = f"{value_id} = {target_id}"
            out.append(_splice(source, assign, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 3: statements after the for-loop reference the loop variable instead
# of the accumulator that was actually selected
# ----------------------------------------------------------------------

def _use_accumulator_after_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for for_node in ast.walk(tree):
        if not (isinstance(for_node, ast.For) and isinstance(for_node.target, ast.Name)):
            continue
        loop_var = for_node.target.id
        acc_name = None
        for stmt in for_node.body:
            if (isinstance(stmt, ast.If) and len(stmt.body) == 1
                    and isinstance(stmt.body[0], ast.Assign)):
                assign = stmt.body[0]
                if (len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name)
                        and isinstance(assign.value, ast.Name)
                        and assign.value.id == loop_var
                        and assign.targets[0].id != loop_var):
                    acc_name = assign.targets[0].id
                    break
        if not acc_name:
            continue
        parent = for_node.parent
        if parent is None:
            continue
        body_list = _body_list_of(parent, for_node)
        if not body_list:
            continue
        idx = body_list.index(for_node)
        following = body_list[idx + 1:]
        if not following:
            continue
        replacements = []
        for stmt in following:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Name) and n.id == loop_var and isinstance(n.ctx, ast.Load):
                    s, e = _span(source, n)
                    replacements.append((s, e, acc_name))
        if replacements:
            out.append(_multi_splice(source, replacements))
    return out


# ----------------------------------------------------------------------
# Rule 4: undefined container/variable name -> the function's parameter
# ----------------------------------------------------------------------

def _undefined_to_param(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        defined = _defined_names(func)
        bad_ids = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id == 'list' and isinstance(getattr(n, 'parent', None), ast.Subscript) \
                        and n.parent.value is n:
                    bad_ids.add(n.id)
                elif n.id not in defined and n.id not in _BUILTINS:
                    bad_ids.add(n.id)
        bad_ids.discard(param)
        if not bad_ids:
            continue
        replacements = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in bad_ids:
                s, e = _span(source, n)
                replacements.append((s, e, param))
        if replacements:
            out.append(_multi_splice(source, replacements))
    return out


# ----------------------------------------------------------------------
# Rule 5: `return X` where X is undefined but a clear list accumulator
# exists -> point the return at the accumulator
# ----------------------------------------------------------------------

def _fix_return_undefined_name(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        defined = _defined_names(func)
        accs = _find_accumulators(func)
        if len(accs) != 1:
            continue
        for n in ast.walk(func):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name):
                if n.value.id not in defined and n.value.id != accs[0]:
                    out.append(_splice(source, n.value, accs[0]))
    return out


# ----------------------------------------------------------------------
# Rule 6: function never returns -> add `return <accumulator>`
# ----------------------------------------------------------------------

def _append_missing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        accs = _find_accumulators(func)
        if len(accs) != 1 or not func.body:
            continue
        last = func.body[-1]
        indent = _indent_of(source, last)
        end = _span(source, last)[1]
        insertion = f"\n{indent}return {accs[0]}"
        out.append(source[:end] + insertion + source[end:])
    return out


# ----------------------------------------------------------------------
# Rule 7: trailing `print(x)` used instead of `return <accumulator>`
# ----------------------------------------------------------------------

def _print_to_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        accs = _find_accumulators(func)
        if len(accs) != 1:
            continue
        acc = accs[0]
        for n in ast.walk(func):
            if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                    and isinstance(n.value.func, ast.Name) and n.value.func.id == 'print'):
                host = n
                while host.parent is not func and host not in func.body:
                    host = host.parent
                    if host is None:
                        break
                if host is None:
                    continue
                if host is n:
                    out.append(_splice(source, n, f"return {acc}"))
                else:
                    ps, pe = _span(source, n)
                    he = _span(source, host)[1]
                    indent = _indent_of(source, host)
                    insertion = f"\n{indent}return {acc}"
                    reps = [(ps, pe, "pass"), (he, he, insertion)]
                    out.append(_multi_splice(source, reps))
    return out


# ----------------------------------------------------------------------
# Rule 8: `return X.reverse()` / `return X.reverse` returns None
# ----------------------------------------------------------------------

def _fix_return_reverse(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Return):
            continue
        obj = None
        if (isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr == 'reverse' and len(n.value.args) == 0):
            obj = n.value.func.value
        elif isinstance(n.value, ast.Attribute) and n.value.attr == 'reverse':
            obj = n.value.value
        if obj is None:
            continue
        obj_text = _text(source, obj)
        indent = _indent_of(source, n)
        new_text = f"{obj_text}.reverse()\n{indent}return {obj_text}"
        out.append(_splice(source, n, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 9: `.reverse`/`.sort` used as a statement without being called
# ----------------------------------------------------------------------

def _add_missing_call_parens(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Attribute)
                and n.value.attr in ('reverse', 'sort')):
            out.append(_splice(source, n.value, _text(source, n.value) + "()"))
    return out


# ----------------------------------------------------------------------
# Rule 10: `.reverse()` (or bare `.reverse`) wrongly executed every
# iteration instead of once after the loop
# ----------------------------------------------------------------------

def _move_reverse_after_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for loop_node in ast.walk(tree):
        if not isinstance(loop_node, (ast.For, ast.While)):
            continue
        body = loop_node.body
        if len(body) < 2 or not isinstance(body[-1], ast.Expr):
            continue
        val = body[-1].value
        obj = None
        if (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                and val.func.attr == 'reverse' and len(val.args) == 0):
            obj = val.func.value
        elif isinstance(val, ast.Attribute) and val.attr == 'reverse':
            obj = val.value
        if obj is None:
            continue
        obj_text = _text(source, obj)
        ls, le = _line_bounds(source, body[-1])
        loop_e = _span(source, loop_node)[1]
        indent = _indent_of(source, loop_node)
        insertion = f"\n{indent}{obj_text}.reverse()"
        reps = [(ls, le, ""), (loop_e, loop_e, insertion)]
        out.append(_multi_splice(source, reps))
    return out


# ----------------------------------------------------------------------
# Rule 11: naive swap without a temp variable (`a=b; b=a`)
# ----------------------------------------------------------------------

def _iter_blocks(tree):
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            blk = getattr(node, field, None)
            if isinstance(blk, list):
                yield blk


def _fix_naive_swap(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for block in _iter_blocks(tree):
        for i in range(len(block) - 1):
            a, b = block[i], block[i + 1]
            if not (isinstance(a, ast.Assign) and isinstance(b, ast.Assign)
                    and len(a.targets) == 1 and len(b.targets) == 1):
                continue
            t1 = _text(source, a.targets[0])
            v1 = _text(source, a.value)
            t2 = _text(source, b.targets[0])
            v2 = _text(source, b.value)
            if t1 != t2 and t1 == v2 and t2 == v1:
                s = _span(source, a)[0]
                e = _span(source, b)[1]
                new_text = f"{t1}, {t2} = {v1}, {v2}"
                out.append(source[:s] + new_text + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 12: tuple-swap RHS accidentally duplicated (`a[i],a[j] = a[j],a[j]`)
# ----------------------------------------------------------------------

def _fix_duplicate_swap_tuple(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1):
            continue
        tgt, val = n.targets[0], n.value
        if not (isinstance(tgt, ast.Tuple) and isinstance(val, ast.Tuple)
                and len(tgt.elts) == 2 and len(val.elts) == 2):
            continue
        v0 = _text(source, val.elts[0])
        v1 = _text(source, val.elts[1])
        if v0 == v1:
            t0 = _text(source, tgt.elts[0])
            t1 = _text(source, tgt.elts[1])
            new_val = f"{t1}, {t0}"
            out.append(_splice(source, val, new_val))
    return out


# ----------------------------------------------------------------------
# Rule 13: swapping a sub-field instead of the whole tuple element
# ----------------------------------------------------------------------

def _fix_subscript_whole_swap(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1):
            continue
        tgt, val = n.targets[0], n.value
        if not (isinstance(tgt, ast.Tuple) and isinstance(val, ast.Tuple)
                and len(tgt.elts) == 2 and len(val.elts) == 2):
            continue
        elts = list(tgt.elts) + list(val.elts)
        if not all(isinstance(e, ast.Subscript) and isinstance(e.value, ast.Subscript) for e in elts):
            continue
        ot0 = _text(source, tgt.elts[0].value)
        ot1 = _text(source, tgt.elts[1].value)
        ov0 = _text(source, val.elts[0].value)
        ov1 = _text(source, val.elts[1].value)
        new_text = f"{ot0}, {ot1} = {ov0}, {ov1}"
        out.append(_splice(source, n, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 14: mutation statements accidentally left inside the inner for
# loop, should run once per outer while-iteration
# ----------------------------------------------------------------------

def _dedent_mutations_out_of_inner_for(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for for_node in ast.walk(tree):
        if not isinstance(for_node, ast.For):
            continue
        parent = for_node.parent
        if not isinstance(parent, ast.While):
            continue
        body = for_node.body
        if len(body) < 2 or not isinstance(body[0], ast.If):
            continue
        trailing = body[1:]
        texts = [_text(source, s) for s in trailing]
        if not (any('.remove(' in t for t in texts) and any('.append(' in t for t in texts)):
            continue
        del_start = _line_bounds(source, trailing[0])[0]
        del_end = _line_bounds(source, trailing[-1])[1]
        removed = source[del_start:del_end]
        for_indent = _indent_of(source, for_node)
        lines = removed.splitlines(keepends=True)
        reindented = "".join((for_indent + ln.lstrip()) if ln.strip() else ln for ln in lines)
        for_e = _span(source, for_node)[1]
        reps = [(del_start, del_end, ""), (for_e, for_e, "\n" + reindented.rstrip('\n'))]
        out.append(_multi_splice(source, reps))
    return out


# ----------------------------------------------------------------------
# Rule 15: `return` placed inside the loop body instead of after it
# ----------------------------------------------------------------------

def _move_return_out_of_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for loop_node in ast.walk(tree):
        if not isinstance(loop_node, (ast.While, ast.For)):
            continue
        body = loop_node.body
        if len(body) > 1 and isinstance(body[-1], ast.Return):
            ret = body[-1]
            ret_text = _text(source, ret)
            del_start, del_end = _line_bounds(source, ret)
            loop_e = _span(source, loop_node)[1]
            indent = _indent_of(source, loop_node)
            insertion = f"\n{indent}{ret_text}"
            reps = [(del_start, del_end, ""), (loop_e, loop_e, insertion)]
            out.append(_multi_splice(source, reps))
    return out


# ----------------------------------------------------------------------
# Rule 16: accumulator returned ascending with no reversal
# ----------------------------------------------------------------------

def _insert_reverse_before_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        accs = _find_accumulators(func)
        if len(accs) != 1:
            continue
        acc = accs[0]
        if f"{acc}.reverse(" in source or f"{acc}[::-1]" in source:
            continue
        for n in ast.walk(func):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id == acc:
                indent = _indent_of(source, n)
                s = _span(source, n)[0]
                insertion = f"{acc}.reverse()\n{indent}"
                out.append(source[:s] + insertion + source[s:])
    return out


def _return_slice_reverse(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        accs = _find_accumulators(func)
        if len(accs) != 1:
            continue
        acc = accs[0]
        if f"{acc}.reverse(" in source or f"{acc}[::-1]" in source:
            continue
        for n in ast.walk(func):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id == acc:
                out.append(_splice(source, n.value, f"{acc}[::-1]"))
    return out


# ----------------------------------------------------------------------
# Rule 17: accumulator update assigned from an undefined name instead of
# the actual loop variable
# ----------------------------------------------------------------------

def _fix_undefined_loopvar_assignment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        defined = _defined_names(func)
        for ifnode in ast.walk(func):
            if not (isinstance(ifnode, ast.If) and len(ifnode.body) == 1
                    and isinstance(ifnode.body[0], ast.Assign)):
                continue
            assign = ifnode.body[0]
            if not (len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name)
                    and isinstance(assign.value, ast.Name)):
                continue
            val_id = assign.value.id
            if val_id in defined:
                continue
            for_node = _enclosing(ifnode, ast.For)
            if for_node is None or not isinstance(for_node.target, ast.Name):
                continue
            loop_id = for_node.target.id
            if loop_id != val_id:
                out.append(_splice(source, assign.value, loop_id))
    return out


# ----------------------------------------------------------------------
# Rule 18: bubble-sort adjacent compare on two subscripted fields picks
# the wrong order (ascending instead of descending)
# ----------------------------------------------------------------------

def _flip_adjacent_double_subscript_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Compare) and len(n.ops) == 1):
            continue
        left, right = n.left, n.comparators[0]
        if not (isinstance(left, ast.Subscript) and isinstance(left.value, ast.Subscript)
                and isinstance(right, ast.Subscript) and isinstance(right.value, ast.Subscript)):
            continue
        op_t = type(n.ops[0])
        if op_t not in (ast.Gt, ast.GtE):
            continue
        new_op = _OPTXT[_FLIP[op_t]]
        le = _span(source, left)[1]
        rs = _span(source, right)[0]
        out.append(source[:le] + f' {new_op} ' + source[rs:])
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="flip_selection_compare_direction",
                 apply=_flip_selection_compare,
                 symptoms=("wrong",)),
            Rule(name="swap_backward_assign_to_loopvar",
                 apply=_swap_backward_assign,
                 symptoms=("wrong",)),
            Rule(name="use_accumulator_after_loop",
                 apply=_use_accumulator_after_loop,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="undefined_name_to_param",
                 apply=_undefined_to_param,
                 symptoms=("err:NameError", "err:TypeError", "wrong")),
            Rule(name="fix_return_undefined_name",
                 apply=_fix_return_undefined_name,
                 symptoms=("err:NameError",)),
            Rule(name="append_missing_return",
                 apply=_append_missing_return,
                 symptoms=("wrong",)),
            Rule(name="print_to_return",
                 apply=_print_to_return,
                 symptoms=("wrong",)),
            Rule(name="fix_return_reverse_call",
                 apply=_fix_return_reverse,
                 symptoms=("wrong",)),
            Rule(name="add_missing_call_parens",
                 apply=_add_missing_call_parens,
                 symptoms=("wrong",)),
            Rule(name="move_reverse_after_loop",
                 apply=_move_reverse_after_loop,
                 symptoms=("wrong",)),
            Rule(name="fix_naive_swap_no_temp",
                 apply=_fix_naive_swap,
                 symptoms=("wrong",)),
            Rule(name="fix_duplicate_swap_tuple",
                 apply=_fix_duplicate_swap_tuple,
                 symptoms=("wrong",)),
            Rule(name="fix_subscript_whole_swap",
                 apply=_fix_subscript_whole_swap,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="dedent_mutations_out_of_inner_for",
                 apply=_dedent_mutations_out_of_inner_for,
                 symptoms=("timeout", "wrong")),
            Rule(name="move_return_out_of_loop",
                 apply=_move_return_out_of_loop,
                 symptoms=("wrong",)),
            Rule(name="insert_reverse_before_return",
                 apply=_insert_reverse_before_return,
                 symptoms=("wrong",)),
            Rule(name="return_slice_reverse",
                 apply=_return_slice_reverse,
                 symptoms=("wrong",)),
            Rule(name="fix_undefined_loopvar_assignment",
                 apply=_fix_undefined_loopvar_assignment,
                 symptoms=("err:NameError",)),
            Rule(name="flip_adjacent_double_subscript_compare",
                 apply=_flip_adjacent_double_subscript_compare,
                 symptoms=("wrong",)),
        ]