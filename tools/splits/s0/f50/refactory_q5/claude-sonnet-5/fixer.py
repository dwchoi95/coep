"""
Repair module for the Top-K assignment.

Each Rule below targets one recurring misconception observed in buggy
student submissions and expresses it as a small, local AST-located,
source-span-spliced edit.
"""

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


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _get_slice_expr(sl):
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _target_names(t):
    names = set()
    if isinstance(t, ast.Name):
        names.add(t.id)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for e in t.elts:
            names |= _target_names(e)
    elif isinstance(t, ast.Starred):
        names |= _target_names(t.value)
    return names


def _collect_defined_names(func):
    names = set()
    args = func.args
    for a in list(getattr(args, "posonlyargs", [])) + list(args.args) + list(args.kwonlyargs):
        names.add(a.arg)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                names |= _target_names(t)
        elif isinstance(n, ast.AugAssign):
            names |= _target_names(n.target)
        elif isinstance(n, ast.AnnAssign):
            names |= _target_names(n.target)
        elif isinstance(n, (ast.For, getattr(ast, "AsyncFor", ast.For))):
            names |= _target_names(n.target)
        elif isinstance(n, ast.FunctionDef):
            names.add(n.name)
        elif isinstance(n, ast.withitem):
            if n.optional_vars:
                names |= _target_names(n.optional_vars)
        elif isinstance(n, ast.ExceptHandler):
            if n.name:
                names.add(n.name)
        elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in n.generators:
                names |= _target_names(gen.target)
    return names


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


def _best_candidate(x, candidates):
    cands = [c for c in candidates if c and c != x]
    subs = [c for c in cands if c in x or x in c]
    if len(subs) == 1:
        return subs[0]
    if len(subs) > 1:
        subs.sort(key=lambda c: _lev(x, c))
        if len(subs) >= 2 and _lev(x, subs[0]) == _lev(x, subs[1]):
            return None
        return subs[0]
    scored = [(c, _lev(x, c)) for c in cands]
    scored = [p for p in scored if p[1] <= 2]
    if not scored:
        return None
    scored.sort(key=lambda p: p[1])
    if len(scored) >= 2 and scored[0][1] == scored[1][1]:
        return None
    return scored[0][0]


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapped


# ----------------------------------------------------------------------
# Rule 1: undefined-name typo correction (NameError-style misconception)
# ----------------------------------------------------------------------

def _rule_undefined_name_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    try:
        import builtins as _b
        builtin_names = set(dir(_b))
    except Exception:
        builtin_names = set()
    module_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        local_defined = _collect_defined_names(func)
        full_defined = local_defined | builtin_names | module_funcs | {func.name}
        loads = {}
        for n2 in ast.walk(func):
            if isinstance(n2, ast.Name) and isinstance(n2.ctx, ast.Load):
                if n2.id not in full_defined:
                    loads.setdefault(n2.id, []).append(n2)
        if not loads:
            continue
        edits = []
        for name, nodes in loads.items():
            cand = _best_candidate(name, local_defined)
            if cand is None:
                continue
            for n2 in nodes:
                s, e = _span(source, n2)
                edits.append((s, e, cand))
        if not edits:
            continue
        edits.sort(key=lambda t: t[0], reverse=True)
        new_source = source
        for s, e, cand in edits:
            new_source = new_source[:s] + cand + new_source[e:]
        if new_source != source:
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 2: append target undefined -> should be the list measured by while
# ----------------------------------------------------------------------

