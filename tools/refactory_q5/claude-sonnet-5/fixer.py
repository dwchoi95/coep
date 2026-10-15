"""
Repair module for the Top-K assignment.

Each rule is a small, local, AST-located source-splice transformation
targeting one recurring misconception observed in student submissions.
"""

import ast
import builtins
import difflib

from src.core.repair import Rule


# ----------------------------------------------------------------------
# Helpers
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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _collect_bound_names(func):
    names = set()
    for a in func.args.args:
        names.add(a.arg)
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.For):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def _get_index_expr(node):
    idx = node.slice
    if hasattr(ast, "Index") and isinstance(idx, ast.Index):
        idx = idx.value
    return idx


# ----------------------------------------------------------------------
# Rule: flip min-finder to max-finder in tracker for-loop
# ----------------------------------------------------------------------

def flip_min_to_max(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for stmt in node.body:
                if isinstance(stmt, ast.If) and len(stmt.body) >= 1:
                    assign = stmt.body[0]
                    if (isinstance(assign, ast.Assign) and len(assign.targets) == 1
                            and isinstance(assign.targets[0], ast.Name)
                            and isinstance(assign.value, ast.Name)
                            and assign.value.id == loopvar):
                        test = stmt.test
                        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                                and isinstance(test.left, ast.Name)
                                and isinstance(test.comparators[0], ast.Name)):
                            op = test.ops[0]
                            left_id = test.left.id
                            right_id = test.comparators[0].id
                            tracker = assign.targets[0].id
                            if {left_id, right_id} != {loopvar, tracker}:
                                continue
                            is_max = ((left_id == loopvar and isinstance(op, ast.Gt)) or
                                      (left_id == tracker and isinstance(op, ast.Lt)))
                            if not is_max and isinstance(op, (ast.Lt, ast.Gt)):
                                newop = " > " if isinstance(op, ast.Lt) else " < "
                                ls, le = _span(source, test.left)
                                rs, re_ = _span(source, test.comparators[0])
                                new_cmp = source[ls:le] + newop + source[rs:re_]
                                out.append(_splice(source, test, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule: tracker-update assigns to a wrong/unrelated variable name
# ----------------------------------------------------------------------

def fix_tracker_assign_target(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for stmt in node.body:
                if isinstance(stmt, ast.If) and len(stmt.body) >= 1:
                    assign = stmt.body[0]
                    if (isinstance(assign, ast.Assign) and len(assign.targets) == 1
                            and isinstance(assign.targets[0], ast.Name)
                            and isinstance(assign.value, ast.Name)
                            and assign.value.id == loopvar):
                        target_name = assign.targets[0].id
                        test = stmt.test
                        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                                and isinstance(test.left, ast.Name)
                                and isinstance(test.comparators[0], ast.Name)):
                            op = test.ops[0]
                            left_id = test.left.id
                            right_id = test.comparators[0].id
                            tracker = None
                            if left_id == loopvar and isinstance(op, ast.Gt):
                                tracker = right_id
                            elif right_id == loopvar and isinstance(op, ast.Lt):
                                tracker = left_id
                            if tracker and tracker != target_name:
                                out.append(_splice(source, assign.targets[0], tracker))
    return out


# ----------------------------------------------------------------------
# Rule: swap order of remove(max(x)) / append(max(x))
# ----------------------------------------------------------------------

def _is_call(stmt, attr):
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute) and stmt.value.func.attr == attr
            and len(stmt.value.args) == 1 and isinstance(stmt.value.args[0], ast.Call)
            and isinstance(stmt.value.args[0].func, ast.Name) and stmt.value.args[0].func.id == 'max'
            and len(stmt.value.args[0].args) == 1 and isinstance(stmt.value.args[0].args[0], ast.Name))


