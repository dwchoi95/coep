"""
Repair module for the Top-K assignment.

Each Rule below targets one recurring misconception observed in the
submitted solutions.  Rules operate purely on the AST span of the
*original* source text and splice in minimal, local edits -- they never
rebuild the whole function/module.
"""

import ast
import builtins

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


def _node_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _apply_edits(source, edits):
    """edits: list of (start, end, text).  Non-overlapping, any order."""
    edits = sorted(edits, key=lambda x: x[0], reverse=True)
    out = source
    for s, e, t in edits:
        out = out[:s] + t + out[e:]
    return out


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _find_parent_body(tree, target):
    for n in ast.walk(tree):
        body = getattr(n, 'body', None)
        if isinstance(body, list) and target in body:
            return body
        orelse = getattr(n, 'orelse', None)
        if isinstance(orelse, list) and target in orelse:
            return orelse
    return None


def _is_simple_call(stmt, attr):
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr == attr)


def _safe_wrap(fn):
    def wrapper(source):
        try:
            cands = fn(source)
        except Exception:
            return []
        out = []
        for c in cands:
            if isinstance(c, str) and c != source and c not in out:
                out.append(c)
        return out
    return wrapper


_BUILTIN_NAMES = set(dir(builtins)) | {'True', 'False', 'None'}


def _levenshtein(a, b):
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


# ----------------------------------------------------------------------
# Rule 1: swap order of remove(max(x)) / append(max(x))
# ----------------------------------------------------------------------

def rule_swap_remove_append_order(source):
    tree = _parse(source)
    if tree is None:
        return []
    swaps = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if _is_simple_call(a, 'remove') and _is_simple_call(b, 'append'):
                if a.value.args and b.value.args:
                    arg_a = _node_text(source, a.value.args[0])
                    arg_b = _node_text(source, b.value.args[0])
                    if arg_a == arg_b and 'max(' in arg_a:
                        sa, ea = _span(source, a)
                        sb, eb = _span(source, b)
                        swaps.append((sa, ea, sb, eb))
    if not swaps:
        return []
    swaps.sort(key=lambda x: x[0], reverse=True)
    out_src = source
    for sa, ea, sb, eb in swaps:
        text_a = out_src[sa:ea]
        text_b = out_src[sb:eb]
        out_src = out_src[:sa] + text_b + out_src[ea:sb] + text_a + out_src[eb:]
    return [out_src]


# ----------------------------------------------------------------------
# Rule 2: fix mismatched tracker/item names inside the "find max" loop
# ----------------------------------------------------------------------

def rule_fix_tracker_mismatch(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        L = node.target.id
        if_node = None
        for st in node.body:
            if isinstance(st, ast.If):
                if_node = st
                break
        if if_node is None:
            continue
        test = if_node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Gt, ast.Lt))):
            continue
        left, right = test.left, test.comparators[0]
        if not (isinstance(left, ast.Name) and isinstance(right, ast.Name)):
            continue
        assign = None
        for st in if_node.body:
            if (isinstance(st, ast.Assign) and len(st.targets) == 1
                    and isinstance(st.targets[0], ast.Name) and isinstance(st.value, ast.Name)):
                assign = st
                break
        if assign is None:
            continue
        AT, AV = assign.targets[0], assign.value

        track = None
        parent_body = _find_parent_body(tree, node)
        if parent_body is not None:
            idx = parent_body.index(node)
            if idx > 0:
                prev = parent_body[idx - 1]
                if (isinstance(prev, ast.Assign) and len(prev.targets) == 1
                        and isinstance(prev.targets[0], ast.Name)):
                    track = prev.targets[0].id
        if track is None:
            if AT.id != L:
                track = AT.id
            elif right.id != L:
                track = right.id
        if track is None or track == L:
            continue

        if isinstance(test.ops[0], ast.Gt):
            expect_left, expect_right = L, track
        else:
            expect_left, expect_right = track, L

        edits = []
        if left.id != expect_left:
            s, e = _span(source, left)
            edits.append((s, e, expect_left))
        if right.id != expect_right:
            s, e = _span(source, right)
            edits.append((s, e, expect_right))
        if AT.id != track:
            s, e = _span(source, AT)
            edits.append((s, e, track))
        if AV.id != L:
            s, e = _span(source, AV)
            edits.append((s, e, L))
        if edits:
            out.append(_apply_edits(source, edits))
    return out


# ----------------------------------------------------------------------
# Rule 3: fix remove()/append() arguments that use the leftover loop
# variable instead of the running max/min tracker.
# ----------------------------------------------------------------------

