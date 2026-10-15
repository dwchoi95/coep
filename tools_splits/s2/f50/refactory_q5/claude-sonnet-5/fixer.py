"""
Repair module for the Top-K assignment.

Each rule locates a specific AST pattern associated with a known
misconception from the class's submissions and produces one or more
candidate patches by splicing small, local edits into the original
source text (never rebuilding the whole program).
"""

import ast
import builtins
import difflib

from src.core.repair import Rule

_BUILTINS = set(dir(builtins))


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


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _line_span(source, node):
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    start_line_idx = node.lineno - 1
    end_line_idx = node.end_lineno - 1
    line_start = starts[start_line_idx]
    end_idx = end_line_idx + 1
    line_end = starts[end_idx] if end_idx < len(starts) else starts[-1]
    return line_start, line_end


def _apply_many(source, replacements):
    out = source
    for s, e, text in sorted(replacements, key=lambda r: r[0], reverse=True):
        out = out[:s] + text + out[e:]
    return out


def _unwrap_index(sl):
    if isinstance(sl, ast.Index):
        return sl.value
    return sl


def _closest(name, candidates):
    name_l = name.lower()
    best = None
    for c in candidates:
        if c == name:
            continue
        cl = c.lower()
        if name_l in cl or cl in name_l:
            if best is None or abs(len(c) - len(name)) < abs(len(best) - len(name)):
                best = c
    if best:
        return best
    scored = [(c, difflib.SequenceMatcher(None, name, c).ratio())
              for c in candidates if c != name]
    scored.sort(key=lambda x: -x[1])
    if scored and scored[0][1] >= 0.72:
        return scored[0][0]
    return None


def _find_accumulator(fn):
    empty_lists = set()
    for node in ast.walk(fn):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.List) and len(node.value.elts) == 0):
            empty_lists.add(node.targets[0].id)
    appended = set()
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)):
            appended.add(node.func.value.id)
    accs = [c for c in empty_lists if c in appended]
    if len(accs) == 1:
        return accs[0]
    return None


def _find_track_var(for_node):
    t = for_node.target
    if not isinstance(t, ast.Name):
        return None, None
    if len(for_node.body) != 1 or not isinstance(for_node.body[0], ast.If):
        return None, None
    stmt = for_node.body[0]
    test = stmt.test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
        return None, None
    if not isinstance(test.ops[0], (ast.Gt, ast.Lt, ast.GtE, ast.LtE)):
        return None, None
    left, right = test.left, test.comparators[0]
    if not (isinstance(left, ast.Name) and isinstance(right, ast.Name)):
        return None, None
    names = [left.id, right.id]
    if t.id not in names:
        return None, None
    others = [n for n in names if n != t.id]
    if not others:
        return None, None
    track_name = others[0]
    if len(stmt.body) != 1 or not isinstance(stmt.body[0], ast.Assign):
        return None, None
    assign = stmt.body[0]
    if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
        return None, None
    if assign.targets[0].id != track_name:
        return None, None
    if not (isinstance(assign.value, ast.Name) and assign.value.id == t.id):
        return None, None
    return t.id, track_name


def _safe(fn):
    def wrapper(source):
        try:
            result = fn(source)
        except Exception:
            return []
        out = []
        seen = set()
        for r in result or []:
            if isinstance(r, str) and r != source and r not in seen:
                seen.add(r)
                out.append(r)
        return out
    return wrapper


# ----------------------------------------------------------------------
# Rule 1: append/remove uses the max-finding loop variable instead of
# the variable that actually tracks the running max.
# ----------------------------------------------------------------------

def r_append_loop_var_instead_of_tracked(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i, stmt in enumerate(body):
            if not isinstance(stmt, ast.For):
                continue
            loop_var, track_var = _find_track_var(stmt)
            if not loop_var or not track_var:
                continue
            reps = []
            for later in body[i + 1:]:
                for sub in ast.walk(later):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr in ('append', 'remove')):
                        for arg in sub.args:
                            if isinstance(arg, ast.Name) and arg.id == loop_var:
                                s, e = _span(source, arg)
                                reps.append((s, e, track_var))
            if reps:
                results.append(_apply_many(source, reps))
    return results


# ----------------------------------------------------------------------
# Rule 2: the final return slices the wrong variable (e.g. the mutated
# input list) instead of the accumulator that was actually built up.
# ----------------------------------------------------------------------