def fix_remove_before_append_order(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            if _is_call(s1, 'remove') and _is_call(s2, 'append'):
                l1 = s1.value.args[0].args[0].id
                l2 = s2.value.args[0].args[0].id
                if l1 == l2:
                    s1s, s1e = _span(source, s1)
                    s2s, s2e = _span(source, s2)
                    t1 = source[s1s:s1e]
                    t2 = source[s2s:s2e]
                    indent = ' ' * s1.col_offset
                    new_text = t2 + '\n' + indent + t1
                    out.append(source[:s1s] + new_text + source[s2e:])
    return out


# ----------------------------------------------------------------------
# Rule: normalize hard-coded / off-by-one slice upper bound to k
# ----------------------------------------------------------------------

def fix_slice_bound_to_k(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if len(func.args.args) < 2:
            continue
        k_name = func.args.args[1].arg
        for node in ast.walk(func):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                sl = node.slice
                if sl.lower is None and sl.upper is not None and sl.step is None:
                    upper = sl.upper
                    if isinstance(upper, ast.Name) and upper.id == k_name:
                        continue
                    replace = False
                    if (isinstance(upper, ast.BinOp) and isinstance(upper.left, ast.Name)
                            and upper.left.id == k_name and isinstance(upper.op, (ast.Add, ast.Sub))):
                        replace = True
                    elif isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                        replace = True
                    if replace:
                        out.append(_splice(source, upper, k_name))
    return out


# ----------------------------------------------------------------------
# Rule: while ... <= k  ->  while ... < k
# ----------------------------------------------------------------------

def fix_lte_len_k_bound(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if len(func.args.args) < 2:
            continue
        k_name = func.args.args[1].arg
        for node in ast.walk(func):
            if (isinstance(node, ast.While) and isinstance(node.test, ast.Compare)
                    and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.LtE)):
                right = node.test.comparators[0]
                if isinstance(right, ast.Name) and right.id == k_name:
                    ls, le = _span(source, node.test.left)
                    rs, re_ = _span(source, right)
                    new_cmp = source[ls:le] + " < " + source[rs:re_]
                    out.append(_splice(source, node.test, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule: while k >= 0  ->  while k > 0
# ----------------------------------------------------------------------

def fix_gte_zero_bound(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.While) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.GtE)):
            left = node.test.left
            right = node.test.comparators[0]
            if isinstance(right, ast.Constant) and right.value == 0 and isinstance(left, ast.Name):
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " > " + source[rs:re_]
                out.append(_splice(source, node.test, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule: `.append[x]` / `.remove[x]` / `.pop[x]` -> proper call syntax
# ----------------------------------------------------------------------

def fix_subscript_call_syntax(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr in ('append', 'remove', 'pop', 'index')):
            idx = _get_index_expr(node)
            if isinstance(idx, ast.Slice):
                continue
            obj_s, obj_e = _span(source, node.value)
            idx_s, idx_e = _span(source, idx)
            new_text = source[obj_s:obj_e] + "(" + source[idx_s:idx_e] + ")"
            out.append(_splice(source, node, new_text))
    return out


# ----------------------------------------------------------------------
# Rule: missing return statement for the accumulator list
# ----------------------------------------------------------------------

def fix_missing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        body = func.body
        if not body:
            continue
        real_body = [s for s in body if not isinstance(s, ast.Pass)]
        if real_body and isinstance(real_body[-1], ast.Return):
            continue
        if any(isinstance(s, ast.Return) for s in body):
            continue
        acc_candidates = []
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.List) and len(node.value.elts) == 0):
                acc_candidates.append(node.targets[0].id)
        if not acc_candidates:
            continue
        acc = acc_candidates[-1]
        last_stmt = body[-1]
        indent = ' ' * last_stmt.col_offset
        _, e = _span(source, last_stmt)
        insertion = f"\n{indent}return {acc}"
        out.append(source[:e] + insertion + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: return uses wrong (non-accumulator) list variable
# ----------------------------------------------------------------------

def fix_return_wrong_variable(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        appended_vars = set()
        for node in ast.walk(func):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)):
                appended_vars.add(node.func.value.id)
        if len(appended_vars) != 1:
            continue
        acc = next(iter(appended_vars))
        for node in ast.walk(func):
            if (isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript)
                    and isinstance(node.value.value, ast.Name)):
                rname = node.value.value.id
                if rname != acc:
                    out.append(_splice(source, node.value.value, acc))
    return out


# ----------------------------------------------------------------------
# Rule: append() called on undefined object name -> the real accumulator
# ----------------------------------------------------------------------

def fix_undefined_accumulator(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        bound = _collect_bound_names(func)
        list_inits = []
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.List) and len(node.value.elts) == 0):
                list_inits.append(node.targets[0].id)
        if not list_inits:
            continue
        for node in ast.walk(func):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)):
                vname = node.func.value.id
                if vname not in bound:
                    cands = difflib.get_close_matches(vname, list_inits, n=1, cutoff=0.0) or list_inits
                    out.append(_splice(source, node.func.value, cands[0]))
    return out


# ----------------------------------------------------------------------
# Rule: append(raw_list) when the max value was just computed separately
# ----------------------------------------------------------------------

