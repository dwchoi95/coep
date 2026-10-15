"""
Repair module for the Sequential Search assignment.

Each rule performs a single, small, structurally-targeted edit on the
submitted source (located via the AST, spliced into the original text).
Rules are meant to be composed by the harness's search procedure; none of
them attempts to produce a whole "canonical" solution on its own.
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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _is_zero_const(node):
    return isinstance(node, ast.Constant) and node.value == 0


def _is_emptiness_test(node):
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        op = node.ops[0]
        right = node.comparators[0]
        left = node.left
        if isinstance(op, ast.Eq) and isinstance(right, (ast.List, ast.Tuple)) and len(right.elts) == 0:
            return True
        if isinstance(op, ast.Eq) and isinstance(left, (ast.List, ast.Tuple)) and len(left.elts) == 0:
            return True
        if isinstance(op, ast.Eq) and isinstance(left, ast.Call) and isinstance(left.func, ast.Name) \
           and left.func.id == 'len' and _is_zero_const(right):
            return True
        if isinstance(op, ast.Lt) and isinstance(left, ast.Call) and isinstance(left.func, ast.Name) \
           and left.func.id == 'len' and isinstance(right, ast.Constant) and right.value == 1:
            return True
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return any(_is_emptiness_test(v) for v in node.values)
    return False


# ----------------------------------------------------------------------
# Rule 1: `seq == () or []` style operator-precedence slip
# ----------------------------------------------------------------------

def _fix_or_precedence(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            compares = [v for v in node.values if isinstance(v, ast.Compare)]
            bares = [v for v in node.values if isinstance(v, (ast.List, ast.Tuple))]
            if compares and bares:
                ls, le = _span(source, compares[0].left)
                left_text = source[ls:le]
                for bare in bares:
                    bs, be = _span(source, bare)
                    new_text = f"{left_text} == {source[bs:be]}"
                    out.append(_splice(source, bare, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 2: emptiness test not placed first in an `or` chain (IndexError)
# ----------------------------------------------------------------------

def _reorder_emptiness_first(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            idxs = [i for i, v in enumerate(node.values) if _is_emptiness_test(v)]
            if idxs and idxs[0] != 0:
                texts = []
                for v in node.values:
                    s, e = _span(source, v)
                    texts.append(source[s:e])
                order = idxs + [i for i in range(len(node.values)) if i not in idxs]
                new_text = " or ".join(texts[i] for i in order)
                out.append(_splice(source, node, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 3: body of an emptiness-guard does not actually return 0
# ----------------------------------------------------------------------

def _fix_empty_branch(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_emptiness_test(node.test):
            body = node.body
            if len(body) != 1:
                continue
            stmt = body[0]
            if isinstance(stmt, ast.Pass):
                out.append(_splice(source, stmt, "return 0"))
            elif isinstance(stmt, ast.Return):
                if not _is_zero_const(stmt.value):
                    out.append(_splice(source, stmt, "return 0"))
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                    and isinstance(stmt.targets[0], ast.Name):
                out.append(_splice(source, stmt, "return 0"))
    return out


# ----------------------------------------------------------------------
# Rule 4: no emptiness guard at all, but seq is indexed -> IndexError risk
# ----------------------------------------------------------------------

def _add_empty_guard(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or fn.name != 'search':
            continue
        body = fn.body
        idx0 = 0
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            idx0 = 1
        if idx0 >= len(body):
            continue
        first = body[idx0]
        if isinstance(first, ast.If) and _is_emptiness_test(first.test):
            continue
        uses_index = False
        for node in ast.walk(fn):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'seq':
                uses_index = True
                break
        if not uses_index:
            continue
        indent = ' ' * first.col_offset
        insertion = f"if len(seq) == 0:\n{indent}    return 0\n{indent}"
        s, _e = _span(source, first)
        out.append(source[:s] + insertion + source[s:])
    return out


# ----------------------------------------------------------------------
# Rule 5: `for ...: if cond: return i  else: return len(seq)` misplaced else
# ----------------------------------------------------------------------

def _move_else_after_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and len(node.body) == 1 and isinstance(node.body[0], ast.If):
            ifnode = node.body[0]
            if not ifnode.orelse:
                continue
            for_s, for_e = _span(source, node)
            if_s, _if_e = _span(source, ifnode)
            if_body_end = _span(source, ifnode.body[-1])[1]
            orelse_start = _span(source, ifnode.orelse[0])[0]
            orelse_end = _span(source, ifnode.orelse[-1])[1]
            orelse_text = source[orelse_start:orelse_end]
            for_indent = ' ' * node.col_offset
            new_for_part = source[for_s:if_s] + source[if_s:if_body_end]
            replacement = new_for_part + "\n" + for_indent + orelse_text
            out.append(source[:for_s] + replacement + source[for_e:])
    return out


# ----------------------------------------------------------------------
# Rule 6: trailing for-loop with no fallback `return len(seq)` afterwards
# ----------------------------------------------------------------------

def _append_fallback_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        if not body:
            continue
        last = body[-1]
        if isinstance(last, ast.For):
            has_return = any(isinstance(n, ast.Return) for n in ast.walk(last))
            if has_return:
                indent = ' ' * last.col_offset
                s, e = _span(source, last)
                out.append(source[:e] + "\n" + indent + "return len(seq)" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 7: `x >= seq[len(seq)-1]` / `x >= seq[-1]` should be strict `>`
# ----------------------------------------------------------------------

def _ge_to_gt_last_elem(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
            right = node.comparators[0]
            rs, re_ = _span(source, right)
            text = source[rs:re_]
            if 'seq[-1]' in text or ('seq[' in text and 'len(seq)' in text):
                ls, le = _span(source, node.left)
                new_cmp = source[ls:le] + " > " + text
                out.append(_splice(source, node, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule 8 / 9: strict comparisons against `x` should be non-strict
# ----------------------------------------------------------------------

def _lt_to_le_x(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            if isinstance(node.left, ast.Name) and node.left.id == 'x':
                ls, le = _span(source, node.left)
                rs, re_ = _span(source, node.comparators[0])
                new_cmp = source[ls:le] + " <= " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


def _gt_to_ge_x(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == 'x':
                ls, le = _span(source, node.left)
                rs, re_ = _span(source, node.comparators[0])
                new_cmp = source[ls:le] + " >= " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule 10: `range(seq)`, `for i in len(seq)`, `range(len(seq)-1)` slips
# ----------------------------------------------------------------------

def _fix_range_calls(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        it = node.iter
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == 'range' \
                and len(it.args) == 1:
            arg = it.args[0]
            if isinstance(arg, ast.Name) and arg.id == 'seq':
                s, e = _span(source, arg)
                out.append(source[:s] + "len(seq)" + source[e:])
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                left = arg.left
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == 'len':
                    s, e = _span(source, arg)
                    ls, le = _span(source, left)
                    out.append(source[:s] + source[ls:le] + source[e:])
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == 'len':
            s, e = _span(source, it)
            out.append(source[:s] + "range(" + source[s:e] + ")" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 11 / 12: `for i, x in seq` style shadowing of the search value `x`
# ----------------------------------------------------------------------

def _wrap_enumerate_missing(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and len(node.target.elts) == 2:
            it = node.iter
            if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == 'enumerate'):
                s, e = _span(source, it)
                text = source[s:e]
                out.append(source[:s] + f"enumerate({text})" + source[e:])
    return out


def _unshadow_x_in_enumerate(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and len(node.target.elts) == 2:
            second = node.target.elts[1]
            if isinstance(second, ast.Name) and second.id == 'x':
                s, e = _span(source, second)
                out.append(source[:s] + "elem" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 13: `seq.index[i]` used instead of `seq.index(i)`
# ----------------------------------------------------------------------

def _fix_index_subscript_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
                and node.value.attr == 'index':
            vs, ve = _span(source, node.value)
            value_text = source[vs:ve]
            target = node.slice
            if hasattr(ast, 'Index') and isinstance(target, ast.Index):
                target = target.value
            ts, te = _span(source, target)
            slice_text = source[ts:te]
            new_text = f"{value_text}({slice_text})"
            out.append(_splice(source, node, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 14: `count==0` typo'd as a comparison instead of an assignment
# ----------------------------------------------------------------------

def _fix_eq_assign_typo(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for stmt in fn.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Compare) \
                    and len(stmt.value.ops) == 1 and isinstance(stmt.value.ops[0], ast.Eq) \
                    and isinstance(stmt.value.left, ast.Name):
                left_s, left_e = _span(source, stmt.value.left)
                right = stmt.value.comparators[0]
                right_s, right_e = _span(source, right)
                new_text = source[left_s:left_e] + " = " + source[right_s:right_e]
                out.append(_splice(source, stmt.value, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 15: counter used (augmented-assigned or returned) without ever
# being initialized -> insert `name = 0` at the top of the function.
# ----------------------------------------------------------------------

def _ensure_counter_initialized(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if not fn.body:
            continue
        param_names = {a.arg for a in fn.args.args}
        candidates = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                candidates.add(node.target.id)
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                candidates.add(node.value.id)
        candidates -= param_names
        candidates -= {'True', 'False', 'None'}
        first = fn.body[0]
        for name in sorted(candidates):
            already_init = False
            if isinstance(first, ast.Assign):
                for t in first.targets:
                    if isinstance(t, ast.Name) and t.id == name:
                        already_init = True
            if already_init:
                continue
            indent = ' ' * first.col_offset
            s, _e = _span(source, first)
            out.append(source[:s] + f"{name} = 0\n{indent}" + source[s:])
    return out


# ----------------------------------------------------------------------
# Rule 16: `while ...: if cond: advance` with no else -> potential
# infinite loop when the condition never becomes false (add a break).
# ----------------------------------------------------------------------

def _add_break_to_dead_while(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and len(node.body) == 1 and isinstance(node.body[0], ast.If):
            ifn = node.body[0]
            if not ifn.orelse:
                s, e = _span(source, ifn)
                indent = ' ' * ifn.col_offset
                insertion = "\n" + indent + "else:\n" + indent + "    break"
                out.append(source[:e] + insertion + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 17: `return count - 1` style off-by-one on a return value
# ----------------------------------------------------------------------

def _remove_minus_one_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) \
                and isinstance(node.value.op, ast.Sub) \
                and isinstance(node.value.right, ast.Constant) and node.value.right.value == 1:
            ls, le = _span(source, node.value.left)
            out.append(_splice(source, node.value, source[ls:le]))
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="fix_or_precedence_bare_literal",
                 apply=_fix_or_precedence,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="reorder_emptiness_test_first",
                 apply=_reorder_emptiness_first,
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="empty_guard_body_should_return_zero",
                 apply=_fix_empty_branch,
                 symptoms=("wrong", "err:TypeError", "err:IndexError")),
            Rule(name="add_missing_empty_guard",
                 apply=_add_empty_guard,
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="move_misplaced_loop_else",
                 apply=_move_else_after_loop,
                 symptoms=("wrong",)),
            Rule(name="append_missing_fallback_return",
                 apply=_append_fallback_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="ge_to_gt_on_last_element_check",
                 apply=_ge_to_gt_last_elem,
                 symptoms=("wrong",)),
            Rule(name="strict_lt_to_le_on_x",
                 apply=_lt_to_le_x,
                 symptoms=("wrong",)),
            Rule(name="strict_gt_to_ge_on_x",
                 apply=_gt_to_ge_x,
                 symptoms=("wrong",)),
            Rule(name="fix_range_len_wrapping",
                 apply=_fix_range_calls,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="wrap_missing_enumerate",
                 apply=_wrap_enumerate_missing,
                 symptoms=("err:ValueError", "wrong")),
            Rule(name="unshadow_x_in_enumerate_target",
                 apply=_unshadow_x_in_enumerate,
                 symptoms=("wrong",)),
            Rule(name="fix_index_subscript_should_be_call",
                 apply=_fix_index_subscript_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_eq_assign_typo",
                 apply=_fix_eq_assign_typo,
                 symptoms=("err:NameError", "err:UnboundLocalError")),
            Rule(name="ensure_counter_initialized",
                 apply=_ensure_counter_initialized,
                 symptoms=("err:NameError", "err:UnboundLocalError")),
            Rule(name="add_break_to_dead_while",
                 apply=_add_break_to_dead_while,
                 symptoms=("timeout",)),
            Rule(name="remove_spurious_minus_one_on_return",
                 apply=_remove_minus_one_return,
                 symptoms=("wrong",)),
        ]