def r_return_wrong_accumulator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        acc = _find_accumulator(fn)
        if not acc:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                val = node.value.value
                if isinstance(val, ast.Name) and val.id != acc:
                    results.append(_splice(source, val, acc))
    return results


# ----------------------------------------------------------------------
# Rule 3: a local variable is assigned the result of calling a module
# function of the same name -> UnboundLocalError. Rename the local var,
# leaving the actual call target untouched.
# ----------------------------------------------------------------------

def r_rename_shadowed_function_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    results = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        shadow_name = None
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                tgt = node.targets[0].id
                val = node.value
                if (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                        and val.func.id == tgt and tgt in func_names):
                    shadow_name = tgt
                    break
        if not shadow_name:
            continue
        new_name = shadow_name + "_local"
        call_func_ids = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == shadow_name):
                call_func_ids.add(id(node.func))
        reps = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and node.id == shadow_name:
                if id(node) in call_func_ids:
                    continue
                s, e = _span(source, node)
                reps.append((s, e, new_name))
        if reps:
            results.append(_apply_many(source, reps))
    return results


# ----------------------------------------------------------------------
# Rule 4: an undefined (typoed) identifier closely matches a variable
# actually assigned in the function; replace all its load-occurrences.
# ----------------------------------------------------------------------

def r_undefined_name_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    module_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    results = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        assigned = set(a.arg for a in fn.args.args)
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    assigned.add(node.target.id)
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    assigned.add(node.target.id)
        reps = []
        memo = {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                nid = node.id
                if nid in assigned or nid in module_funcs or nid in _BUILTINS:
                    continue
                if nid not in memo:
                    memo[nid] = _closest(nid, assigned)
                match = memo[nid]
                if match:
                    s, e = _span(source, node)
                    reps.append((s, e, match))
        if reps:
            results.append(_apply_many(source, reps))
    return results


# ----------------------------------------------------------------------
# Rule 5: inside `if a > b: X = a_or_b`, X is a stray unused variable
# instead of the variable that is actually being tracked.
# ----------------------------------------------------------------------

def r_wrong_assign_target_in_maxloop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1):
            continue
        if not isinstance(node.test.ops[0], (ast.Gt, ast.Lt, ast.GtE, ast.LtE)):
            continue
        left, right = node.test.left, node.test.comparators[0]
        if not (isinstance(left, ast.Name) and isinstance(right, ast.Name)):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Assign):
            continue
        assign = node.body[0]
        if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
            continue
        if not isinstance(assign.value, ast.Name):
            continue
        v = assign.value.id
        t = assign.targets[0].id
        if v == left.id:
            track = right.id
        elif v == right.id:
            track = left.id
        else:
            continue
        if t != track and t != v:
            results.append(_splice(source, assign.targets[0], track))
    return results


# ----------------------------------------------------------------------
# Rule 6: `m = max(x)` followed by `acc.append(wrong_arg)` where the
# argument should have been `m`.
# ----------------------------------------------------------------------

def r_append_wrong_arg_after_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            stmt, nxt = body[i], body[i + 1]
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            if not (isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name)
                    and stmt.value.func.id == 'max'):
                continue
            m = stmt.targets[0].id
            if not (isinstance(nxt, ast.Expr) and isinstance(nxt.value, ast.Call)
                    and isinstance(nxt.value.func, ast.Attribute)
                    and nxt.value.func.attr == 'append'):
                continue
            call = nxt.value
            if len(call.args) != 1 or not isinstance(call.args[0], ast.Name):
                continue
            arg = call.args[0]
            if arg.id != m:
                results.append(_splice(source, arg, m))
    return results


# ----------------------------------------------------------------------
# Rule 7: `obj.append[x]` / `obj.remove[x]` written with brackets
# instead of a call.
# ----------------------------------------------------------------------

def r_bracket_to_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Subscript):
            sub = node.value
            if (isinstance(sub.value, ast.Attribute)
                    and sub.value.attr in ('append', 'remove', 'pop', 'extend')):
                attr_s, attr_e = _span(source, sub.value)
                attr_text = source[attr_s:attr_e]
                sl = _unwrap_index(sub.slice)
                sl_s, sl_e = _span(source, sl)
                sl_text = source[sl_s:sl_e]
                new_text = attr_text + "(" + sl_text + ")"
                results.append(_splice(source, node.value, new_text))
    return results