def fix_append_raw_list_instead_of_max(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        for node in ast.walk(func):
            body = getattr(node, 'body', None)
            if not isinstance(body, list):
                continue
            last_max_assign = None
            for stmt in body:
                if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and isinstance(stmt.value, ast.Call)
                        and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == 'max'
                        and len(stmt.value.args) == 1 and isinstance(stmt.value.args[0], ast.Name)):
                    last_max_assign = (stmt.targets[0].id, stmt.value.args[0].id)
                for sub in ast.walk(stmt):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr == 'append' and len(sub.args) == 1
                            and isinstance(sub.args[0], ast.Name) and last_max_assign):
                        varname, listname = last_max_assign
                        if sub.args[0].id == listname:
                            out.append(_splice(source, sub.args[0], varname))
    return out


# ----------------------------------------------------------------------
# Rule: undefined name used as append/remove arg after a tracker for-loop
# ----------------------------------------------------------------------

def fix_undefined_ref_after_tracker_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        bound = _collect_bound_names(func)
        for node in ast.walk(func):
            if isinstance(node, ast.While):
                tracker = None
                for stmt in node.body:
                    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                            and isinstance(stmt.targets[0], ast.Name)):
                        tracker = stmt.targets[0].id
                        break
                if tracker is None:
                    continue
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr in ('append', 'remove') and len(sub.args) == 1
                            and isinstance(sub.args[0], ast.Name)):
                        argname = sub.args[0].id
                        if argname not in bound and argname != tracker:
                            out.append(_splice(source, sub.args[0], tracker))
    return out


# ----------------------------------------------------------------------
# Rule: generic close-match typo rename for undefined local names
# ----------------------------------------------------------------------

def fix_generic_typo_rename(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    builtins_set = set(dir(builtins))
    module_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for func in _funcs(tree):
        bound = _collect_bound_names(func) | module_funcs
        loads = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                loads.setdefault(node.id, []).append(node)
        for name, nodes in loads.items():
            if name in bound or name in builtins_set:
                continue
            matches = difflib.get_close_matches(name, list(bound), n=1, cutoff=0.75)
            if len(matches) == 1:
                repl = matches[0]
                for node in nodes:
                    out.append(_splice(source, node, repl))
    return out


# ----------------------------------------------------------------------
# Rule: append(list.remove(x)) -> append(x); list.remove(x)  (remove()->None)
# ----------------------------------------------------------------------

def fix_append_of_remove_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute) and call.func.attr == 'append'
                    and len(call.args) == 1):
                inner = call.args[0]
                if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                        and inner.func.attr == 'remove' and len(inner.args) == 1):
                    outer_s, outer_e = _span(source, call.func.value)
                    list_s, list_e = _span(source, inner.func.value)
                    arg_s, arg_e = _span(source, inner.args[0])
                    indent = ' ' * node.col_offset
                    append_target_text = source[outer_s:outer_e]
                    list_text = source[list_s:list_e]
                    arg_text = source[arg_s:arg_e]
                    new_text = (f"{append_target_text}.append({arg_text})\n"
                                f"{indent}{list_text}.remove({arg_text})")
                    out.append(_splice(source, node, new_text))
    return out


# ----------------------------------------------------------------------
# Rule: pop(max(lst)) -> pop(lst.index(max(lst)))  (pop needs an index)
# ----------------------------------------------------------------------

def fix_pop_with_value_instead_of_index(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'pop' and len(node.args) == 1):
            arg = node.args[0]
            if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'max'
                    and len(arg.args) == 1 and isinstance(arg.args[0], ast.Name)):
                listname = arg.args[0].id
                if isinstance(node.func.value, ast.Name) and node.func.value.id == listname:
                    arg_s, arg_e = _span(source, arg)
                    arg_text = source[arg_s:arg_e]
                    new_arg = f"{listname}.index({arg_text})"
                    out.append(_splice(source, arg, new_arg))
    return out


# ----------------------------------------------------------------------
# Rule: for i in range(len(x)): if i == max(x)  ->  if x[i] == max(x)
# ----------------------------------------------------------------------

