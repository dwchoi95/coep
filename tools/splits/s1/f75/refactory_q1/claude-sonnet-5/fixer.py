"""
Repair module for the "Sequential Search" assignment.

Each Rule below targets one recurring misconception observed across buggy
student submissions. All edits are performed as source-span splices on the
original text (never a full rewrite), so patches stay small and local.
"""

import ast
import re

from src.core.repair import Rule


# --------------------------------------------------------------------------
# AST / source-splicing helpers
# --------------------------------------------------------------------------

def _span(source, node):
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _src(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _splice_span(source, s, e, new_text):
    return source[:s] + new_text + source[e:]


def _indent_of(node):
    return ' ' * node.col_offset


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _is_empty_literal(node):
    return (isinstance(node, ast.Tuple) and len(node.elts) == 0) or \
           (isinstance(node, ast.List) and len(node.elts) == 0)


def _unwrap_index(sl):
    idx_cls = getattr(ast, 'Index', None)
    if idx_cls is not None and isinstance(sl, idx_cls):
        return sl.value
    return sl


def _is_last_or_max(node):
    if isinstance(node, ast.Subscript):
        sl = _unwrap_index(node.slice)
        if isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub) \
           and isinstance(sl.operand, ast.Constant) and sl.operand.value == 1:
            return True
        if isinstance(sl, ast.BinOp) and isinstance(sl.op, ast.Sub):
            left, right = sl.left, sl.right
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) \
               and left.func.id == 'len' and isinstance(right, ast.Constant) \
               and right.value == 1:
                return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'max':
        return True
    return False


def _contains_name(node, name):
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node))


def _loop_vars(node):
    names = []
    t = node.target
    if isinstance(t, ast.Name):
        names.append(t.id)
    elif isinstance(t, ast.Tuple):
        for e in t.elts:
            if isinstance(e, ast.Name):
                names.append(e.id)
    return names


NEG_OP = {ast.Lt: '>=', ast.LtE: '>', ast.Gt: '<=', ast.GtE: '<',
          ast.Eq: '!=', ast.NotEq: '=='}


def _negate_compare_text(source, cmp):
    if not (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1):
        return None
    opstr = NEG_OP.get(type(cmp.ops[0]))
    if opstr is None:
        return None
    left_src = _src(source, cmp.left)
    right_src = _src(source, cmp.comparators[0])
    return f"{left_src} {opstr} {right_src}"


def _safe(fn):
    def wrapper(source):
        try:
            result = fn(source)
        except Exception:
            return []
        out = []
        for r in result:
            if isinstance(r, str) and r != source and r not in out:
                out.append(r)
        return out
    return wrapper


# --------------------------------------------------------------------------
# Rule implementations
# --------------------------------------------------------------------------

def _rule_or_precedence(source):
    """`seq == () or []`  ->  `seq == () or seq == []` (operator precedence slip)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if isinstance(a, ast.Compare) and _is_empty_literal(b):
                left_src = _src(source, a.left)
                lit_src = _src(source, b)
                out.append(_splice(source, b, f"{left_src} == {lit_src}"))
            elif isinstance(b, ast.Compare) and _is_empty_literal(a):
                left_src = _src(source, b.left)
                lit_src = _src(source, a)
                out.append(_splice(source, a, f"{left_src} == {lit_src}"))
    return out


def _rule_expand_single_empty_check(source):
    """`if seq == ():` (only tuple, or only list) -> covers both empty forms."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            t = node.test
            if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
                lit = t.comparators[0]
                if _is_empty_literal(lit):
                    name_src = _src(source, t.left)
                    out.append(_splice(source, t, f"{name_src} == () or {name_src} == []"))
    return out