def _rule_fix_undefined_append_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(func):
            if not isinstance(node, ast.While):
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Lt)
                    and isinstance(test.left, ast.Call)
                    and isinstance(test.left.func, ast.Name)
                    and test.left.func.id == 'len'
                    and len(test.left.args) == 1
                    and isinstance(test.left.args[0], ast.Name)):
                continue
            loopvar = test.left.args[0].id
            for n2 in ast.walk(node):
                if (isinstance(n2, ast.Expr) and isinstance(n2.value, ast.Call)
                        and isinstance(n2.value.func, ast.Attribute)
                        and n2.value.func.attr == 'append'
                        and isinstance(n2.value.func.value, ast.Name)):
                    obj = n2.value.func.value
                    if obj.id != loopvar:
                        s, e = _span(source, obj)
                        out.append(source[:s] + loopvar + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 3: wrong variable updated inside running-max tracker pattern
# ----------------------------------------------------------------------

def _rule_wrong_tracker_update(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)
                and isinstance(test.comparators[0], ast.Name)):
            continue
        tracker = test.comparators[0].id
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Assign):
            continue
        assign = node.body[0]
        if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
            continue
        target = assign.targets[0]
        if not (isinstance(assign.value, ast.expr) and ast.dump(assign.value) == ast.dump(test.left)):
            continue
        if target.id != tracker:
            s, e = _span(source, target)
            out.append(source[:s] + tracker + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 4: using the loop variable after the loop instead of the tracker
# ----------------------------------------------------------------------

def _rule_use_loopvar_instead_of_tracker(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parent_map = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        V = node.target.id
        M = None
        for stmt in node.body:
            if not (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare)
                    and len(stmt.test.ops) == 1 and isinstance(stmt.test.ops[0], ast.Gt)):
                continue
            left, right = stmt.test.left, stmt.test.comparators[0]
            if not (isinstance(left, ast.Name) and left.id == V and isinstance(right, ast.Name)):
                continue
            if len(stmt.body) != 1 or not isinstance(stmt.body[0], ast.Assign):
                continue
            a = stmt.body[0]
            if len(a.targets) != 1 or not isinstance(a.targets[0], ast.Name):
                continue
            if a.targets[0].id == right.id and isinstance(a.value, ast.Name) and a.value.id == V:
                M = right.id
        if M is None:
            continue
        parent = parent_map.get(node)
        if parent is None:
            continue
        body_list = None
        for field in ('body', 'orelse', 'finalbody'):
            lst_ = getattr(parent, field, None)
            if isinstance(lst_, list) and node in lst_:
                body_list = lst_
                break
        if body_list is None:
            continue
        idx = body_list.index(node)
        following = body_list[idx + 1:]
        if not following:
            continue
        targets = []
        for stmt in following:
            for n2 in ast.walk(stmt):
                if isinstance(n2, ast.Name) and n2.id == V and isinstance(n2.ctx, ast.Load):
                    targets.append(n2)
        if not targets:
            continue
        spans = sorted((_span(source, n2) for n2 in targets), reverse=True)
        new_source = source
        for s, e in spans:
            new_source = new_source[:s] + M + new_source[e:]
        if new_source != source:
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 5: split "X.append(Y.remove(Z))" into two statements
# ----------------------------------------------------------------------

def _rule_split_append_remove(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        call = node.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == 'append' and len(call.args) == 1):
            continue
        inner = call.args[0]
        if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == 'remove' and len(inner.args) == 1):
            continue
        a_s, a_e = _span(source, call.func.value)
        z_s, z_e = _span(source, inner.args[0])
        b_s, b_e = _span(source, inner.func.value)
        indent = ' ' * node.col_offset
        z_text = source[z_s:z_e]
        new_stmt = (source[a_s:a_e] + ".append(" + z_text + ")\n" +
                    indent + source[b_s:b_e] + ".remove(" + z_text + ")")
        out.append(_splice(source, node, new_stmt))
    return out


# ----------------------------------------------------------------------
# Rule 6: "for i in range(k): X.append(max(lst))" missing removal
# ----------------------------------------------------------------------

def _rule_missing_remove_after_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        body = node.body
        if len(body) != 1 or not isinstance(body[0], ast.Expr):
            continue
        call = body[0].value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == 'append' and len(call.args) == 1):
            continue
        arg = call.args[0]
        if not (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                and arg.func.id == 'max' and len(arg.args) == 1
                and isinstance(arg.args[0], ast.Name)):
            continue
        list_name = arg.args[0].id
        _, e = _span(source, body[0])
        indent = ' ' * body[0].col_offset
        new_source = source[:e] + "\n" + indent + list_name + ".remove(max(" + list_name + "))" + source[e:]
        out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 7: `.append[x]` / `.remove[x]` -> `.append(x)` / `.remove(x)`
# ----------------------------------------------------------------------

def _rule_bracket_to_paren_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    targets = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr in ('append', 'remove', 'pop')):
            sl = _get_slice_expr(node.slice)
            if isinstance(sl, ast.expr):
                targets.append((node, node.value, sl))
    if not targets:
        return []
    spans = []
    for node, attr_node, sl in targets:
        s, e = _span(source, node)
        a_s, a_e = _span(source, attr_node)
        sl_s, sl_e = _span(source, sl)
        spans.append((s, e, a_s, a_e, sl_s, sl_e))
    spans.sort(key=lambda x: x[0], reverse=True)
    new_source = source
    for s, e, a_s, a_e, sl_s, sl_e in spans:
        new_text = source[a_s:a_e] + "(" + source[sl_s:sl_e] + ")"
        new_source = new_source[:s] + new_text + new_source[e:]
    return [new_source] if new_source != source else []


# ----------------------------------------------------------------------
# Rule 8: off-by-one in slice bound ([:k+1], [:5] -> [:k])
# ----------------------------------------------------------------------