def fix_range_len_missing_subscript(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == 'range' and len(node.iter.args) == 1):
            rng_arg = node.iter.args[0]
            if (isinstance(rng_arg, ast.Call) and isinstance(rng_arg.func, ast.Name)
                    and rng_arg.func.id == 'len' and len(rng_arg.args) == 1
                    and isinstance(rng_arg.args[0], ast.Name)):
                listname = rng_arg.args[0].id
                loopvar = node.target.id
                for stmt in ast.walk(node):
                    if (isinstance(stmt, ast.Compare) and len(stmt.ops) == 1
                            and isinstance(stmt.ops[0], ast.Eq)):
                        left = stmt.left
                        if isinstance(left, ast.Name) and left.id == loopvar:
                            right = stmt.comparators[0]
                            if (isinstance(right, ast.Call) and isinstance(right.func, ast.Name)
                                    and right.func.id == 'max'):
                                out.append(_splice(source, left, f"{listname}[{loopvar}]"))
    return out


# ----------------------------------------------------------------------
# Rule: lst.extend([i])  -> lst.extend([lst[i]])   (index vs. value)
# ----------------------------------------------------------------------

def fix_extend_index_should_be_value(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'extend' and isinstance(node.func.value, ast.Name)
                and len(node.args) == 1 and isinstance(node.args[0], ast.List)
                and len(node.args[0].elts) == 1):
            elt = node.args[0].elts[0]
            if isinstance(elt, ast.Name):
                listname = node.func.value.id
                out.append(_splice(source, elt, f"{listname}[{elt.id}]"))
    return out


# ----------------------------------------------------------------------
# Rule: broken swap without temp (a[i]=a[j]; a[j]=a[i]) -> tuple swap
# ----------------------------------------------------------------------

def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def fix_broken_swap(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            if (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)
                    and len(s1.targets) == 1 and len(s2.targets) == 1):
                t1, t2 = s1.targets[0], s2.targets[0]
                v1, v2 = s1.value, s2.value
                if (isinstance(t1, ast.Subscript) and isinstance(t2, ast.Subscript)
                        and isinstance(v1, ast.Subscript) and isinstance(v2, ast.Subscript)):
                    if _text(source, t1) == _text(source, v2) and _text(source, t2) == _text(source, v1):
                        t1_text = _text(source, t1)
                        t2_text = _text(source, t2)
                        s1s, _ = _span(source, s1)
                        _, s2e = _span(source, s2)
                        new_text = f"{t1_text}, {t2_text} = {t2_text}, {t1_text}"
                        out.append(source[:s1s] + new_text + source[s2e:])
    return out


# ----------------------------------------------------------------------
# Rule: single-pass bubble compare without an outer repeat loop
# ----------------------------------------------------------------------

def fix_missing_outer_pass_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.args.args:
            continue
        listname = func.args.args[0].arg
        top_fors = [s for s in func.body if isinstance(s, ast.For)]
        top_whiles = [s for s in func.body if isinstance(s, ast.While)]
        if len(top_fors) == 1 and len(top_whiles) == 0:
            forloop = top_fors[0]
            has_compare = any(isinstance(n, ast.Compare) for n in ast.walk(forloop))
            if has_compare:
                fs, fe = _span(source, forloop)
                block_text = source[fs:fe]
                indented = '\n'.join(
                    ('    ' + line if line.strip() else line)
                    for line in block_text.splitlines()
                )
                new_text = f"for _pass_outer in range(len({listname})):\n{indented}"
                out.append(source[:fs] + new_text + source[fe:])
    return out


# ----------------------------------------------------------------------
# Rule: missing k<=0 guard (break-after-append pattern mishandles k==0)
# ----------------------------------------------------------------------

def fix_missing_k_zero_guard(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.body or len(func.args.args) < 2:
            continue
        first = func.body[0]
        if isinstance(first, ast.If):
            names_in_test = [n.id for n in ast.walk(first.test) if isinstance(n, ast.Name)]
            if func.args.args[1].arg in names_in_test:
                continue
        found = False
        for node in ast.walk(func):
            if isinstance(node, (ast.While, ast.For)):
                body = node.body
                append_idx = None
                break_idx = None
                for idx, stmt in enumerate(body):
                    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                        append_idx = idx
                    if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                            and isinstance(stmt.value.func, ast.Attribute)
                            and stmt.value.func.attr == 'append'):
                        append_idx = idx
                    if isinstance(stmt, ast.If):
                        for sub in ast.walk(stmt):
                            if isinstance(sub, ast.Break):
                                break_idx = idx
                if append_idx is not None and break_idx is not None and append_idx < break_idx:
                    found = True
                    break
        if found:
            k_name = func.args.args[1].arg
            first_stmt = func.body[0]
            indent = ' ' * first_stmt.col_offset
            insertion = f"if {k_name} <= 0:\n{indent}    return []\n{indent}"
            s, _ = _span(source, first_stmt)
            out.append(source[:s] + insertion + source[s:])
    return out