def _rule_insert_empty_guard(source):
    """Insert a missing `if not seq: return 0` guard before unsafe seq[0]/seq[-1] use."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.body:
            continue
        s0, e0 = _span(source, func)
        ftext = source[s0:e0]
        if re.search(r'seq\s*==\s*\(\)|seq\s*==\s*\[\]|not\s+seq\b|len\(seq\)\s*==\s*0', ftext):
            continue
        if not re.search(r'seq\[\s*0\s*\]|seq\[\s*-1\s*\]', ftext):
            continue
        body = func.body
        idx = 0
        if idx < len(body) and isinstance(body[idx], ast.Expr) \
           and isinstance(getattr(body[idx], 'value', None), ast.Constant) \
           and isinstance(body[idx].value.value, str):
            idx += 1
        if idx >= len(body):
            continue
        target = body[idx]
        indent = _indent_of(target)
        guard = f"if not seq:\n{indent}    return 0\n{indent}"
        s, _e = _span(source, target)
        out.append(_splice_span(source, s, s, guard))
    return out


def _rule_empty_check_assign_to_return(source):
    """`if <emptycheck>: position = 0` -> `return 0` (falls through & crashes otherwise)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_src = _src(source, node.test)
            if 'seq' in test_src and ('()' in test_src or '[]' in test_src):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Assign):
                    assign = node.body[0]
                    if len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name):
                        value_src = _src(source, assign.value)
                        out.append(_splice(source, assign, f"return {value_src}"))
    return out


def _rule_hoist_trailing_return(source):
    """for: (if cond: return i) ; return FALLBACK  ->  move FALLBACK after the loop."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            body = node.body
            for i in range(len(body) - 1):
                cur, nxt = body[i], body[i + 1]
                if isinstance(cur, ast.If) and not cur.orelse and \
                   len(cur.body) == 1 and isinstance(cur.body[0], ast.Return) and \
                   isinstance(nxt, ast.Return) and i + 1 == len(body) - 1:
                    for_s, for_e = _span(source, node)
                    nxt_s, nxt_e = _span(source, nxt)
                    if nxt_e != for_e:
                        continue
                    cur_s, cur_e = _span(source, cur)
                    indent = _indent_of(node)
                    nxt_text = source[nxt_s:nxt_e]
                    new_source = source[:cur_e] + "\n" + indent + nxt_text + source[for_e:]
                    out.append(new_source)
    return out


def _rule_convert_if_else_to_postloop(source):
    """for: if cond: return i  else: return FALLBACK -> move FALLBACK after loop."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            body = node.body
            if body and isinstance(body[-1], ast.If):
                ifnode = body[-1]
                if len(ifnode.body) == 1 and isinstance(ifnode.body[0], ast.Return) and \
                   len(ifnode.orelse) == 1 and isinstance(ifnode.orelse[0], ast.Return):
                    lvars = _loop_vars(node)
                    body_ret, orelse_ret = ifnode.body[0], ifnode.orelse[0]
                    body_has = body_ret.value is not None and any(_contains_name(body_ret.value, v) for v in lvars)
                    orelse_has = orelse_ret.value is not None and any(_contains_name(orelse_ret.value, v) for v in lvars)
                    if body_has and not orelse_has:
                        indent = _indent_of(node)
                        orelse_text = _src(source, orelse_ret)
                        if_s, _if_e = _span(source, ifnode)
                        _bs, bodyret_e = _span(source, body_ret)
                        new_if_text = source[if_s:bodyret_e]
                        for_s, for_e = _span(source, node)
                        new_source = source[:if_s] + new_if_text + "\n" + indent + orelse_text + source[for_e:]
                        out.append(new_source)
    return out


def _rule_collapse_keep_orelse(source):
    """for: if WRONG: return junk  else: return i  -> if NOT WRONG: return i (keep looping)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            body = node.body
            if body and isinstance(body[-1], ast.If):
                ifnode = body[-1]
                if len(ifnode.body) == 1 and isinstance(ifnode.body[0], ast.Return) and \
                   len(ifnode.orelse) == 1 and isinstance(ifnode.orelse[0], ast.Return):
                    lvars = _loop_vars(node)
                    body_ret, orelse_ret = ifnode.body[0], ifnode.orelse[0]
                    body_has = body_ret.value is not None and any(_contains_name(body_ret.value, v) for v in lvars)
                    orelse_has = orelse_ret.value is not None and any(_contains_name(orelse_ret.value, v) for v in lvars)
                    if orelse_has and not body_has:
                        neg = _negate_compare_text(source, ifnode.test)
                        if neg is None:
                            continue
                        indent = _indent_of(ifnode)
                        orelse_text = _src(source, orelse_ret)
                        new_if_text = f"if {neg}:\n{indent}    {orelse_text}"
                        out.append(_splice(source, ifnode, new_if_text))
    return out


def _rule_append_fallback_return(source):
    """Function ends with a loop/if that may fall through without returning -> add return len(seq)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        body = func.body
        last_idx = len(body) - 1
        while last_idx >= 0 and isinstance(body[last_idx], ast.Expr) \
              and isinstance(getattr(body[last_idx], 'value', None), ast.Constant):
            last_idx -= 1
        if last_idx < 0:
            continue
        node = body[last_idx]
        if isinstance(node, (ast.For, ast.While, ast.If)):
            if not any(isinstance(n2, ast.Return) for n2 in ast.walk(node)):
                continue
            indent = _indent_of(node)
            s, e = _span(source, node)
            out.append(source[:s] + source[s:e] + "\n" + indent + "return len(seq)" + source[e:])
    return out


