import ast
import builtins

from src.core.repair import Rule


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


def _apply_edits(source, edits):
    edits = sorted(edits, key=lambda e: e[0], reverse=True)
    s = source
    for start, end, repl in edits:
        s = s[:start] + repl + s[end:]
    return s


def _iter_bodies(tree):
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            if hasattr(node, field):
                body = getattr(node, field)
                if isinstance(body, list):
                    yield body


def _safe(fn):
    def wrapped(source):
        try:
            result = fn(source)
        except Exception:
            return []
        out = []
        seen = set()
        for r in result:
            if r and r != source and r not in seen:
                seen.add(r)
                out.append(r)
        return out
    return wrapped


def _find_selection_compare(for_node):
    if not isinstance(for_node.target, ast.Name):
        return None
    loop_var = for_node.target.id
    for stmt in for_node.body:
        if isinstance(stmt, ast.If) and len(stmt.body) == 1:
            assign = stmt.body[0]
            if isinstance(assign, ast.Assign) and len(assign.targets) == 1 \
               and isinstance(assign.targets[0], ast.Name):
                tname = assign.targets[0].id
                test = stmt.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1 \
                   and isinstance(test.ops[0], (ast.Lt, ast.Gt)):
                    names = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
                    if loop_var in names and tname in names:
                        return test
    return None


def _selection_info(for_node):
    test = _find_selection_compare(for_node)
    if test is None:
        return None
    loop_var = for_node.target.id
    names = [n.id for n in ast.walk(test) if isinstance(n, ast.Name)]
    tracker = next((nm for nm in names if nm != loop_var), None)
    if tracker is None:
        return None
    return loop_var, tracker, test


# ---------------------------------------------------------------------------
# Rule: wrong variable appended/removed after a max-selection for-loop
# ---------------------------------------------------------------------------
@_safe
def fix_wrong_var_after_selection(source):
    tree = ast.parse(source)
    out = []
    for body in _iter_bodies(tree):
        for i, stmt in enumerate(body):
            if not isinstance(stmt, ast.For):
                continue
            info = _selection_info(stmt)
            if not info:
                continue
            loop_var, tracker, _ = info
            if loop_var == tracker:
                continue
            edits = []
            for j in range(i + 1, len(body)):
                s2 = body[j]
                if isinstance(s2, ast.Expr) and isinstance(s2.value, ast.Call):
                    call = s2.value
                    if isinstance(call.func, ast.Attribute) and call.func.attr in ('remove', 'append') \
                       and len(call.args) == 1:
                        arg = call.args[0]
                        if isinstance(arg, ast.Name) and arg.id == loop_var:
                            edits.append(arg)
            if edits:
                spans = [_span(source, n) for n in edits]
                edit_list = [(s, e, tracker) for s, e in spans]
                out.append(_apply_edits(source, edit_list))
    return out


