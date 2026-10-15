"""
Repair rules for the "Sequential Search" assignment.

Each rule is a small, local, AST-located source-span splice targeting a
specific, generalizable misconception seen across many buggy submissions.
Rules never rewrite whole functions; they only touch the minimal span that
carries the bug.
"""

import ast

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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _get_params(tree):
    """Returns (first_param, second_param) of the last top-level `search`."""
    names = ("x", "seq")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "search":
            args = [a.arg for a in node.args.args]
            if len(args) >= 2:
                names = (args[0], args[1])
    return names


def _slice_value(sl):
    if isinstance(sl, ast.Index):
        sl = sl.value
    if isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub) \
       and isinstance(sl.operand, ast.Constant):
        return -sl.operand.value
    if isinstance(sl, ast.Constant):
        return sl.value
    return None


def _is_emptiness_test(test, seq_name):
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        operand = test.operand
        if isinstance(operand, ast.Name) and operand.id == seq_name:
            return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
        left = test.left
        comp = test.comparators[0]
        if isinstance(left, ast.Name) and left.id == seq_name:
            if isinstance(comp, (ast.Tuple, ast.List)) and not comp.elts:
                return True
            if isinstance(comp, ast.Call) and isinstance(comp.func, ast.Name) \
               and comp.func.id in ("tuple", "list") and not comp.args:
                return True
        if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
            if left.args and isinstance(left.args[0], ast.Name) and left.args[0].id == seq_name:
                if isinstance(comp, ast.Constant) and comp.value == 0:
                    return True
        if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "list":
            if left.args and isinstance(left.args[0], ast.Name) and left.args[0].id == seq_name:
                if isinstance(comp, (ast.List, ast.Tuple)) and not comp.elts:
                    return True
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
        return any(_is_emptiness_test(v, seq_name) for v in test.values)
    return False