def _rule_bare_return_to_break(source):
    """A bare `return` (no value) inside a loop almost always should be `break`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            for n2 in ast.walk(node):
                if isinstance(n2, ast.Return) and n2.value is None:
                    out.append(_splice(source, n2, "break"))
    return out


def _rule_selfadd_fix(source):
    """`position += position` (never grows past doubling from 0) -> `position += 1`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name) \
               and node.target.id == node.value.id:
                out.append(_splice(source, node.value, "1"))
    return out


def _rule_init_missing_loopvar(source):
    """`for i, e in enumerate(seq): ... ` then `return i` after, without initializing i=0."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        body = func.body
        for i, node in enumerate(body):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) \
               and len(node.target.elts) == 2 and isinstance(node.target.elts[0], ast.Name) \
               and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) \
               and node.iter.func.id == 'enumerate':
                idxname = node.target.elts[0].id
                assigned_before = any(
                    isinstance(n2, ast.Name) and n2.id == idxname and isinstance(n2.ctx, ast.Store)
                    for j in range(i) for n2 in ast.walk(body[j])
                )
                if assigned_before:
                    continue
                if i + 1 < len(body):
                    nxt = body[i + 1]
                    if isinstance(nxt, ast.Return) and isinstance(nxt.value, ast.Name) \
                       and nxt.value.id == idxname:
                        indent = _indent_of(node)
                        s, _e = _span(source, node)
                        out.append(_splice_span(source, s, s, f"{idxname} = 0\n{indent}"))
    return out


def _rule_nested_helper_call(source):
    """A nested recursive `helper` function is defined but its result is never returned."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        body = func.body
        if not body:
            continue
        last = body[-1]
        if isinstance(last, ast.FunctionDef):
            helper_name = last.name
            already = any(
                isinstance(n2, ast.Return) and isinstance(n2.value, ast.Call)
                and isinstance(n2.value.func, ast.Name) and n2.value.func.id == helper_name
                for n2 in ast.walk(func)
            )
            if already:
                continue
            arg_name = '0'
            for stmt in body[:-1]:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                   and isinstance(stmt.targets[0], ast.Name):
                    arg_name = stmt.targets[0].id
            indent = _indent_of(last)
            s, e = _span(source, last)
            out.append(source[:e] + f"\n{indent}return {helper_name}({arg_name})" + source[e:] if False
                        else source[:e] + f"\n{indent}return {helper_name}({arg_name})" + source[e:])
    return out


def _rule_sorted_bare(source):
    """`sorted(seq)` as a bare statement discards the result -> `seq = sorted(seq)`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
           and isinstance(node.value.func, ast.Name) and node.value.func.id == 'sorted' \
           and len(node.value.args) == 1 and isinstance(node.value.args[0], ast.Name):
            n = node.value.args[0].id
            out.append(_splice(source, node, f"{n} = sorted({n})"))
    return out


def _rule_final_expr_return(source):
    """A trailing bare call expression (forgot `return`) -> wrap with `return`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    blocks = []
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            lst = getattr(node, field, None)
            if isinstance(lst, list):
                blocks.append(lst)
    for lst in blocks:
        if not lst:
            continue
        last = lst[-1]
        if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
            out.append(_splice(source, last, "return " + _src(source, last.value)))
    return out