def rule_fix_remove_append_arg(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        L = node.target.id
        track = None
        for st in node.body:
            if isinstance(st, ast.If):
                for s2 in st.body:
                    if (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                            and isinstance(s2.targets[0], ast.Name)):
                        track = s2.targets[0].id
        if track is None or track == L:
            continue
        parent_body = _find_parent_body(tree, node)
        if parent_body is None:
            continue
        idx = parent_body.index(node)
        edits = []
        for st in parent_body[idx + 1:]:
            if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                    and isinstance(st.value.func, ast.Attribute)
                    and st.value.func.attr in ('remove', 'append')
                    and len(st.value.args) == 1):
                arg = st.value.args[0]
                if isinstance(arg, ast.Name) and arg.id == L and arg.id != track:
                    s, e = _span(source, arg)
                    edits.append((s, e, track))
        if edits:
            out.append(_apply_edits(source, edits))
    return out


# ----------------------------------------------------------------------
# Rule 4: final `return lst[:k]` should return the accumulator, not the
# original (now emptied) input list.
# ----------------------------------------------------------------------

def rule_fix_return_slice_var(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        list_param = params[0]
        acc = None
        for n in ast.walk(func):
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.List) and not n.value.elts):
                name = n.targets[0].id
                for n2 in ast.walk(func):
                    if (isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute)
                            and n2.func.attr == 'append' and isinstance(n2.func.value, ast.Name)
                            and n2.func.value.id == name):
                        acc = name
                        break
            if acc:
                break
        if acc is None or acc == list_param:
            continue
        for ret in ast.walk(func):
            if (isinstance(ret, ast.Return) and isinstance(ret.value, ast.Subscript)
                    and isinstance(ret.value.value, ast.Name) and ret.value.value.id == list_param):
                out.append(_splice(source, ret.value.value, acc))
    return out


# ----------------------------------------------------------------------
# Rule 5: off-by-one slice bound `[:k+1]` / `[:k-1]` -> `[:k]`
# ----------------------------------------------------------------------

def rule_fix_slice_off_by_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            for bound in (node.slice.upper, node.slice.lower):
                if (isinstance(bound, ast.BinOp) and isinstance(bound.op, (ast.Add, ast.Sub))
                        and isinstance(bound.left, ast.Name) and bound.left.id == 'k'
                        and isinstance(bound.right, ast.Constant) and bound.right.value == 1):
                    s, e = _span(source, bound)
                    edits.append((s, e, 'k'))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


# ----------------------------------------------------------------------
# Rule 6: `<= k` loop bound should be `< k`
# ----------------------------------------------------------------------