def _build_parent_map(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


# ----------------------------------------------------------------------
# Rule 1: empty-guard branch returns/sets the wrong "empty" value
# ----------------------------------------------------------------------

def fix_empty_guard_wrong_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    _, seq_name = _get_params(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_emptiness_test(node.test, seq_name):
            body = node.body
            if len(body) != 1:
                continue
            stmt = body[0]
            if isinstance(stmt, ast.Pass):
                out.append(_splice(source, stmt, "return 0"))
            elif isinstance(stmt, ast.Return):
                if stmt.value is None:
                    out.append(_splice(source, stmt, "return 0"))
                else:
                    is_zero = isinstance(stmt.value, ast.Constant) and stmt.value.value == 0
                    if not is_zero:
                        vs, ve = _span(source, stmt.value)
                        out.append(source[:vs] + "0" + source[ve:])
            elif isinstance(stmt, ast.Assign):
                if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) \
                   and isinstance(stmt.value, ast.Constant) and stmt.value.value == 0:
                    out.append(_splice(source, stmt, "return 0"))
    return out


# ----------------------------------------------------------------------
# Rule 2: `seq == () or []` style broken boolean emptiness checks
# ----------------------------------------------------------------------

def fix_or_literal_emptiness_check(source):
    tree = _parse(source)
    if tree is None:
        return []
    _, seq_name = _get_params(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for val in node.values:
                if isinstance(val, (ast.List, ast.Tuple)) and not val.elts:
                    text = _text(source, val)
                    out.append(_splice(source, val, f"{seq_name} == {text}"))
    return out


# ----------------------------------------------------------------------
# Rule 3: `seq == 0` used instead of an emptiness check
# ----------------------------------------------------------------------

def fix_seq_eq_zero(source):
    tree = _parse(source)
    if tree is None:
        return []
    _, seq_name = _get_params(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if isinstance(left, ast.Name) and left.id == seq_name \
               and isinstance(right, ast.Constant) and right.value == 0:
                out.append(_splice(source, node, f"not {seq_name}"))
    return out


# ----------------------------------------------------------------------
# Rule 4: missing empty-sequence guard before seq[0]/seq[-1] access
# ----------------------------------------------------------------------

def insert_missing_empty_guard(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        if fn.name != "search":
            continue
        args = [a.arg for a in fn.args.args]
        if len(args) < 2:
            continue
        seq_name = args[1]
        body = fn.body
        idx0 = 0
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
           and isinstance(body[0].value.value, str):
            idx0 = 1
        if idx0 >= len(body):
            continue
        already = any(isinstance(s, ast.If) and _is_emptiness_test(s.test, seq_name)
                      for s in body[:idx0 + 1])
        if already:
            continue
        target = body[idx0]
        found = False
        for node in ast.walk(target):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
               and node.value.id == seq_name:
                if _slice_value(node.slice) in (0, -1):
                    found = True
                    break
        if not found:
            continue
        s, _ = _span(source, target)
        indent = " " * target.col_offset
        guard = f"if not {seq_name}:\n{indent}    return 0\n{indent}"
        out.append(source[:s] + guard + source[s:])
    return out


# ----------------------------------------------------------------------
# Rule 5: for-loop iterator missing range()/len()
# ----------------------------------------------------------------------

def fix_for_iter_missing_range(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "len":
                text = _text(source, it)
                out.append(_splice(source, it, f"range({text})"))
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range" \
               and len(it.args) == 1 and isinstance(it.args[0], ast.Name):
                arg = it.args[0]
                arg_text = _text(source, arg)
                out.append(_splice(source, arg, f"len({arg_text})"))
    return out


# ----------------------------------------------------------------------
# Rule 6: range(len(seq) +/- 1) off-by-one
# ----------------------------------------------------------------------

def fix_range_off_by_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" \
           and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Sub)):
                left = arg.left
                right = arg.right
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len" \
                   and isinstance(right, ast.Constant) and right.value == 1:
                    left_text = _text(source, left)
                    out.append(_splice(source, arg, left_text))
    return out


# ----------------------------------------------------------------------
# Rule 7: relax strict comparisons (< -> <=, > -> >=)
# ----------------------------------------------------------------------

def relax_strict_compare(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            new_op = None
            if isinstance(op, ast.Lt):
                new_op = "<="
            elif isinstance(op, ast.Gt):
                new_op = ">="
            if new_op:
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + f" {new_op} " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule 8: canonicalize `elem < x` style comparisons to `x <= elem`
# ----------------------------------------------------------------------

def canonicalize_elem_compare(source):
    tree = _parse(source)
    if tree is None:
        return []
    x_name, _ = _get_params(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            left, right = node.left, node.comparators[0]
            if isinstance(right, ast.Name) and right.id == x_name \
               and not (isinstance(left, ast.Name) and left.id == x_name) \
               and isinstance(op, (ast.Lt, ast.LtE)):
                left_text = _text(source, left)
                out.append(_splice(source, node, f"{x_name} <= {left_text}"))
    return out


# ----------------------------------------------------------------------
# Rule 9: `return x` inside a loop should return the loop index
# ----------------------------------------------------------------------

def fix_return_x_to_loop_var(source):
    tree = _parse(source)
    if tree is None:
        return []
    x_name, _ = _get_params(tree)
    parents = _build_parent_map(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == x_name:
            cur = parents.get(node)
            loop_var = None
            while cur is not None:
                if isinstance(cur, ast.For):
                    tgt = cur.target
                    if isinstance(tgt, ast.Name):
                        loop_var = tgt.id
                    elif isinstance(tgt, ast.Tuple) and tgt.elts and isinstance(tgt.elts[0], ast.Name):
                        loop_var = tgt.elts[0].id
                    break
                cur = parents.get(cur)
            if loop_var:
                vs, ve = _span(source, node.value)
                out.append(source[:vs] + loop_var + source[ve:])
    return out


# ----------------------------------------------------------------------
# Rule 10: a return statement trailing an `if` inside a loop body fires
# prematurely (same indentation as the `if`); move it after the loop.
# ----------------------------------------------------------------------

def move_trailing_stmt_out_of_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and len(node.body) == 2:
            first, second = node.body
            if isinstance(first, ast.If) and not first.orelse and isinstance(second, ast.Return):
                s_for, _ = _span(source, node)
                s_last, e_last = _span(source, second)
                before = source[s_for:s_last].rstrip()
                indent = " " * node.col_offset
                stmt_text = source[s_last:e_last]
                new_for = before + "\n" + indent + stmt_text
                out.append(_splice(source, node, new_for))
    return out


# ----------------------------------------------------------------------
# Rule 11: `if cond: return i / else: return len(seq)` inside a loop
# fires the else branch too early; move the else out of the loop.
# ----------------------------------------------------------------------

def move_else_out_of_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and len(node.body) == 1:
            if_node = node.body[0]
            if isinstance(if_node, ast.If) and if_node.orelse:
                if len(if_node.orelse) == 1 and isinstance(if_node.orelse[0], ast.If):
                    continue
                s_for, _ = _span(source, node)
                last_then = if_node.body[-1]
                _, e_then = _span(source, last_then)
                for_without_else = source[s_for:e_then]
                indent = " " * node.col_offset
                else_lines = []
                for stmt in if_node.orelse:
                    s_s, e_s = _span(source, stmt)
                    else_lines.append(indent + source[s_s:e_s])
                new_block = for_without_else + "\n" + "\n".join(else_lines)
                out.append(_splice(source, node, new_block))
    return out


# ----------------------------------------------------------------------
# Rule 12: for-loop is the last statement with no fallback return
# ----------------------------------------------------------------------

def append_missing_trailing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        if fn.name != "search" or not fn.body:
            continue
        args = [a.arg for a in fn.args.args]
        if len(args) < 2:
            continue
        seq_name = args[1]
        last = fn.body[-1]
        if isinstance(last, ast.For) and not last.orelse:
            _, e = _span(source, last)
            indent = " " * last.col_offset
            out.append(source[:e] + f"\n{indent}return len({seq_name})" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 13: trailing `return i + 1` should be `return len(seq)`
# ----------------------------------------------------------------------

def fix_trailing_iplus1(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        if fn.name != "search" or not fn.body:
            continue
        args = [a.arg for a in fn.args.args]
        if len(args) < 2:
            continue
        seq_name = args[1]
        last = fn.body[-1]
        if isinstance(last, ast.Return) and isinstance(last.value, ast.BinOp) \
           and isinstance(last.value.op, ast.Add):
            left, right = last.value.left, last.value.right
            if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and right.value == 1:
                found_loop = False
                for node in ast.walk(fn):
                    if isinstance(node, ast.For):
                        tgt = node.target
                        names = []
                        if isinstance(tgt, ast.Name):
                            names.append(tgt.id)
                        elif isinstance(tgt, ast.Tuple):
                            names.extend(e.id for e in tgt.elts if isinstance(e, ast.Name))
                        if left.id in names:
                            found_loop = True
                            break
                if found_loop:
                    vs, ve = _span(source, last.value)
                    out.append(source[:vs] + f"len({seq_name})" + source[ve:])
    return out


# ----------------------------------------------------------------------
# Rule 14: result variable only assigned inside a loop (unbound on
# empty input) - initialize it to 0 up front.
# ----------------------------------------------------------------------

def init_unbound_result_var(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        if fn.name != "search" or not fn.body:
            continue
        body = fn.body
        last = body[-1]
        if isinstance(last, ast.Return) and isinstance(last.value, ast.Name):
            name = last.value.id
            top_level_assigned = any(
                isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in s.targets)
                for s in body[:-1]
            )
            if top_level_assigned:
                continue
            nested_assigned = any(
                isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
                for node in ast.walk(fn)
            )
            if not nested_assigned:
                continue
            insert_idx = 0
            if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
               and isinstance(body[0].value.value, str):
                insert_idx = 1
            if insert_idx >= len(body):
                continue
            target_stmt = body[insert_idx]
            s, e = _span(source, target_stmt)
            indent = " " * target_stmt.col_offset
            new_text = f"{name} = 0\n{indent}" + source[s:e]
            out.append(_splice(source, target_stmt, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 15: `sorted(seq)` called but its result is discarded
# ----------------------------------------------------------------------

def fix_unused_sorted_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "sorted" \
               and len(call.args) == 1 and isinstance(call.args[0], ast.Name):
                name = call.args[0].id
                call_text = _text(source, call)
                out.append(_splice(source, node, f"{name} = {call_text}"))
    return out


# ----------------------------------------------------------------------
# Rule 16: a trailing bare expression statement forgot `return`
# ----------------------------------------------------------------------

def bare_expr_to_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    seen = set()
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list) and block:
                last = block[-1]
                if isinstance(last, ast.Expr):
                    val = last.value
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        continue
                    key = (last.lineno, last.col_offset, last.end_lineno, last.end_col_offset)
                    if key in seen:
                        continue
                    seen.add(key)
                    expr_text = _text(source, val)
                    out.append(_splice(source, last, f"return {expr_text}"))
    return out


# ----------------------------------------------------------------------
# Rule 17: `obj.method[arg]` meant to be a call `obj.method(arg)`
# ----------------------------------------------------------------------

def fix_method_subscript_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            sl = node.slice
            if isinstance(sl, ast.Index):
                sl = sl.value
            try:
                arg_text = _text(source, sl)
                base_text = _text(source, node.value)
            except Exception:
                continue
            out.append(_splice(source, node, f"{base_text}({arg_text})"))
    return out


# ----------------------------------------------------------------------
# Rule 18: accumulator initialized to 0 but should default to len(seq)
# (search-with-break pattern that never updates on "larger than all")
# ----------------------------------------------------------------------

def fix_break_accumulator_init(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        if fn.name != "search" or not fn.body:
            continue
        args = [a.arg for a in fn.args.args]
        if len(args) < 2:
            continue
        seq_name = args[1]
        for stmt in fn.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
               and isinstance(stmt.targets[0], ast.Name) \
               and isinstance(stmt.value, ast.Constant) and stmt.value.value == 0:
                var = stmt.targets[0].id
                last = fn.body[-1]
                if isinstance(last, ast.Return) and isinstance(last.value, ast.Name) and last.value.id == var:
                    has_break = any(isinstance(n2, ast.Break) for n2 in ast.walk(fn))
                    if has_break:
                        vs, ve = _span(source, stmt.value)
                        out.append(source[:vs] + f"len({seq_name})" + source[ve:])
    return out


# ----------------------------------------------------------------------
# Rule 19: `for i, x in seq:` missing enumerate()
# ----------------------------------------------------------------------

def fix_missing_enumerate(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and len(node.target.elts) == 2:
            it = node.iter
            if isinstance(it, ast.Name):
                text = _text(source, it)
                out.append(_splice(source, it, f"enumerate({text})"))
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="empty_guard_wrong_return", apply=fix_empty_guard_wrong_return,
                 symptoms=("wrong", "err:TypeError", "err:IndexError")),
            Rule(name="or_literal_emptiness_check", apply=fix_or_literal_emptiness_check,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="seq_eq_zero_check", apply=fix_seq_eq_zero,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="insert_missing_empty_guard", apply=insert_missing_empty_guard,
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="for_iter_missing_range", apply=fix_for_iter_missing_range,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="range_off_by_one", apply=fix_range_off_by_one,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="relax_strict_compare", apply=relax_strict_compare,
                 symptoms=("wrong",)),
            Rule(name="canonicalize_elem_compare", apply=canonicalize_elem_compare,
                 symptoms=("wrong",)),
            Rule(name="return_x_to_loop_var", apply=fix_return_x_to_loop_var,
                 symptoms=("wrong",)),
            Rule(name="move_trailing_stmt_out_of_loop", apply=move_trailing_stmt_out_of_loop,
                 symptoms=("wrong",)),
            Rule(name="move_else_out_of_loop", apply=move_else_out_of_loop,
                 symptoms=("wrong",)),
            Rule(name="append_missing_trailing_return", apply=append_missing_trailing_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="trailing_iplus1_to_lenseq", apply=fix_trailing_iplus1,
                 symptoms=("wrong",)),
            Rule(name="init_unbound_result_var", apply=init_unbound_result_var,
                 symptoms=("err:UnboundLocalError", "err:NameError", "wrong")),
            Rule(name="fix_unused_sorted_call", apply=fix_unused_sorted_call,
                 symptoms=("wrong",)),
            Rule(name="bare_expr_to_return", apply=bare_expr_to_return,
                 symptoms=("wrong",)),
            Rule(name="fix_method_subscript_call", apply=fix_method_subscript_call,
                 symptoms=("err:TypeError",)),
            Rule(name="break_accumulator_init", apply=fix_break_accumulator_init,
                 symptoms=("wrong",)),
            Rule(name="missing_enumerate", apply=fix_missing_enumerate,
                 symptoms=("err:TypeError", "wrong")),
        ]