def _rule_lt_to_le(source):
    """Relax a strict `<` comparison to `<=` (misses the equal-element case)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            new_cmp = _src(source, left) + " <= " + _src(source, right)
            out.append(_splice(source, node, new_cmp))
    return out


def _rule_upper_bound_inclusive(source):
    """`x >= seq[-1]` (or `seq[-1] <= x`) -> strict, since equality belongs to an earlier index."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            left, right = node.left, node.comparators[0]
            if isinstance(op, ast.GtE) and isinstance(left, ast.Name) and left.id == 'x' \
               and _is_last_or_max(right):
                new_cmp = _src(source, left) + " > " + _src(source, right)
                out.append(_splice(source, node, new_cmp))
            elif isinstance(op, ast.LtE) and isinstance(right, ast.Name) and right.id == 'x' \
                 and _is_last_or_max(left):
                new_cmp = _src(source, left) + " < " + _src(source, right)
                out.append(_splice(source, node, new_cmp))
    return out


def _rule_for_len_missing_range(source):
    """`for i in len(seq):` -> `for i in range(len(seq)):`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) \
           and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'len':
            if len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Call) \
               and isinstance(node.iter.args[0].func, ast.Name) and node.iter.args[0].func.id == 'range':
                continue  # handled by the swap rule below
            inner_src = _src(source, node.iter)
            out.append(_splice(source, node.iter, f"range({inner_src})"))
    return out


def _rule_for_range_len_swap(source):
    """`for i in len(range(seq)):` -> `for i in range(len(seq)):`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) \
           and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'len' \
           and len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Call) \
           and isinstance(node.iter.args[0].func, ast.Name) and node.iter.args[0].func.id == 'range' \
           and len(node.iter.args[0].args) == 1:
            inner = node.iter.args[0].args[0]
            inner_src = _src(source, inner)
            out.append(_splice(source, node.iter, f"range(len({inner_src}))"))
    return out


def _rule_for_range_missing_len(source):
    """`for i in range(seq):` -> `for i in range(len(seq)):`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        params = {a.arg for a in func.args.args}
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) \
               and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range' \
               and len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Name) \
               and node.iter.args[0].id in params:
                argnode = node.iter.args[0]
                out.append(_splice(source, argnode, f"len({argnode.id})"))
    return out


def _rule_range_len_minus1(source):
    """`range(len(seq)-1)` skips the last index -> `range(len(seq))`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) \
           and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range' \
           and len(node.iter.args) == 1:
            arg = node.iter.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) \
               and isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name) \
               and arg.left.func.id == 'len' and isinstance(arg.right, ast.Constant) \
               and arg.right.value == 1:
                out.append(_splice(source, arg, _src(source, arg.left)))
    return out


def _rule_len_as_container(source):
    """`len[i]` confuses the builtin with the sequence parameter -> `seq[i]`."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        params = [a.arg for a in func.args.args]
        seqname = params[1] if len(params) > 1 else 'seq'
        for node in ast.walk(func):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
               and node.value.id == 'len':
                out.append(_splice(source, node.value, seqname))
    return out


def _rule_add_len0_guard(source):
    """`for i in range(0, len(seq)+1): if x < seq[0]: ...` crashes on empty seq -> add a guard."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) \
           and isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range' \
           and len(node.iter.args) == 2:
            body = node.body
            if body and isinstance(body[0], ast.If) and isinstance(body[0].test, ast.Compare):
                for_s, for_e = _span(source, node)
                fortext = source[for_s:for_e]
                if 'len(seq) == 0' in fortext or 'len(seq)==0' in fortext or 'seq == ()' in fortext:
                    continue
                ifnode = body[0]
                test = ifnode.test
                test_src = _src(source, test)
                indent = _indent_of(ifnode)
                s_if, _ = _span(source, ifnode)
                _ts, e_test = _span(source, test)
                colon_idx = source.find(':', e_test)
                if colon_idx == -1:
                    continue
                new_header = (f"if len(seq) == 0:\n{indent}    return 0\n"
                              f"{indent}elif {test_src}:")
                out.append(source[:s_if] + new_header + source[colon_idx + 1:])
    return out


