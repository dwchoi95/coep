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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _dedupe(source, out):
    seen = []
    for cand in out:
        if cand != source and cand not in seen:
            seen.append(cand)
    return seen


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


# ---------------------------------------------------------------------------
# Rule: comparison threshold should be an exact "==1" (or equivalent "!=1")
def _rule_threshold_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []

    def handle_if(ifnode, false_val_node):
        test = ifnode.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and len(test.comparators) == 1):
            return
        right = test.comparators[0]
        op = test.ops[0]
        if not isinstance(right, ast.Constant) or isinstance(right.value, bool):
            return
        if not isinstance(right.value, int) or right.value not in (1, 2):
            return
        if not isinstance(op, (ast.Gt, ast.GtE, ast.LtE, ast.Lt)):
            return
        if len(ifnode.body) != 1 or not isinstance(ifnode.body[0], ast.Return):
            return
        a_node = ifnode.body[0].value
        if not (isinstance(a_node, ast.Constant) and isinstance(a_node.value, bool)):
            return
        if not (isinstance(false_val_node, ast.Constant)
                and isinstance(false_val_node.value, bool)):
            return
        if a_node.value == false_val_node.value:
            return
        new_op = '==' if a_node.value is True else '!='
        ls, le = _span(source, test.left)
        left_text = source[ls:le]
        new_test = f"{left_text} {new_op} 1"
        s, e = _span(source, test)
        out.append(source[:s] + new_test + source[e:])

    for node in ast.walk(tree):
        if isinstance(node, ast.If) and len(node.orelse) == 1 \
                and isinstance(node.orelse[0], ast.Return):
            handle_if(node, node.orelse[0].value)

    def scan_list(stmts):
        for i, s in enumerate(stmts):
            if isinstance(s, ast.If) and not s.orelse and i + 1 < len(stmts):
                nxt = stmts[i + 1]
                if isinstance(nxt, ast.Return):
                    handle_if(s, nxt.value)

    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            val = getattr(node, field, None)
            if isinstance(val, list):
                scan_list(val)

    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: Name used but never bound anywhere in the function -> parameter typo
def _bound_names(func):
    names = {a.arg for a in func.args.args}
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
    return names


def _rule_undefined_to_param(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    builtin_names = set(dir(builtins))
    toplevel = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    out = []
    for func in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        bound = _bound_names(func) | builtin_names | toplevel | {'True', 'False', 'None'}
        params = [a.arg for a in func.args.args if a.arg != 'possible_birthdays']
        if not params:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) \
                    and node.id not in bound:
                best = None
                for p in params:
                    if p in node.id or node.id in p:
                        best = p
                        break
                if best is None:
                    best = params[0]
                if best != node.id:
                    out.append(_splice(source, node, best))
    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: "x = x + 1" / "x += 1" where x is never initialized -> rename to the
# real counter variable (initialized to 0 and compared against 1 later)
def _rule_self_assign_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        params = {a.arg for a in func.args.args}
        counters = []
        for stmt in func.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                    and isinstance(stmt.targets[0], ast.Name) \
                    and isinstance(stmt.value, ast.Constant) and stmt.value.value == 0:
                counters.append(stmt.targets[0].id)
        if not counters:
            continue
        for node in ast.walk(func):
            tgt_name = None
            is_assign = False
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name):
                val = node.value
                if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add) \
                        and isinstance(val.left, ast.Name) \
                        and val.left.id == node.targets[0].id:
                    tgt_name = node.targets[0].id
                    is_assign = True
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) \
                    and isinstance(node.op, ast.Add):
                tgt_name = node.target.id
            if tgt_name is None or tgt_name in params or tgt_name in counters:
                continue
            best = None
            for c in counters:
                if c.rstrip('s') == tgt_name.rstrip('s') or c in tgt_name or tgt_name in c:
                    best = c
                    break
            if best is None:
                best = counters[0]
            if is_assign:
                out.append(_splice(source, node, f"{best} = {best} + 1"))
            else:
                out.append(_splice(source, node.target, best))
    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: counter re-initialised with the same name as the function parameter,