# ---------------------------------------------------------------------------
# Rule: flip min/max selection direction (Lt <-> Gt) for a max-selection loop
# ---------------------------------------------------------------------------
@_safe
def fix_selection_direction(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            info = _selection_info(node)
            if not info:
                continue
            _, _, test = info
            left_s, left_e = _span(source, test.left)
            right_s, right_e = _span(source, test.comparators[0])
            new_op = '>' if isinstance(test.ops[0], ast.Lt) else '<'
            new_text = source[left_s:left_e] + f' {new_op} ' + source[right_s:right_e]
            out.append(_splice(source, test, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: misplaced remove/append statements nested inside a selection for-loop
# (they should run once per outer iteration, after the for-loop finishes)
# ---------------------------------------------------------------------------
@_safe
def fix_misplaced_mutation_in_loop(source):
    tree = ast.parse(source)
    out = []
    for body in _iter_bodies(tree):
        for stmt in body:
            if not isinstance(stmt, ast.For):
                continue
            info = _selection_info(stmt)
            if not info:
                continue
            misplaced = []

            def collect(b):
                for s in b:
                    if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
                        c = s.value
                        if isinstance(c.func, ast.Attribute) and c.func.attr in ('remove', 'append') \
                           and len(c.args) == 1 and isinstance(c.args[0], ast.Name):
                            misplaced.append(s)
                    elif isinstance(s, ast.If):
                        collect(s.body)

            collect(stmt.body)
            if not misplaced:
                continue

            for_s, for_e = _span(source, stmt)
            indent = ' ' * stmt.col_offset
            texts = [source[_span(source, m)[0]:_span(source, m)[1]] for m in misplaced]
            insertion = ''.join('\n' + indent + t for t in texts)

            edits = [(for_e, for_e, insertion)]
            for m in misplaced:
                ms, me = _span(source, m)
                line_start = source.rfind('\n', 0, ms) + 1
                edits.append((line_start, me, ''))
            out.append(_apply_edits(source, edits))
    return out


# ---------------------------------------------------------------------------
# Rule: slice bound not using k correctly (e.g. [:k-1], [0:3])
# ---------------------------------------------------------------------------
@_safe
def fix_slice_bound(source):
    tree = ast.parse(source)
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if 'k' not in [a.arg for a in fn.args.args]:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                upper = node.slice.upper
                if upper is None:
                    continue
                replace = None
                if isinstance(upper, ast.BinOp) and isinstance(upper.op, ast.Sub) \
                   and isinstance(upper.left, ast.Name) and upper.left.id == 'k' \
                   and isinstance(upper.right, ast.Constant):
                    replace = 'k'
                elif isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                    replace = 'k'
                if replace:
                    out.append(_splice(source, upper, replace))
    return out


# ---------------------------------------------------------------------------
# Rule: for i in range(k-1) -> range(k)
# ---------------------------------------------------------------------------
@_safe
def fix_range_k_minus_one(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'range' \
           and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) \
               and isinstance(arg.left, ast.Name) and arg.left.id == 'k' \
               and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                out.append(_splice(source, arg, 'k'))
    return out


# ---------------------------------------------------------------------------
# Rule: while len(x) <= k  ->  while len(x) < k
# ---------------------------------------------------------------------------
@_safe
def fix_while_len_lte_k(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            test = node.test
            if isinstance(test.ops[0], ast.LtE):
                left = test.left
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == 'len':
                    le = _span(source, left)[1]
                    rs = _span(source, test.comparators[0])[0]
                    between = source[le:rs]
                    if '<=' in between:
                        new_between = between.replace('<=', '< ', 1)
                        out.append(source[:le] + new_between + source[rs:])
    return out


# ---------------------------------------------------------------------------
# Rule: frozen length comparison (x = len(lst); while x >= x - k) -> use len(lst)
# ---------------------------------------------------------------------------
@_safe
def fix_frozen_length_compare(source):
    tree = ast.parse(source)
    assigns = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == 'len' \
               and len(val.args) == 1 and isinstance(val.args[0], ast.Name):
                assigns[node.targets[0].id] = val.args[0].id
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            test = node.test
            left = test.left
            right = test.comparators[0]
            if isinstance(left, ast.Name) and left.id in assigns:
                if isinstance(right, ast.BinOp) and isinstance(right.op, ast.Sub) \
                   and isinstance(right.left, ast.Name) and right.left.id == left.id:
                    lst_name = assigns[left.id]
                    new_left = f'len({lst_name})'
                    out.append(_splice(source, left, new_left))
    return out


# ---------------------------------------------------------------------------
# Rule: missing return at end of function that builds a list via .append(
# ---------------------------------------------------------------------------
@_safe
def fix_missing_return(source):
    tree = ast.parse(source)
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(fn))
        if has_return:
            continue
        target_var = None
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'append':
                if isinstance(n.func.value, ast.Name):
                    target_var = n.func.value.id
        if target_var is None or not fn.body:
            continue
        last_stmt = fn.body[-1]
        _, e = _span(source, last_stmt)
        indent = ' ' * last_stmt.col_offset
        insertion = '\n' + indent + f'return {target_var}'
        out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule: lst.pop(max(lst))  ->  lst.pop(lst.index(max(lst)))
# ---------------------------------------------------------------------------
@_safe
def fix_pop_max_needs_index(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'pop' \
           and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'max' \
               and len(arg.args) == 1 and isinstance(arg.args[0], ast.Name):
                lst_name = arg.args[0].id
                new_arg = f'{lst_name}.index(max({lst_name}))'
                out.append(_splice(source, arg, new_arg))
    return out


# ---------------------------------------------------------------------------
# Rule: X.append(Y.remove(Z)) -> X.append(Z); Y.remove(Z)
# ---------------------------------------------------------------------------
@_safe
def fix_append_wraps_remove(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == 'append' and len(call.args) == 1:
                inner = call.args[0]
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) \
                   and inner.func.attr == 'remove' and len(inner.args) == 1:
                    a_s, a_e = _span(source, call.func.value)
                    r_s, r_e = _span(source, inner.func.value)
                    arg_s, arg_e = _span(source, inner.args[0])
                    indent = ' ' * node.col_offset
                    new_text = (source[a_s:a_e] + '.append(' + source[arg_s:arg_e] + ')'
                                + '\n' + indent +
                                source[r_s:r_e] + '.remove(' + source[arg_s:arg_e] + ')')
                    out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: missing lst.remove(max(lst)) after appending max(lst) in a loop
# ---------------------------------------------------------------------------
@_safe
def fix_missing_remove_after_max_use(source):
    tree = ast.parse(source)
    out = []
    for loop in ast.walk(tree):
        if not isinstance(loop, (ast.For, ast.While)):
            continue
        for stmt in loop.body:
            lst_name = None
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == 'append' and len(call.args) == 1:
                    arg = call.args[0]
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'max' \
                       and len(arg.args) == 1 and isinstance(arg.args[0], ast.Name):
                        lst_name = arg.args[0].id
            elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
                val = stmt.value
                if isinstance(val, ast.List) and len(val.elts) == 1:
                    elt = val.elts[0]
                    if isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name) and elt.func.id == 'max' \
                       and len(elt.args) == 1 and isinstance(elt.args[0], ast.Name):
                        lst_name = elt.args[0].id
            if lst_name:
                has_remove = any(
                    isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'remove'
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == lst_name
                    for n in ast.walk(loop)
                )
                if not has_remove:
                    _, e = _span(source, stmt)
                    indent = ' ' * stmt.col_offset
                    insertion = '\n' + indent + f'{lst_name}.remove(max({lst_name}))'
                    out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule: appending the whole list right after computing its max into a var
# ---------------------------------------------------------------------------
@_safe
def fix_append_arg_mismatch_after_max(source):
    tree = ast.parse(source)
    out = []
    for body in _iter_bodies(tree):
        for i, stmt in enumerate(body):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                var = stmt.targets[0].id
                val = stmt.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == 'max' \
                   and len(val.args) == 1 and isinstance(val.args[0], ast.Name):
                    lst_name = val.args[0].id
                    if i + 1 < len(body):
                        nxt = body[i + 1]
                        if isinstance(nxt, ast.Expr) and isinstance(nxt.value, ast.Call):
                            call = nxt.value
                            if isinstance(call.func, ast.Attribute) and call.func.attr == 'append' \
                               and len(call.args) == 1:
                                arg = call.args[0]
                                if isinstance(arg, ast.Name) and arg.id == lst_name and lst_name != var:
                                    out.append(_splice(source, arg, var))
    return out


# ---------------------------------------------------------------------------
# Rule: X[idx] accessed via subscript brackets instead of calling a list
# method (e.g. r.append[biggest] -> r.append(biggest))
# ---------------------------------------------------------------------------
@_safe
def fix_subscript_as_call(source):
    tree = ast.parse(source)
    out = []
    _IndexType = getattr(ast, 'Index', None)
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
           and node.value.attr in ('append', 'remove', 'pop', 'insert', 'extend'):
            sl = node.slice
            if _IndexType is not None and isinstance(sl, _IndexType):
                sl = sl.value
            if isinstance(sl, ast.Slice):
                continue
            vs, ve = _span(source, node.value)
            ss, se = _span(source, sl)
            new_text = source[vs:ve] + '(' + source[ss:se] + ')'
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: comparing a range(len(lst)) index variable directly to a value
# instead of indexing the list (i == max(lst) -> lst[i] == max(lst))
# ---------------------------------------------------------------------------
@_safe
def fix_index_value_confusion(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name) \
           and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) \
           and node.iter.func.id == 'range' and len(node.iter.args) == 1:
            rng_arg = node.iter.args[0]
            if isinstance(rng_arg, ast.Call) and isinstance(rng_arg.func, ast.Name) \
               and rng_arg.func.id == 'len' and len(rng_arg.args) == 1 \
               and isinstance(rng_arg.args[0], ast.Name):
                idx_var = node.target.id
                lst_name = rng_arg.args[0].id
                for n in ast.walk(node):
                    if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Eq):
                        if isinstance(n.left, ast.Name) and n.left.id == idx_var:
                            out.append(_splice(source, n.left, f'{lst_name}[{idx_var}]'))
    return out


# ---------------------------------------------------------------------------
# Rule: local variable shadows a module-level function it is assigned from
# (sort = sort(lst) -> UnboundLocalError)
# ---------------------------------------------------------------------------
@_safe
def fix_shadowed_function_var(source):
    tree = ast.parse(source)
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                tname = node.targets[0].id
                val = node.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == tname \
                   and tname in func_names and tname != fn.name:
                    new_name = tname + '_result'
                    call_func_ids = set()
                    for n in ast.walk(fn):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == tname:
                            call_func_ids.add(id(n.func))
                    edits = []
                    for n in ast.walk(fn):
                        if isinstance(n, ast.Name) and n.id == tname and id(n) not in call_func_ids:
                            s, e = _span(source, n)
                            edits.append((s, e, new_name))
                    if edits:
                        out.append(_apply_edits(source, edits))
    return out


# ---------------------------------------------------------------------------
# Rule: generic typo-identifier unification (NameError-style misconceptions)
# ---------------------------------------------------------------------------
def _levenshtein(a, b):
    if a == b:
        return 0
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[n]


@_safe
def fix_typo_identifier(source):
    tree = ast.parse(source)
    builtin_names = set(dir(builtins))
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        assigned = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
            elif isinstance(n, ast.AugAssign):
                if isinstance(n.target, ast.Name):
                    assigned.add(n.target.id)
            elif isinstance(n, ast.For):
                if isinstance(n.target, ast.Name):
                    assigned.add(n.target.id)
            elif isinstance(n, ast.comprehension):
                if isinstance(n.target, ast.Name):
                    assigned.add(n.target.id)
        for a in fn.args.args:
            assigned.add(a.arg)

        name_nodes = [n for n in ast.walk(fn) if isinstance(n, ast.Name)]

        undefined_ids = set()
        for n in name_nodes:
            if isinstance(n.ctx, ast.Load) and n.id not in assigned \
               and n.id not in builtin_names and n.id not in func_names:
                undefined_ids.add(n.id)
        if not undefined_ids:
            continue

        for u in undefined_ids:
            best = None
            for a_id in assigned:
                if a_id == u or a_id in func_names:
                    continue
                if len(a_id) < 3 or len(u) < 3:
                    continue
                if _levenshtein(a_id, u) <= 2:
                    best = a_id
                    break
            if best is None:
                continue
            count_a = sum(1 for n in name_nodes if n.id == best)
            count_u = sum(1 for n in name_nodes if n.id == u)
            if count_a >= count_u:
                loser, winner = u, best
            else:
                loser, winner = best, u
            edits = [(_span(source, n)[0], _span(source, n)[1], winner)
                     for n in name_nodes if n.id == loser]
            if edits:
                out.append(_apply_edits(source, edits))
    return out


# ---------------------------------------------------------------------------
# Rule: missing k<=0 guard when the loop relies on a break-after-append
# ---------------------------------------------------------------------------
@_safe
def fix_missing_k_zero_guard(source):
    tree = ast.parse(source)
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or 'k' not in [a.arg for a in fn.args.args]:
            continue
        has_guard = False
        for n in ast.walk(fn):
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                left, right = n.left, n.comparators[0]
                if isinstance(left, ast.Name) and left.id == 'k' and isinstance(right, ast.Constant) \
                   and right.value == 0:
                    has_guard = True
                if isinstance(right, ast.Name) and right.id == 'k' and isinstance(left, ast.Constant) \
                   and left.value == 0:
                    has_guard = True
        has_break_pattern = any(
            isinstance(n, ast.If) and any(isinstance(s, ast.Break) for s in n.body)
            for n in ast.walk(fn)
        )
        if has_guard or not has_break_pattern or not fn.body:
            continue
        first_stmt = fn.body[0]
        s, _ = _span(source, first_stmt)
        indent = ' ' * first_stmt.col_offset
        insertion = f'if k <= 0:\n{indent}    return []\n{indent}'
        out.append(source[:s] + insertion + source[s:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="wrong_var_in_append_remove_after_selection",
                 apply=fix_wrong_var_after_selection,
                 symptoms=("wrong",)),
            Rule(name="flip_selection_min_max_direction",
                 apply=fix_selection_direction,
                 symptoms=("wrong",)),
            Rule(name="misplaced_mutation_inside_selection_loop",
                 apply=fix_misplaced_mutation_in_loop,
                 symptoms=("wrong",)),
            Rule(name="slice_bound_not_k",
                 apply=fix_slice_bound,
                 symptoms=("wrong",)),
            Rule(name="range_k_minus_one",
                 apply=fix_range_k_minus_one,
                 symptoms=("wrong",)),
            Rule(name="while_len_lte_k_off_by_one",
                 apply=fix_while_len_lte_k,
                 symptoms=("wrong", "timeout")),
            Rule(name="frozen_length_compare",
                 apply=fix_frozen_length_compare,
                 symptoms=("wrong", "timeout")),
            Rule(name="missing_return_after_build",
                 apply=fix_missing_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="pop_max_needs_index",
                 apply=fix_pop_max_needs_index,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="append_wraps_remove_call",
                 apply=fix_append_wraps_remove,
                 symptoms=("wrong",)),
            Rule(name="missing_remove_after_max_append",
                 apply=fix_missing_remove_after_max_use,
                 symptoms=("wrong", "timeout")),
            Rule(name="append_whole_list_instead_of_max",
                 apply=fix_append_arg_mismatch_after_max,
                 symptoms=("wrong",)),
            Rule(name="subscript_used_instead_of_call",
                 apply=fix_subscript_as_call,
                 symptoms=("err:TypeError",)),
            Rule(name="index_value_confusion",
                 apply=fix_index_value_confusion,
                 symptoms=("wrong",)),
            Rule(name="shadowed_function_name_variable",
                 apply=fix_shadowed_function_var,
                 symptoms=("err:UnboundLocalError",)),
            Rule(name="typo_identifier_unification",
                 apply=fix_typo_identifier,
                 symptoms=("err:NameError",)),
            Rule(name="missing_k_zero_guard",
                 apply=fix_missing_k_zero_guard,
                 symptoms=("wrong",)),
        ]