def _rule_off_by_one_slice(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        param_names = {a.arg for a in func.args.args}
        if 'k' not in param_names:
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.Subscript):
                continue
            sl = _get_slice_expr(node.slice)
            if not (isinstance(sl, ast.Slice) and sl.lower is None and sl.step is None and sl.upper is not None):
                continue
            up = sl.upper
            if isinstance(up, ast.Name) and up.id == 'k':
                continue
            bad = False
            if isinstance(up, ast.BinOp) and isinstance(up.op, (ast.Add, ast.Sub)):
                l, r = up.left, up.right
                if (isinstance(l, ast.Name) and l.id == 'k'
                        and isinstance(r, ast.Constant) and isinstance(r.value, int) and r.value != 0):
                    bad = True
                elif (isinstance(r, ast.Name) and r.id == 'k'
                        and isinstance(l, ast.Constant) and isinstance(l.value, int) and l.value != 0):
                    bad = True
            elif isinstance(up, ast.Constant) and isinstance(up.value, int):
                bad = True
            if bad:
                s, e = _span(source, up)
                out.append(source[:s] + "k" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 9: off-by-one while bound (len(x) <= k -> len(x) < k)
# ----------------------------------------------------------------------

def _rule_off_by_one_while_lte(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.LtE)
                and isinstance(test.left, ast.Call) and isinstance(test.left.func, ast.Name)
                and test.left.func.id == 'len'):
            continue
        right = test.comparators[0]
        left_s, left_e = _span(source, test.left)
        right_s, right_e = _span(source, right)
        new_cmp = source[left_s:left_e] + " < " + source[right_s:right_e]
        out.append(_splice(source, test, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule 10: a return statement trapped inside a loop body (premature exit)
# ----------------------------------------------------------------------

def _rule_move_return_out_of_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.While, ast.For)):
            continue
        body = node.body
        if len(body) < 2 or not isinstance(body[-1], ast.Return):
            continue
        ret = body[-1]
        rs, re_ = _span(source, ret)
        line_start = source.rfind('\n', 0, rs) + 1
        if source[line_start:rs].strip() != "":
            continue
        new_indent = ' ' * node.col_offset
        new_source = source[:line_start] + new_indent + source[rs:]
        if new_source != source:
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 11: `for i in range(len(lst)): if i == X` -> `if lst[i] == X`
# ----------------------------------------------------------------------

def _rule_index_vs_value_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        itr = node.iter
        if not (isinstance(itr, ast.Call) and isinstance(itr.func, ast.Name) and itr.func.id == 'range'
                and len(itr.args) == 1 and isinstance(itr.args[0], ast.Call)
                and isinstance(itr.args[0].func, ast.Name) and itr.args[0].func.id == 'len'
                and len(itr.args[0].args) == 1 and isinstance(itr.args[0].args[0], ast.Name)):
            continue
        list_name = itr.args[0].args[0].id
        ivar = node.target.id
        for cmp in ast.walk(node):
            if (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1
                    and isinstance(cmp.left, ast.Name) and cmp.left.id == ivar):
                s, e = _span(source, cmp.left)
                out.append(source[:s] + f"{list_name}[{ivar}]" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 12: A = B; B = A pseudo-swap -> tuple swap
# ----------------------------------------------------------------------

def _rule_swap_without_temp(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            if not (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)):
                continue
            if len(s1.targets) != 1 or len(s2.targets) != 1:
                continue
            t1, v1 = s1.targets[0], s1.value
            t2, v2 = s2.targets[0], s2.value
            if (ast.dump(t1) == ast.dump(v2) and ast.dump(t2) == ast.dump(v1)
                    and ast.dump(t1) != ast.dump(t2)):
                t1s, t1e = _span(source, t1)
                v1s, v1e = _span(source, v1)
                new_stmt = f"{source[t1s:t1e]}, {source[v1s:v1e]} = {source[v1s:v1e]}, {source[t1s:t1e]}"
                s_start, _ = _span(source, s1)
                _, s_end = _span(source, s2)
                out.append(source[:s_start] + new_stmt + source[s_end:])
    return out


# ----------------------------------------------------------------------
# Rule 13: trailing "tracker = seq[0]" reset placed after use instead of before
# ----------------------------------------------------------------------

def _rule_move_reset_assignment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.While) and len(node.body) >= 2):
            continue
        last = node.body[-1]
        if not (isinstance(last, ast.Assign) and len(last.targets) == 1
                and isinstance(last.targets[0], ast.Name) and isinstance(last.value, ast.Subscript)):
            continue
        sl = _get_slice_expr(last.value.slice)
        is_zero = isinstance(sl, ast.Constant) and sl.value == 0
        if not (is_zero and isinstance(last.value.value, ast.Name)):
            continue
        first_stmt = node.body[0]
        if ast.dump(first_stmt) == ast.dump(last):
            continue
        s, e = _span(source, last)
        stmt_text = source[s:e]
        line_start = source.rfind('\n', 0, s) + 1
        line_end = source.find('\n', e)
        line_end = line_end + 1 if line_end != -1 else len(source)
        removed = source[:line_start] + source[line_end:]
        fs, _ = _span(source, first_stmt)
        first_line_start = source.rfind('\n', 0, fs) + 1
        indent = source[first_line_start:fs]
        insertion_text = indent + stmt_text + "\n"
        if first_line_start > len(removed):
            continue
        new_source = removed[:first_line_start] + insertion_text + removed[first_line_start:]
        if new_source != source:
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 14: inner-loop search missing break; counter misplaced inside it
# ----------------------------------------------------------------------