# shadowing it (e.g. `month = 0` inside unique_month(month, ...))
def _rule_counter_shadow(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        params = {a.arg for a in func.args.args}
        for stmt in func.body:
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            name = stmt.targets[0].id
            if name not in params:
                continue
            if not (isinstance(stmt.value, ast.Constant) and stmt.value.value == 0):
                continue
            newname = name + 'count'
            keep_ids = set()
            for node in ast.walk(func):
                if isinstance(node, ast.Compare):
                    left = node.left
                    for comp in node.comparators:
                        if isinstance(comp, ast.Name) and comp.id == name \
                                and isinstance(left, ast.Subscript):
                            keep_ids.add(id(comp))
                        if isinstance(left, ast.Name) and left.id == name \
                                and isinstance(comp, ast.Subscript):
                            keep_ids.add(id(left))
            targets = [n for n in ast.walk(func)
                       if isinstance(n, ast.Name) and n.id == name and id(n) not in keep_ids]
            if len(targets) < 2:
                continue
            targets_sorted = sorted(targets, key=lambda n: _span(source, n)[0], reverse=True)
            new_source = source
            for n in targets_sorted:
                s, e = _span(source, n)
                new_source = new_source[:s] + newname + new_source[e:]
            out.append(new_source)
    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: call to an undefined function name that is a near-typo of a defined one
def _rule_call_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fid = node.func.id
            if fid in defined or not fid.startswith('unique_'):
                continue
            for d in defined:
                if not d.startswith('unique_'):
                    continue
                diff = sum(1 for a, b in zip(d, fid) if a != b) + abs(len(d) - len(fid))
                if diff <= 3:
                    out.append(_splice(source, node.func, d))
                    break
    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: contains_unique_day calls unique_day without filtering by month first
def _rule_missing_month_filter(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == 'contains_unique_day']:
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        monthparam = params[0]
        for node in ast.walk(func):
            if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
                continue
            loopvar = node.target.id
            for stmt in node.body:
                if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Call) \
                        and isinstance(stmt.test.func, ast.Name) \
                        and 'unique' in stmt.test.func.id:
                    ts, te = _span(source, stmt.test)
                    test_text = source[ts:te]
                    new_test = f"{monthparam} == {loopvar}[0] and {test_text}"
                    out.append(_splice(source, stmt.test, new_test))
    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: function ends with a hard-coded `return True` even though it tracks
# a flag/counter that should be returned instead
def _rule_return_true_to_flag(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.body:
            continue
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue
        flag = None
        for stmt in func.body[:-1]:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                    and isinstance(stmt.targets[0], ast.Name) \
                    and isinstance(stmt.value, ast.Constant) \
                    and stmt.value.value in (False, 0):
                flag = stmt.targets[0].id
                break
        if flag is None:
            continue
        out.append(_splice(source, last.value, flag))
    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: function returns a bare name that is only ever assigned conditionally,
# never initialised unconditionally -> insert `name = False` at the top
def _rule_uninitialized_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.body:
            continue
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Name)):
            continue
        name = last.value.id
        if name in {a.arg for a in func.args.args}:
            continue
        top_assigned = any(
            isinstance(stmt, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in stmt.targets)
            for stmt in func.body[:-1])
        if top_assigned:
            continue
        nested_assigned = any(
            isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets)
            for node in ast.walk(func))
        if not nested_assigned:
            continue
        first = func.body[0]
        s, _e = _span(source, first)
        indent = ' ' * first.col_offset
        out.append(source[:s] + f"{name} = False\n{indent}" + source[s:])
    return _dedupe(source, out)


# ---------------------------------------------------------------------------
# Rule: off-by-one `i <= len(seq)` used as a loop/index guard
def _rule_le_len_offbyone(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and isinstance(node.ops[0], ast.LtE):
            right = node.comparators[0]
            if isinstance(right, ast.Call) and isinstance(right.func, ast.Name) \
                    and right.func.id == 'len':
                ls, le = _span(source, node.left)
                rs, re_ = _span(source, right)
                new_cmp = f"{source[ls:le]} < {source[rs:re_]}"
                out.append(_splice(source, node, new_cmp))
    return _dedupe(source, out)


def _wrap(fn):
    def apply(source):
        try:
            return fn(source)
        except Exception:
            return []
    return apply


class Fixer:
    def rules(self):
        return [
            Rule(name="threshold_to_eq1", apply=_wrap(_rule_threshold_fix),
                 symptoms=("wrong",)),
            Rule(name="undefined_name_to_param", apply=_wrap(_rule_undefined_to_param),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="self_assign_undefined_counter", apply=_wrap(_rule_self_assign_fix),
                 symptoms=("err:UnboundLocalError", "err:NameError", "wrong")),
            Rule(name="counter_shadows_param", apply=_wrap(_rule_counter_shadow),
                 symptoms=("wrong",)),
            Rule(name="call_typo_fix", apply=_wrap(_rule_call_typo),
                 symptoms=("err:NameError",)),
            Rule(name="missing_month_filter", apply=_wrap(_rule_missing_month_filter),
                 symptoms=("wrong",)),
            Rule(name="return_true_to_flag", apply=_wrap(_rule_return_true_to_flag),
                 symptoms=("wrong",)),
            Rule(name="uninitialized_return_var", apply=_wrap(_rule_uninitialized_return),
                 symptoms=("err:NameError", "err:UnboundLocalError")),
            Rule(name="le_len_offbyone", apply=_wrap(_rule_le_len_offbyone),
                 symptoms=("err:IndexError", "timeout")),
        ]