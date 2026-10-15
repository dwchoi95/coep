import ast

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


def _mentions(node, name):
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node))


def _lev(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[lb]


def _iter_extremum_patterns(tree):
    found = []
    for for_node in ast.walk(tree):
        if not isinstance(for_node, ast.For) or not isinstance(for_node.target, ast.Name):
            continue
        for_var = for_node.target.id
        for node in ast.walk(for_node):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                op = node.test.ops[0]
                if not isinstance(op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                    continue
                assign = None
                for st in node.body:
                    if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                        assign = st
                        break
                if assign is None:
                    continue
                current_var = assign.targets[0].id
                if current_var == for_var:
                    continue
                if not _mentions(assign.value, for_var):
                    continue
                left, right = node.test.left, node.test.comparators[0]
                lf, rf = _mentions(left, for_var), _mentions(right, for_var)
                lc, rc = _mentions(left, current_var), _mentions(right, current_var)
                if lf and rc and not rf:
                    side = 'left'
                elif rf and lc and not lf:
                    side = 'right'
                else:
                    continue
                found.append((for_node, node, current_var, for_var, side))
    return found


def _fix_accumulator_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        decl = None
        for st in func.body:
            if (isinstance(st, ast.Assign) and len(st.targets) == 1
                    and isinstance(st.targets[0], ast.Name)
                    and isinstance(st.value, ast.List) and len(st.value.elts) == 0):
                decl = st.targets[0].id
                break
        if decl is None:
            continue
        assigned_names = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    for nm in ast.walk(t):
                        if isinstance(nm, ast.Name):
                            assigned_names.add(nm.id)
            elif isinstance(n, ast.For):
                for nm in ast.walk(n.target):
                    if isinstance(nm, ast.Name):
                        assigned_names.add(nm.id)
            elif isinstance(n, ast.arg):
                assigned_names.add(n.arg)
        patches = []
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'append':
                if (isinstance(n.func.value, ast.Name) and n.func.value.id != decl
                        and n.func.value.id not in assigned_names):
                    patches.append(n.func.value)
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name):
                if n.value.id != decl and n.value.id not in assigned_names:
                    patches.append(n.value)
        if not patches:
            continue
        try:
            patches.sort(key=lambda p: _span(source, p)[0], reverse=True)
            new_source = source
            for node in patches:
                new_source = _splice(new_source, node, decl)
            out.append(new_source)
        except Exception:
            pass
    return out


def _add_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        acc = None
        for st in func.body:
            if (isinstance(st, ast.Assign) and len(st.targets) == 1
                    and isinstance(st.targets[0], ast.Name)
                    and isinstance(st.value, ast.List) and len(st.value.elts) == 0):
                acc = st.targets[0].id
                break
        if acc is None or not func.body:
            continue
        try:
            indent = " " * func.body[0].col_offset
            lines = source.splitlines(keepends=True)
            last_stmt = func.body[-1]
            insert_idx = last_stmt.end_lineno
            new_line = f"{indent}return {acc}\n"
            new_lines = lines[:insert_idx] + [new_line] + lines[insert_idx:]
            out.append("".join(new_lines))
        except Exception:
            pass
    return out


def _print_to_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
            f = last.value.func
            if isinstance(f, ast.Name) and f.id == 'print' and len(last.value.args) >= 1:
                try:
                    arg = last.value.args[0]
                    s_, e_ = _span(source, arg)
                    arg_text = source[s_:e_]
                    out.append(_splice(source, last, f"return {arg_text}"))
                except Exception:
                    pass
    return out


def _dedent_trailing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.While) and node.body:
                last = node.body[-1]
                if isinstance(last, ast.Return):
                    try:
                        lines = source.splitlines(keepends=True)
                        ret_idx = last.lineno - 1
                        while_idx = node.lineno - 1
                        while_line = lines[while_idx]
                        outer_indent = while_line[:len(while_line) - len(while_line.lstrip())]
                        ret_line = lines[ret_idx]
                        stripped = ret_line.strip()
                        new_return_line = outer_indent + stripped + "\n"
                        new_lines = lines[:ret_idx] + lines[ret_idx + 1:]
                        insert_idx = ret_idx
                        new_lines = new_lines[:insert_idx] + [new_return_line] + new_lines[insert_idx:]
                        out.append("".join(new_lines))
                    except Exception:
                        pass
    return out