def _rule_move_counter_add_break(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.left, ast.Name)):
            continue
        counter_name = test.left.id
        if not node.body or not isinstance(node.body[-1], ast.For):
            continue
        for_node = node.body[-1]
        if not for_node.body or not isinstance(for_node.body[-1], ast.If):
            continue
        if_node = for_node.body[-1]
        if not if_node.body or if_node.orelse:
            continue
        last_stmt = if_node.body[-1]
        if not (isinstance(last_stmt, ast.AugAssign) and isinstance(last_stmt.target, ast.Name)
                and last_stmt.target.id == counter_name):
            continue
        if any(isinstance(s, ast.Break) for s in if_node.body):
            continue
        rs, re_ = _span(source, last_stmt)
        old_text = source[rs:re_]
        indent_for = ' ' * for_node.col_offset
        for_s, for_e = _span(source, for_node)
        if for_e < re_:
            continue
        new_source = (source[:rs] + "break" + source[re_:for_e] +
                      "\n" + indent_for + old_text + source[for_e:])
        if new_source != source:
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 15: self-shadowing recursive call `X = X(...)` where X names a
# module-level function -> rename the bound variable.
# ----------------------------------------------------------------------

def _rule_self_shadow_rename(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    module_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for stmt in ast.walk(func):
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            tgt = stmt.targets[0]
            val = stmt.value
            if not (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                    and val.func.id == tgt.id and val.func.id in module_funcs):
                continue
            fname = tgt.id
            used = _collect_defined_names(func)
            new_name = fname + "_result"
            while new_name in used:
                new_name += "_"
            edits = []
            s_tgt, e_tgt = _span(source, tgt)
            edits.append((s_tgt, e_tgt))
            for n2 in ast.walk(func):
                if (isinstance(n2, ast.Name) and n2.id == fname
                        and isinstance(n2.ctx, ast.Load) and n2 is not val.func
                        and (n2.lineno, n2.col_offset) > (stmt.lineno, stmt.col_offset)):
                    edits.append(_span(source, n2))
            spans = sorted(set(edits), reverse=True)
            new_source = source
            for s, e in spans:
                new_source = new_source[:s] + new_name + new_source[e:]
            if new_source != source:
                out.append(new_source)
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="undefined_name_typo",
                 apply=_safe(_rule_undefined_name_typo),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_append_target_matches_while_var",
                 apply=_safe(_rule_fix_undefined_append_target),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="wrong_tracker_update_target",
                 apply=_safe(_rule_wrong_tracker_update),
                 symptoms=("wrong",)),
            Rule(name="use_loopvar_instead_of_tracker_after_loop",
                 apply=_safe(_rule_use_loopvar_instead_of_tracker),
                 symptoms=("wrong",)),
            Rule(name="split_append_remove",
                 apply=_safe(_rule_split_append_remove),
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="missing_remove_after_append",
                 apply=_safe(_rule_missing_remove_after_append),
                 symptoms=("wrong",)),
            Rule(name="bracket_to_paren_call",
                 apply=_safe(_rule_bracket_to_paren_call),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="off_by_one_slice_bound",
                 apply=_safe(_rule_off_by_one_slice),
                 symptoms=("wrong",)),
            Rule(name="off_by_one_while_lte",
                 apply=_safe(_rule_off_by_one_while_lte),
                 symptoms=("wrong", "err:ValueError")),
            Rule(name="move_return_out_of_loop",
                 apply=_safe(_rule_move_return_out_of_loop),
                 symptoms=("wrong",)),
            Rule(name="index_vs_value_compare",
                 apply=_safe(_rule_index_vs_value_compare),
                 symptoms=("wrong",)),
            Rule(name="swap_without_temp",
                 apply=_safe(_rule_swap_without_temp),
                 symptoms=("wrong",)),
            Rule(name="move_reset_assignment_into_loop",
                 apply=_safe(_rule_move_reset_assignment),
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="move_counter_increment_add_break",
                 apply=_safe(_rule_move_counter_add_break),
                 symptoms=("wrong", "timeout", "err:IndexError")),
            Rule(name="self_shadowing_recursive_call_rename",
                 apply=_safe(_rule_self_shadow_rename),
                 symptoms=("err:UnboundLocalError", "wrong")),
        ]