# ----------------------------------------------------------------------
# Rule: range(k-1) -> range(k)
# ----------------------------------------------------------------------

def fix_range_k_minus_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if len(func.args.args) < 2:
            continue
        k_name = func.args.args[1].arg
        for node in ast.walk(func):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'range' and len(node.args) == 1):
                arg = node.args[0]
                if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
                        and isinstance(arg.left, ast.Name) and arg.left.id == k_name
                        and isinstance(arg.right, ast.Constant) and arg.right.value == 1):
                    out.append(_splice(source, arg, k_name))
    return out


# ----------------------------------------------------------------------
# Rule: missing lst.remove(max(lst)) causes infinite repeat of the same max
# ----------------------------------------------------------------------

def fix_missing_remove_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.While, ast.For)):
            continue
        body = node.body
        max_calls = []
        remove_present = False
        for stmt in body:
            for sub in ast.walk(stmt):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                        and sub.func.id == 'max' and len(sub.args) == 1
                        and isinstance(sub.args[0], ast.Name)):
                    max_calls.append((stmt, sub.args[0].id))
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr in ('remove', 'pop')):
                    remove_present = True
        if max_calls and not remove_present:
            stmt, lname = max_calls[0]
            _, e = _span(source, stmt)
            indent = ' ' * stmt.col_offset
            insertion = f"\n{indent}{lname}.remove(max({lname}))"
            out.append(source[:e] + insertion + source[e:])
    return out


# ----------------------------------------------------------------------
# Fixer
# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="flip_min_to_max_extremum",
                 apply=flip_min_to_max,
                 symptoms=("wrong",)),
            Rule(name="tracker_assign_wrong_var",
                 apply=fix_tracker_assign_target,
                 symptoms=("wrong",)),
            Rule(name="swap_remove_append_order",
                 apply=fix_remove_before_append_order,
                 symptoms=("wrong",)),
            Rule(name="slice_bound_normalize_to_k",
                 apply=fix_slice_bound_to_k,
                 symptoms=("wrong",)),
            Rule(name="lte_len_k_bound_off_by_one",
                 apply=fix_lte_len_k_bound,
                 symptoms=("wrong", "timeout")),
            Rule(name="gte_zero_bound_off_by_one",
                 apply=fix_gte_zero_bound,
                 symptoms=("wrong",)),
            Rule(name="subscript_should_be_call",
                 apply=fix_subscript_call_syntax,
                 symptoms=("err:TypeError",)),
            Rule(name="missing_return_statement",
                 apply=fix_missing_return,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="return_wrong_accumulator_variable",
                 apply=fix_return_wrong_variable,
                 symptoms=("wrong",)),
            Rule(name="undefined_accumulator_object",
                 apply=fix_undefined_accumulator,
                 symptoms=("err:NameError",)),
            Rule(name="append_raw_list_instead_of_max",
                 apply=fix_append_raw_list_instead_of_max,
                 symptoms=("wrong",)),
            Rule(name="undefined_ref_after_tracker_loop",
                 apply=fix_undefined_ref_after_tracker_loop,
                 symptoms=("err:NameError",)),
            Rule(name="generic_typo_rename",
                 apply=fix_generic_typo_rename,
                 symptoms=("err:NameError",)),
            Rule(name="append_of_remove_returns_none",
                 apply=fix_append_of_remove_call,
                 symptoms=("wrong",)),
            Rule(name="pop_value_instead_of_index",
                 apply=fix_pop_with_value_instead_of_index,
                 symptoms=("wrong", "err:ValueError")),
            Rule(name="range_len_missing_subscript",
                 apply=fix_range_len_missing_subscript,
                 symptoms=("wrong",)),
            Rule(name="extend_index_should_be_value",
                 apply=fix_extend_index_should_be_value,
                 symptoms=("wrong",)),
            Rule(name="broken_swap_without_temp",
                 apply=fix_broken_swap,
                 symptoms=("wrong",)),
            Rule(name="missing_outer_pass_loop",
                 apply=fix_missing_outer_pass_loop,
                 symptoms=("wrong",)),
            Rule(name="missing_k_zero_guard",
                 apply=fix_missing_k_zero_guard,
                 symptoms=("wrong",)),
            Rule(name="range_k_minus_one_to_k",
                 apply=fix_range_k_minus_one,
                 symptoms=("wrong",)),
            Rule(name="missing_remove_after_max",
                 apply=fix_missing_remove_call,
                 symptoms=("wrong", "timeout")),
        ]