def _rule_return_param_instead_of_index(source):
    """`if seq[i] < x: return x` is inverted and returns the value instead of the index."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        xname = params[0]
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loopvar = node.target.id
                for stmt in node.body:
                    if isinstance(stmt, ast.If) and len(stmt.body) == 1 \
                       and isinstance(stmt.body[0], ast.Return) \
                       and isinstance(stmt.body[0].value, ast.Name) \
                       and stmt.body[0].value.id == xname:
                        test = stmt.test
                        if isinstance(test, ast.Compare) and len(test.ops) == 1 \
                           and isinstance(test.ops[0], ast.Lt):
                            left_src = _src(source, test.left)
                            right_src = _src(source, test.comparators[0])
                            indent = _indent_of(stmt)
                            new_if = f"if {right_src} <= {left_src}:\n{indent}    return {loopvar}"
                            out.append(_splice(source, stmt, new_if))
    return out


# --------------------------------------------------------------------------
# Fixer
# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="empty_check_or_precedence",
                 apply=_safe(_rule_or_precedence),
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="expand_single_empty_check",
                 apply=_safe(_rule_expand_single_empty_check),
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="insert_missing_empty_guard",
                 apply=_safe(_rule_insert_empty_guard),
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="empty_check_assign_to_return",
                 apply=_safe(_rule_empty_check_assign_to_return),
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="hoist_trailing_return_out_of_loop",
                 apply=_safe(_rule_hoist_trailing_return),
                 symptoms=("wrong",)),
            Rule(name="move_else_fallback_out_of_loop",
                 apply=_safe(_rule_convert_if_else_to_postloop),
                 symptoms=("wrong",)),
            Rule(name="collapse_bad_branch_keep_found_branch",
                 apply=_safe(_rule_collapse_keep_orelse),
                 symptoms=("wrong",)),
            Rule(name="append_fallback_return_after_loop",
                 apply=_safe(_rule_append_fallback_return),
                 symptoms=("wrong",)),
            Rule(name="bare_return_to_break",
                 apply=_safe(_rule_bare_return_to_break),
                 symptoms=("wrong", "timeout")),
            Rule(name="selfadd_augassign_fix",
                 apply=_safe(_rule_selfadd_fix),
                 symptoms=("timeout", "wrong")),
            Rule(name="init_missing_loopvar_enumerate",
                 apply=_safe(_rule_init_missing_loopvar),
                 symptoms=("err:IndexError", "err:NameError", "err:UnboundLocalError")),
            Rule(name="nested_helper_missing_call",
                 apply=_safe(_rule_nested_helper_call),
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="sorted_bare_call_assign",
                 apply=_safe(_rule_sorted_bare),
                 symptoms=("wrong",)),
            Rule(name="final_expr_missing_return",
                 apply=_safe(_rule_final_expr_return),
                 symptoms=("wrong",)),
            Rule(name="strict_lt_should_be_lte",
                 apply=_safe(_rule_lt_to_le),
                 symptoms=("wrong",)),
            Rule(name="upper_bound_should_be_strict",
                 apply=_safe(_rule_upper_bound_inclusive),
                 symptoms=("wrong",)),
            Rule(name="for_iter_len_missing_range",
                 apply=_safe(_rule_for_len_missing_range),
                 symptoms=("err:TypeError",)),
            Rule(name="for_iter_range_len_swap",
                 apply=_safe(_rule_for_range_len_swap),
                 symptoms=("err:TypeError",)),
            Rule(name="for_range_missing_len",
                 apply=_safe(_rule_for_range_missing_len),
                 symptoms=("err:TypeError",)),
            Rule(name="range_len_minus1_off_by_one",
                 apply=_safe(_rule_range_len_minus1),
                 symptoms=("wrong",)),
            Rule(name="len_used_as_container",
                 apply=_safe(_rule_len_as_container),
                 symptoms=("err:TypeError",)),
            Rule(name="add_len0_guard_before_plus1_range",
                 apply=_safe(_rule_add_len0_guard),
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="return_param_instead_of_index",
                 apply=_safe(_rule_return_param_instead_of_index),
                 symptoms=("wrong",)),
        ]