# ----------------------------------------------------------------------
# Rule 8: a while loop counted with a plain scalar counter compared to
# k, but the counter is never incremented.
# ----------------------------------------------------------------------

def r_missing_counter_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        if not isinstance(test.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.NotEq)):
            continue
        left, right = test.left, test.comparators[0]
        if not (isinstance(left, ast.Name) and isinstance(right, ast.Name)):
            continue
        counter_name = left.id if left.id != 'k' else (right.id if right.id != 'k' else None)
        if not counter_name:
            continue
        incremented = False
        for sub in ast.walk(node):
            if sub is node:
                continue
            if (isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name)
                    and sub.target.id == counter_name):
                incremented = True
            if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                    and isinstance(sub.targets[0], ast.Name)
                    and sub.targets[0].id == counter_name
                    and isinstance(sub.value, ast.BinOp)
                    and isinstance(sub.value.left, ast.Name)
                    and sub.value.left.id == counter_name):
                incremented = True
        if incremented or not node.body:
            continue
        last_stmt = node.body[-1]
        indent = ' ' * node.body[0].col_offset
        insert_line = f"{indent}{counter_name} += 1\n"
        _, last_end = _line_span(source, last_stmt)
        results.append(source[:last_end] + insert_line + source[last_end:])
    return results


# ----------------------------------------------------------------------
# Rule 9: function builds an accumulator but never returns it.
# ----------------------------------------------------------------------

def r_missing_return_statement(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if any(isinstance(n, ast.Return) for n in ast.walk(fn)):
            continue
        acc = _find_accumulator(fn)
        if not acc or not fn.body:
            continue
        last_stmt = fn.body[-1]
        indent = ' ' * fn.body[0].col_offset
        insert_line = f"{indent}return {acc}\n"
        _, last_end = _line_span(source, last_stmt)
        results.append(source[:last_end] + insert_line + source[last_end:])
    return results


# ----------------------------------------------------------------------
# Rule 10: off-by-one arithmetic on k inside range()/slices.
# ----------------------------------------------------------------------

def r_k_off_by_one_arith(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        target_node = None
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'range' and len(node.args) == 1):
            target_node = node.args[0]
        elif isinstance(node, ast.Slice) and node.upper is not None:
            target_node = node.upper
        if target_node is None:
            continue
        if (isinstance(target_node, ast.BinOp) and isinstance(target_node.op, (ast.Add, ast.Sub))
                and isinstance(target_node.right, ast.Constant) and target_node.right.value == 1
                and isinstance(target_node.left, ast.Name)):
            results.append(_splice(source, target_node, target_node.left.id))
    return results


# ----------------------------------------------------------------------
# Rule 11: `while len(acc) <= k:` should be `< k`.
# ----------------------------------------------------------------------

def r_le_k_to_lt_k_while(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.While) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1):
            continue
        op = node.test.ops[0]
        left, right = node.test.left, node.test.comparators[0]
        if (isinstance(op, ast.LtE) and isinstance(right, ast.Name) and right.id == 'k'
                and isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                and left.func.id == 'len'):
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " < " + source[rs:re_]
            results.append(_splice(source, node.test, new_cmp))
    return results


# ----------------------------------------------------------------------
# Rule 12: a hardcoded integer literal used as the slice bound in the
# final return of top_k, instead of the k parameter.
# ----------------------------------------------------------------------

def r_hardcoded_slice_bound_to_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for fn in ast.walk(tree):
        if not (isinstance(fn, ast.FunctionDef) and fn.name == 'top_k'):
            continue
        if len(fn.args.args) < 2:
            continue
        kparam = fn.args.args[1].arg
        for node in ast.walk(fn):
            if not isinstance(node, ast.Return):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Subscript):
                    sl = _unwrap_index(sub.slice)
                    if (isinstance(sl, ast.Slice) and isinstance(sl.upper, ast.Constant)
                            and isinstance(sl.upper.value, int)):
                        results.append(_splice(source, sl.upper, kparam))
    return results


# ----------------------------------------------------------------------
# Rule 13: `lst.remove(max(lst))` performed before `acc.append(max(lst))`
# - wrong order discards the true maximum.
# ----------------------------------------------------------------------

def _is_attr_call_on_max(stmt, attr):
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return False
    call = stmt.value
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == attr):
        return False
    if len(call.args) != 1 or not isinstance(call.args[0], ast.Call):
        return False
    inner = call.args[0]
    return isinstance(inner.func, ast.Name) and inner.func.id == 'max'