def rule_fix_lte_k_bound(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            left, right = node.left, node.comparators[0]
            involves_k = (isinstance(right, ast.Name) and right.id == 'k') or \
                         (isinstance(left, ast.Name) and left.id == 'k')
            if involves_k:
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + ' < ' + source[rs:re_]
                s, e = _span(source, node)
                edits.append((s, e, new_cmp))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


# ----------------------------------------------------------------------
# Rule 7: `while k >= 0` should be `while k > 0`
# ----------------------------------------------------------------------

def rule_fix_gte_zero_bound(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
            left, right = node.left, node.comparators[0]
            if (isinstance(left, ast.Name) and left.id == 'k'
                    and isinstance(right, ast.Constant) and right.value == 0):
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + ' > ' + source[rs:re_]
                s, e = _span(source, node)
                edits.append((s, e, new_cmp))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


# ----------------------------------------------------------------------
# Rule 8: `lst.pop(max(lst))` -> `lst.pop(lst.index(max(lst)))`
# ----------------------------------------------------------------------

def rule_fix_pop_max(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'pop' and len(node.args) == 1):
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'max':
                obj_text = _node_text(source, node.func.value)
                arg_text = _node_text(source, arg)
                new_arg = f"{obj_text}.index({arg_text})"
                out.append(_splice(source, arg, new_arg))
    return out


# ----------------------------------------------------------------------
# Rule 9: a[i] = a[j]; a[j] = a[i]  (self-overwriting swap) -> tuple swap
# ----------------------------------------------------------------------

def rule_fix_bubble_swap(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if not (isinstance(a, ast.Assign) and isinstance(b, ast.Assign)):
                continue
            if len(a.targets) != 1 or len(b.targets) != 1:
                continue
            ta, tb = a.targets[0], b.targets[0]
            va, vb = a.value, b.value
            if not (isinstance(ta, ast.Subscript) and isinstance(va, ast.Subscript)
                    and isinstance(tb, ast.Subscript) and isinstance(vb, ast.Subscript)):
                continue
            if not (isinstance(ta.value, ast.Name) and isinstance(va.value, ast.Name)
                    and isinstance(tb.value, ast.Name) and isinstance(vb.value, ast.Name)):
                continue
            if ta.value.id != va.value.id or tb.value.id != vb.value.id or ta.value.id != tb.value.id:
                continue
            sl_ta, sl_va = ast.dump(ta.slice), ast.dump(va.slice)
            sl_tb, sl_vb = ast.dump(tb.slice), ast.dump(vb.slice)
            if sl_ta == sl_vb and sl_tb == sl_va and sl_ta != sl_tb:
                base_text = _node_text(source, ta.value)
                i_text = _node_text(source, ta.slice)
                j_text = _node_text(source, tb.slice)
                new_text = (f"{base_text}[{i_text}], {base_text}[{j_text}] = "
                            f"{base_text}[{j_text}], {base_text}[{i_text}]")
                s1, e1 = _span(source, a)
                s2, e2 = _span(source, b)
                out.append(source[:s1] + new_text + source[e2:])
    return out


# ----------------------------------------------------------------------
# Rule 10: add an `or k == 0` guard to a top-level empty-list check
# ----------------------------------------------------------------------

def rule_add_k_zero_guard(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if 'k' not in params:
            continue
        for node in func.body:
            if isinstance(node, ast.If):
                test = node.test
                cond_src = _node_text(source, test)
                if 'k' in cond_src:
                    break
                is_target = isinstance(test, ast.Compare) or \
                    (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not))
                if is_target:
                    new_test = f"({cond_src}) or k == 0"
                    out.append(_splice(source, test, new_test))
                break
    return out


# ----------------------------------------------------------------------
# Rule 11: undefined-name typo -> rename to the uniquely close defined name
# ----------------------------------------------------------------------

def rule_fix_undefined_name_typo(source):
    tree = _parse(source)
    if tree is None:
        return []
    all_edits = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = set(a.arg for a in func.args.args)
        defined.add(func.name)
        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                defined.add(n.target.id)
            if isinstance(n, ast.FunctionDef):
                defined.add(n.name)
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                name = n.id
                if name in defined or name in _BUILTIN_NAMES:
                    continue
                best = []
                for d in defined:
                    if d == name:
                        continue
                    if abs(len(d) - len(name)) > 2:
                        continue
                    dist = _levenshtein(name, d)
                    if dist <= 2:
                        best.append((dist, d))
                if not best:
                    continue
                best.sort()
                if len(best) > 1 and best[0][0] == best[1][0]:
                    continue
                s, e = _span(source, n)
                all_edits.append((s, e, best[0][1]))
    if not all_edits:
        return []
    return [_apply_edits(source, all_edits)]


# ----------------------------------------------------------------------
# Rule 12: function builds a result list but never returns it
# ----------------------------------------------------------------------

def rule_fix_missing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != 'top_k':
            continue
        has_return = any(isinstance(st, ast.Return) for st in ast.walk(func))
        if has_return:
            continue
        acc = None
        for n in ast.walk(func):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'append' and isinstance(n.func.value, ast.Name)):
                acc = n.func.value.id
        if acc is None or not func.body:
            continue
        last_stmt = func.body[-1]
        _, e = _span(source, last_stmt)
        indent = ' ' * last_stmt.col_offset
        insertion = f"\n{indent}return {acc}"
        out.append(source[:e] + insertion + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 13: `x.append(y.remove(z))` / `x.append(y.pop(z))` misuse of a
# mutator's (None) return value -> split into two statements.
# ----------------------------------------------------------------------

def rule_fix_append_wraps_mutator(source):
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
                        and inner.func.attr in ('remove', 'pop') and len(inner.args) == 1):
                    outer_list_text = _node_text(source, call.func.value)
                    inner_list_text = _node_text(source, inner.func.value)
                    arg_text = _node_text(source, inner.args[0])
                    indent = ' ' * node.col_offset
                    new_text = (f"{outer_list_text}.append({arg_text})\n"
                                f"{indent}{inner_list_text}.remove({arg_text})")
                    out.append(_splice(source, node, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 14: `range(k-1)` -> `range(k)`
# ----------------------------------------------------------------------

def rule_fix_range_minus_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'range' and len(node.args) == 1):
            arg = node.args[0]
            if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
                    and isinstance(arg.left, ast.Name) and arg.left.id == 'k'
                    and isinstance(arg.right, ast.Constant) and arg.right.value == 1):
                s, e = _span(source, arg)
                edits.append((s, e, 'k'))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


# ----------------------------------------------------------------------
# Rule 15: `obj.append[x]` / `obj.remove[x]` bracket-call typo -> call syntax
# ----------------------------------------------------------------------

def rule_fix_bracket_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    methods = {'append', 'remove', 'pop', 'extend', 'insert'}
    edits = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr in methods):
            sl = node.slice
            if hasattr(ast, 'Index') and isinstance(sl, ast.Index):
                sl = sl.value
            value_text = _node_text(source, node.value)
            arg_text = _node_text(source, sl)
            new_text = f"{value_text}({arg_text})"
            s, e = _span(source, node)
            edits.append((s, e, new_text))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


# ----------------------------------------------------------------------
# Rule 16: a value is appended repeatedly from `max()` but never removed
# from the source list -> insert the missing removal.
# ----------------------------------------------------------------------

def rule_insert_missing_remove(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.While, ast.For)):
            continue
        body = node.body
        append_stmt = None
        list_name = None
        for st in body:
            target_call = None
            if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                    and isinstance(st.value.func, ast.Attribute) and st.value.func.attr == 'append'
                    and len(st.value.args) == 1):
                a0 = st.value.args[0]
                if isinstance(a0, ast.Call) and isinstance(a0.func, ast.Name) and a0.func.id == 'max':
                    target_call = a0
            elif isinstance(st, ast.AugAssign) and isinstance(st.op, ast.Add):
                if isinstance(st.value, ast.List) and len(st.value.elts) == 1:
                    e0 = st.value.elts[0]
                    if isinstance(e0, ast.Call) and isinstance(e0.func, ast.Name) and e0.func.id == 'max':
                        target_call = e0
            if target_call is not None and len(target_call.args) == 1 and isinstance(target_call.args[0], ast.Name):
                append_stmt = st
                list_name = target_call.args[0].id
        if append_stmt is None or list_name is None:
            continue
        has_remove = False
        for n2 in ast.walk(node):
            if (isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute)
                    and n2.func.attr == 'remove' and isinstance(n2.func.value, ast.Name)
                    and n2.func.value.id == list_name):
                has_remove = True
                break
        if has_remove:
            continue
        _, e = _span(source, append_stmt)
        indent = ' ' * append_stmt.col_offset
        insertion = f"\n{indent}{list_name}.remove(max({list_name}))"
        out.append(source[:e] + insertion + source[e:])
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="swap_remove_append_order",
                 apply=_safe_wrap(rule_swap_remove_append_order),
                 symptoms=("wrong",)),
            Rule(name="fix_tracker_name_mismatch",
                 apply=_safe_wrap(rule_fix_tracker_mismatch),
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_remove_append_arg_to_tracker",
                 apply=_safe_wrap(rule_fix_remove_append_arg),
                 symptoms=("wrong",)),
            Rule(name="fix_return_wrong_variable_slice",
                 apply=_safe_wrap(rule_fix_return_slice_var),
                 symptoms=("wrong",)),
            Rule(name="fix_slice_off_by_one",
                 apply=_safe_wrap(rule_fix_slice_off_by_one),
                 symptoms=("wrong",)),
            Rule(name="fix_lte_k_bound",
                 apply=_safe_wrap(rule_fix_lte_k_bound),
                 symptoms=("wrong", "timeout")),
            Rule(name="fix_gte_zero_bound",
                 apply=_safe_wrap(rule_fix_gte_zero_bound),
                 symptoms=("wrong",)),
            Rule(name="fix_pop_max_to_index",
                 apply=_safe_wrap(rule_fix_pop_max),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_bubble_swap_overwrite",
                 apply=_safe_wrap(rule_fix_bubble_swap),
                 symptoms=("wrong",)),
            Rule(name="add_k_zero_guard",
                 apply=_safe_wrap(rule_add_k_zero_guard),
                 symptoms=("wrong",)),
            Rule(name="fix_undefined_name_typo",
                 apply=_safe_wrap(rule_fix_undefined_name_typo),
                 symptoms=("err:NameError",)),
            Rule(name="fix_missing_return_statement",
                 apply=_safe_wrap(rule_fix_missing_return),
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_append_wraps_mutator_call",
                 apply=_safe_wrap(rule_fix_append_wraps_mutator),
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_range_minus_one",
                 apply=_safe_wrap(rule_fix_range_minus_one),
                 symptoms=("wrong",)),
            Rule(name="fix_bracket_call_syntax",
                 apply=_safe_wrap(rule_fix_bracket_call),
                 symptoms=("err:TypeError",)),
            Rule(name="insert_missing_remove_after_max",
                 apply=_safe_wrap(rule_insert_missing_remove),
                 symptoms=("wrong", "timeout")),
        ]