def _fix_extremum_direction(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    invert = {ast.Lt: ('>',), ast.Gt: ('<',), ast.LtE: ('>=',), ast.GtE: ('<=',)}
    for for_node, if_node, current_var, for_var, side in _iter_extremum_patterns(tree):
        op = if_node.test.ops[0]
        wanted = (ast.Gt, ast.GtE) if side == 'left' else (ast.Lt, ast.LtE)
        if isinstance(op, wanted):
            continue
        if type(op) not in invert:
            continue
        sym = invert[type(op)][0]
        try:
            left, right = if_node.test.left, if_node.test.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + f" {sym} " + source[rs:re_]
            out.append(_splice(source, if_node.test, new_cmp))
        except Exception:
            pass
    return out


def _add_age_subscript(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for for_node, if_node, current_var, for_var, side in _iter_extremum_patterns(tree):
        left, right = if_node.test.left, if_node.test.comparators[0]
        patches = []
        for operand in (left, right):
            if isinstance(operand, ast.Name) and operand.id in (for_var, current_var):
                patches.append(operand)
        if not patches:
            continue
        try:
            patches_sorted = sorted(patches, key=lambda n: _span(source, n)[0], reverse=True)
            new_source = source
            for n in patches_sorted:
                s_, e_ = _span(new_source, n)
                new_source = new_source[:s_] + f"{n.id}[1]" + new_source[e_:]
            out.append(new_source)
        except Exception:
            pass
    return out


def _fix_minus_as_assign(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Sub):
            l, r = node.value.left, node.value.right
            if isinstance(l, ast.Name) and isinstance(r, ast.Name):
                try:
                    out.append(_splice(source, node, f"{l.id} = {r.id}"))
                except Exception:
                    pass
    return out


def _max_without_key(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ('max', 'min'):
            if len(node.args) == 1 and not node.keywords and isinstance(node.args[0], ast.Name):
                try:
                    arg = node.args[0]
                    s_, e_ = _span(source, arg)
                    arg_text = source[s_:e_]
                    new_call = f"{node.func.id}({arg_text}, key=lambda x: x[1])"
                    out.append(_splice(source, node, new_call))
                except Exception:
                    pass
    return out


def _swap_call_args_builtin(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id not in ('max', 'min'):
            if (len(node.args) == 1 and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in ('max', 'min') and not node.keywords):
                try:
                    new_call = f"{node.args[0].id}({node.func.id})"
                    out.append(_splice(source, node, new_call))
                except Exception:
                    pass
    return out


def _is_tuple_swap(stmt):
    return (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Tuple) and isinstance(stmt.value, ast.Tuple)
            and len(stmt.targets[0].elts) == 2 and len(stmt.value.elts) == 2)


def _bubble_sort_flip(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    invert = {ast.Lt: '>', ast.Gt: '<', ast.LtE: '>=', ast.GtE: '<='}
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            op = node.test.ops[0]
            if type(op) not in invert:
                continue
            if not any(_is_tuple_swap(s) for s in node.body):
                continue
            try:
                left, right = node.test.left, node.test.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                sym = invert[type(op)]
                new_cmp = source[ls:le] + f" {sym} " + source[rs:re_]
                out.append(_splice(source, node.test, new_cmp))
            except Exception:
                pass
    return out


def _typo_nearest_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    builtins_whitelist = {
        'len', 'range', 'print', 'max', 'min', 'list', 'tuple', 'int', 'str',
        'sorted', 'enumerate', 'True', 'False', 'None', 'set', 'dict', 'abs', 'sum',
        'float', 'bool',
    }
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        assigned = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    for nm in ast.walk(t):
                        if isinstance(nm, ast.Name):
                            assigned.add(nm.id)
            elif isinstance(n, ast.AugAssign):
                if isinstance(n.target, ast.Name):
                    assigned.add(n.target.id)
            elif isinstance(n, ast.For):
                for nm in ast.walk(n.target):
                    if isinstance(nm, ast.Name):
                        assigned.add(nm.id)
        for a in func.args.args:
            assigned.add(a.arg)
        undefined = {}
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id in assigned or n.id in builtins_whitelist or n.id == func.name:
                    continue
                undefined.setdefault(n.id, []).append(n)
        for bad_id, nodes in undefined.items():
            best, best_d = None, None
            for cand in assigned:
                d = _lev(bad_id, cand)
                if best_d is None or d < best_d:
                    best_d, best = d, cand
            if best is None or best_d == 0:
                continue
            threshold = 2 if max(len(bad_id), len(best)) >= 4 else 1
            if best_d > threshold:
                continue
            try:
                nodes_sorted = sorted(nodes, key=lambda n: _span(source, n)[0], reverse=True)
                new_source = source
                for n in nodes_sorted:
                    new_source = _splice(new_source, n, best)
                out.append(new_source)
            except Exception:
                pass
    return out


def _reindent_dedented_loop_calls(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        body = func.body
        for idx, stmt in enumerate(body):
            if not isinstance(stmt, ast.While) or not stmt.body:
                continue
            j = idx + 1
            calls = []
            while j < len(body):
                s = body[j]
                if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
                    f = s.value.func
                    if isinstance(f, ast.Attribute) and f.attr in ('remove', 'append') and isinstance(f.value, ast.Name):
                        calls.append(s)
                        j += 1
                        continue
                break
            if not calls:
                continue
            try:
                lines = source.splitlines(keepends=True)
                last_inner = stmt.body[-1]
                inner_line = lines[last_inner.lineno - 1]
                inner_indent = inner_line[:len(inner_line) - len(inner_line.lstrip())]
                new_lines_text = []
                for c in calls:
                    cline = lines[c.lineno - 1]
                    new_lines_text.append(inner_indent + cline.strip() + "\n")
                start_remove = calls[0].lineno - 1
                end_remove = calls[-1].lineno - 1
                insert_after_idx = last_inner.end_lineno - 1
                if start_remove <= insert_after_idx:
                    continue
                new_body_lines = lines[:start_remove] + lines[end_remove + 1:]
                result_lines = (new_body_lines[:insert_after_idx + 1]
                                + new_lines_text
                                + new_body_lines[insert_after_idx + 1:])
                out.append("".join(result_lines))
            except Exception:
                pass
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="accumulator_name_mismatch",
                 apply=_fix_accumulator_mismatch,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="add_missing_return",
                 apply=_add_missing_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="print_instead_of_return",
                 apply=_print_to_return,
                 symptoms=("wrong",)),
            Rule(name="dedent_trailing_return_from_loop",
                 apply=_dedent_trailing_return,
                 symptoms=("wrong",)),
            Rule(name="extremum_selection_direction_flip",
                 apply=_fix_extremum_direction,
                 symptoms=("wrong",)),
            Rule(name="add_missing_age_subscript",
                 apply=_add_age_subscript,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="minus_typo_should_be_assign",
                 apply=_fix_minus_as_assign,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="max_min_missing_key",
                 apply=_max_without_key,
                 symptoms=("wrong",)),
            Rule(name="swapped_builtin_call_args",
                 apply=_swap_call_args_builtin,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="bubble_sort_direction_flip",
                 apply=_bubble_sort_flip,
                 symptoms=("wrong",)),
            Rule(name="typo_nearest_name_fix",
                 apply=_typo_nearest_name,
                 symptoms=("err:NameError",)),
            Rule(name="reindent_dedented_loop_calls",
                 apply=_reindent_dedented_loop_calls,
                 symptoms=("timeout", "wrong")),
        ]