def r_swap_remove_before_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if _is_attr_call_on_max(a, 'remove') and _is_attr_call_on_max(b, 'append'):
                a_s, a_e = _line_span(source, a)
                b_s, b_e = _line_span(source, b)
                a_text = source[a_s:a_e]
                b_text = source[b_s:b_e]
                results.append(source[:a_s] + b_text + a_text + source[b_e:])
    return results


# ----------------------------------------------------------------------
# Rule 14: an initializer like `biggest = lst[0]` is placed as the first
# statement *inside* the for-loop that scans lst, resetting it every
# iteration; it should precede the loop instead.
# ----------------------------------------------------------------------

def r_hoist_initializer_out_of_for_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and len(node.body) > 1):
            continue
        first = node.body[0]
        if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)):
            continue
        if not isinstance(first.value, ast.Subscript):
            continue
        sub = first.value
        if not isinstance(sub.value, ast.Name) or not isinstance(node.iter, ast.Name):
            continue
        if sub.value.id != node.iter.id:
            continue
        idx = _unwrap_index(sub.slice)
        if not (isinstance(idx, ast.Constant) and idx.value == 0):
            continue
        line_s, line_e = _line_span(source, first)
        assign_text = source[line_s:line_e].strip('\n')
        indent = ' ' * node.col_offset
        new_line = indent + assign_text.strip() + '\n'
        new_source = source[:line_s] + source[line_e:]
        for_line_s, _ = _line_span(source, node)
        new_source = new_source[:for_line_s] + new_line + new_source[for_line_s:]
        results.append(new_source)
    return results


# ----------------------------------------------------------------------
# Rule 15: the max-tracking comparison refers back to the frozen
# initial value (container[0]) instead of the running tracked variable.
# ----------------------------------------------------------------------

def r_stale_initial_value_in_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i, stmt in enumerate(body):
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            track = stmt.targets[0].id
            val = stmt.value
            if not isinstance(val, ast.Subscript) or not isinstance(val.value, ast.Name):
                continue
            container = val.value.id
            idx = _unwrap_index(val.slice)
            if not (isinstance(idx, ast.Constant) and idx.value == 0):
                continue
            for j in range(i + 1, len(body)):
                for for_node in [n for n in ast.walk(body[j]) if isinstance(n, ast.For)]:
                    it = for_node.iter
                    base = it.value if isinstance(it, ast.Subscript) else it
                    if not (isinstance(base, ast.Name) and base.id == container):
                        continue
                    if not isinstance(for_node.target, ast.Name):
                        continue
                    t = for_node.target.id
                    for inner in for_node.body:
                        if not isinstance(inner, ast.If):
                            continue
                        if len(inner.body) != 1 or not isinstance(inner.body[0], ast.Assign):
                            continue
                        a2 = inner.body[0]
                        if len(a2.targets) != 1 or not isinstance(a2.targets[0], ast.Name):
                            continue
                        if a2.targets[0].id != track:
                            continue
                        if not (isinstance(a2.value, ast.Name) and a2.value.id == t):
                            continue
                        test = inner.test
                        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
                            continue
                        l, r = test.left, test.comparators[0]
                        op = test.ops[0]
                        already_ok = (isinstance(l, ast.Name) and isinstance(r, ast.Name) and
                                      ((l.id == t and r.id == track and isinstance(op, ast.Gt)) or
                                       (l.id == track and r.id == t and isinstance(op, ast.Lt))))
                        if already_ok:
                            continue
                        new_text = f"{track} < {t}"
                        results.append(_splice(source, test, new_text))
    return results


# ----------------------------------------------------------------------
# Rule 16: `for n in lst:` whose body indexes `lst[n]`, treating values
# as if they were indices.
# ----------------------------------------------------------------------

def r_for_over_values_should_be_indices(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.iter, ast.Name)
                and isinstance(node.target, ast.Name)):
            continue
        container, tvar = node.iter.id, node.target.id
        found = False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) \
                    and sub.value.id == container:
                sl = _unwrap_index(sub.slice)
                if isinstance(sl, ast.Name) and sl.id == tvar:
                    found = True
        if found:
            new_text = f"range(len({container}))"
            results.append(_splice(source, node.iter, new_text))
    return results


# ----------------------------------------------------------------------
# Rule 17: `elif k == 0: return <full input list>` should return [].
# ----------------------------------------------------------------------

def r_k_zero_return_value(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = [a.arg for a in fn.args.args]
        if not params:
            continue
        first_param = params[0]
        for node in ast.walk(fn):
            if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                    and len(node.test.ops) == 1):
                continue
            op = node.test.ops[0]
            l, r = node.test.left, node.test.comparators[0]
            if (isinstance(op, ast.Eq) and isinstance(l, ast.Name) and l.id == 'k'
                    and isinstance(r, ast.Constant) and r.value == 0):
                if (len(node.body) == 1 and isinstance(node.body[0], ast.Return)
                        and isinstance(node.body[0].value, ast.Name)
                        and node.body[0].value.id == first_param):
                    results.append(_splice(source, node.body[0].value, "[]"))
    return results


# ----------------------------------------------------------------------
# Rule 18: `while lst:` loop collects into an accumulator but never
# removes from `lst`, causing an infinite loop / timeout.
# ----------------------------------------------------------------------

def r_missing_remove_in_while(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    results = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.While) and isinstance(node.test, ast.Name)):
            continue
        container = node.test.id
        has_remove = any(
            isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == 'remove' and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == container
            for sub in ast.walk(node)
        )
        if has_remove:
            continue
        track = None
        for stmt in node.body:
            if isinstance(stmt, ast.For):
                _, tv = _find_track_var(stmt)
                if tv:
                    track = tv
        if not track or not node.body:
            continue
        last_stmt = node.body[-1]
        indent = ' ' * node.body[0].col_offset
        insert_line = f"{indent}{container}.remove({track})\n"
        _, last_end = _line_span(source, last_stmt)
        results.append(source[:last_end] + insert_line + source[last_end:])
    return results


class Fixer:
    def rules(self):
        return [
            Rule(name="append_loop_var_instead_of_tracked",
                 apply=_safe(r_append_loop_var_instead_of_tracked),
                 symptoms=("wrong",)),
            Rule(name="return_wrong_accumulator",
                 apply=_safe(r_return_wrong_accumulator),
                 symptoms=("wrong",)),
            Rule(name="rename_shadowed_function_var",
                 apply=_safe(r_rename_shadowed_function_var),
                 symptoms=("err:UnboundLocalError",)),
            Rule(name="undefined_name_typo",
                 apply=_safe(r_undefined_name_typo),
                 symptoms=("err:NameError",)),
            Rule(name="wrong_assign_target_in_maxloop",
                 apply=_safe(r_wrong_assign_target_in_maxloop),
                 symptoms=("wrong",)),
            Rule(name="append_wrong_arg_after_max",
                 apply=_safe(r_append_wrong_arg_after_max),
                 symptoms=("wrong",)),
            Rule(name="bracket_to_call",
                 apply=_safe(r_bracket_to_call),
                 symptoms=("err:TypeError",)),
            Rule(name="missing_counter_increment",
                 apply=_safe(r_missing_counter_increment),
                 symptoms=("timeout",)),
            Rule(name="missing_return_statement",
                 apply=_safe(r_missing_return_statement),
                 symptoms=("wrong",)),
            Rule(name="k_off_by_one_arith",
                 apply=_safe(r_k_off_by_one_arith),
                 symptoms=("wrong",)),
            Rule(name="le_k_to_lt_k_while",
                 apply=_safe(r_le_k_to_lt_k_while),
                 symptoms=("wrong", "timeout")),
            Rule(name="hardcoded_slice_bound_to_k",
                 apply=_safe(r_hardcoded_slice_bound_to_k),
                 symptoms=("wrong",)),
            Rule(name="swap_remove_before_append",
                 apply=_safe(r_swap_remove_before_append),
                 symptoms=("wrong",)),
            Rule(name="hoist_initializer_out_of_for_loop",
                 apply=_safe(r_hoist_initializer_out_of_for_loop),
                 symptoms=("wrong",)),
            Rule(name="stale_initial_value_in_compare",
                 apply=_safe(r_stale_initial_value_in_compare),
                 symptoms=("wrong",)),
            Rule(name="for_over_values_should_be_indices",
                 apply=_safe(r_for_over_values_should_be_indices),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="k_zero_return_value",
                 apply=_safe(r_k_zero_return_value),
                 symptoms=("wrong",)),
            Rule(name="missing_remove_in_while",
                 apply=_safe(r_missing_remove_in_while),
                 symptoms=("timeout",)),
        ]