import ast

from src.core.repair import Rule


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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _subscript_index(slice_node):
    if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):
        return slice_node.value
    return slice_node


def _is_empty_check(test):
    """True if `test` looks like a check that a sequence is empty."""
    if isinstance(test, ast.BoolOp):
        return any(_is_empty_check(v) for v in test.values)
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
        a, b = test.left, test.comparators[0]
        for side, other in ((a, b), (b, a)):
            if isinstance(side, (ast.List, ast.Tuple)) and len(side.elts) == 0:
                return True
            if isinstance(side, ast.Call) and isinstance(side.func, ast.Name) and side.func.id == "len":
                if isinstance(other, ast.Constant) and other.value == 0:
                    return True
    return False


def _first_param(fn, idx):
    if fn.args.args and len(fn.args.args) > idx:
        return fn.args.args[idx].arg
    return None


# ---------------------------------------------------------------------------
# Rule: insert a guard for the empty-sequence case at the top of the function
# ---------------------------------------------------------------------------
def _add_empty_guard(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef) or not fn.body:
                continue
            seqparam = _first_param(fn, 1)
            if seqparam is None:
                continue
            first = fn.body[0]
            target = first
            if (isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant)
                    and isinstance(first.value.value, str)):
                target = fn.body[1] if len(fn.body) > 1 else None
            if target is None:
                continue
            if isinstance(target, ast.If) and _is_empty_check(target.test):
                continue
            indent = " " * target.col_offset
            ts, _ = _span(source, target)
            guard = f"if len({seqparam}) == 0:\n{indent}    return 0\n{indent}"
            out.append(source[:ts] + guard + source[ts:])
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: relax a strict `<` comparison against the search value to `<=`
# ---------------------------------------------------------------------------
def _fix_strict_lt(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            xparam = _first_param(fn, 0)
            if xparam is None:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                    left, right = node.left, node.comparators[0]
                    involves_x = ((isinstance(left, ast.Name) and left.id == xparam) or
                                  (isinstance(right, ast.Name) and right.id == xparam))
                    if involves_x:
                        ls, le = _span(source, left)
                        rs, re_ = _span(source, right)
                        new_cmp = source[ls:le] + " <= " + source[rs:re_]
                        out.append(_splice(source, node, new_cmp))
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: `>=` against the last element should be strict `>`
# ---------------------------------------------------------------------------
def _is_last_elem_subscript(node):
    if not isinstance(node, ast.Subscript):
        return False
    idx = _subscript_index(node.slice)
    if isinstance(idx, ast.UnaryOp) and isinstance(idx.op, ast.USub):
        if isinstance(idx.operand, ast.Constant) and idx.operand.value == 1:
            return True
    if isinstance(idx, ast.BinOp) and isinstance(idx.op, ast.Sub):
        if (isinstance(idx.left, ast.Call) and isinstance(idx.left.func, ast.Name)
                and idx.left.func.id == "len" and isinstance(idx.right, ast.Constant)
                and idx.right.value == 1):
            return True
    return False


def _fix_last_elem_ge_to_gt(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                right = node.comparators[0]
                if _is_last_elem_subscript(right):
                    ls, le = _span(source, node.left)
                    rs, re_ = _span(source, right)
                    new_text = source[ls:le] + " > " + source[rs:re_]
                    out.append(_splice(source, node, new_text))
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: `seq == () or []` operator-precedence slip
# ---------------------------------------------------------------------------
def _fix_or_bare_empty_literal(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                for val in node.values:
                    if isinstance(val, (ast.List, ast.Tuple)) and len(val.elts) == 0:
                        name_text = None
                        for other in node.values:
                            if isinstance(other, ast.Compare) and isinstance(other.left, ast.Name):
                                name_text = other.left.id
                                break
                        if name_text is None:
                            continue
                        vs, ve = _span(source, val)
                        val_text = source[vs:ve]
                        replacement = f"{name_text} == {val_text}"
                        out.append(source[:vs] + replacement + source[ve:])
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: missing `seq == []` alongside an existing `seq == ()` check
# ---------------------------------------------------------------------------
def _add_missing_list_empty_check(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                tuple_idx = None
                list_present = False
                varname = None
                for i, v in enumerate(node.values):
                    if isinstance(v, ast.Compare) and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq):
                        a, b = v.left, v.comparators[0]
                        if isinstance(a, ast.Name):
                            if isinstance(b, ast.Tuple) and len(b.elts) == 0:
                                tuple_idx = i
                                varname = a.id
                            if isinstance(b, ast.List) and len(b.elts) == 0:
                                list_present = True
                if tuple_idx is not None and not list_present:
                    target = node.values[tuple_idx]
                    s, e = _span(source, target)
                    new_text = source[s:e] + f" or {varname} == []"
                    out.append(source[:s] + new_text + source[e:])
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: reorder `or` conditions so safety (emptiness) checks come first
# ---------------------------------------------------------------------------
def _fix_unsafe_or_order(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) >= 2:
                flags = [_is_empty_check(v) for v in node.values]
                if any(flags) and not flags[0]:
                    order = sorted(range(len(node.values)), key=lambda i: not flags[i])
                    texts = []
                    for i in order:
                        s, e = _span(source, node.values[i])
                        texts.append(source[s:e])
                    new_text = " or ".join(texts)
                    out.append(_splice(source, node, new_text))
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: returning the search value instead of the loop index
# ---------------------------------------------------------------------------
def _fix_return_x_instead_of_index(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            xparam = _first_param(fn, 0)
            if xparam is None:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                    loopvar = node.target.id
                    if loopvar == xparam:
                        continue
                    for sub in ast.walk(node):
                        if (isinstance(sub, ast.Return) and isinstance(sub.value, ast.Name)
                                and sub.value.id == xparam):
                            vs, ve = _span(source, sub.value)
                            out.append(source[:vs] + loopvar + source[ve:])
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: swapped operands in a counting-loop comparison (`elem > x` -> `x > elem`)
# ---------------------------------------------------------------------------
def _fix_swapped_count_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            xparam = _first_param(fn, 0)
            if xparam is None:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                    loopvar = node.target.id
                    for sub in ast.walk(node):
                        if (isinstance(sub, ast.Compare) and len(sub.ops) == 1
                                and isinstance(sub.ops[0], ast.Gt)
                                and isinstance(sub.left, ast.Name) and sub.left.id == loopvar
                                and len(sub.comparators) == 1
                                and isinstance(sub.comparators[0], ast.Name)
                                and sub.comparators[0].id == xparam):
                            new_text = f"{xparam} > {loopvar}"
                            out.append(_splice(source, sub, new_text))
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: an `if/else` pair inside the loop returns `len(seq)` on the FIRST
# mismatch instead of after exhausting the loop; move the else out.
# ---------------------------------------------------------------------------
def _move_return_out_of_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            body = node.body
            # Case A: single `if ...: return i` / `else: return X`
            if len(body) == 1 and isinstance(body[0], ast.If):
                ifn = body[0]
                if (len(ifn.orelse) == 1 and isinstance(ifn.orelse[0], ast.Return)
                        and ifn.body and isinstance(ifn.body[-1], ast.Return)):
                    ret_node = ifn.orelse[0]
                    rs, re_ = _span(source, ret_node)
                    ret_text = source[rs:re_]
                    test_s, test_e = _span(source, ifn.test)
                    b0s, _ = _span(source, ifn.body[0])
                    _, blaste = _span(source, ifn.body[-1])
                    body_indent = " " * ifn.body[0].col_offset
                    new_if = "if " + source[test_s:test_e] + ":\n" + body_indent + source[b0s:blaste]
                    for_indent = " " * node.col_offset
                    if_s, if_e = _span(source, ifn)
                    new_source = source[:if_s] + new_if + "\n" + for_indent + ret_text + source[if_e:]
                    out.append(new_source)
            # Case B: `if ...: return i` followed by a sibling unconditional return
            if len(body) >= 2 and isinstance(body[-1], ast.Return) and isinstance(body[-2], ast.If) \
                    and not body[-2].orelse:
                ifn = body[-2]
                ret_node = body[-1]
                rs, re_ = _span(source, ret_node)
                ret_text = source[rs:re_]
                if_s, if_e = _span(source, ifn)
                node_s, node_e = _span(source, node)
                for_indent = " " * node.col_offset
                new_source = source[:if_e] + source[node_e:]
                insertion_point = if_e
                new_source = new_source[:insertion_point] + "\n" + for_indent + ret_text + new_source[insertion_point:]
                out.append(new_source)
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: `if cond: return X` ... `else: continue` -> drop the dead else-branch
# ---------------------------------------------------------------------------
def _strip_redundant_else_continue(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if (isinstance(node, ast.If) and len(node.orelse) == 1
                    and isinstance(node.orelse[0], ast.Continue) and node.body):
                test_s, test_e = _span(source, node.test)
                b0s, _ = _span(source, node.body[0])
                _, blaste = _span(source, node.body[-1])
                body_indent = " " * node.body[0].col_offset
                new_if = "if " + source[test_s:test_e] + ":\n" + body_indent + source[b0s:blaste]
                out.append(_splice(source, node, new_if))
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: `if cond: continue` ... `else: return X` -> `if not (cond): return X`
# ---------------------------------------------------------------------------
def _invert_if_continue_else_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if (isinstance(node, ast.If) and len(node.body) == 1
                    and isinstance(node.body[0], ast.Continue)
                    and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return)):
                test_s, test_e = _span(source, node.test)
                ret = node.orelse[0]
                rs, re_ = _span(source, ret)
                ret_text = source[rs:re_]
                new_if = "if not (" + source[test_s:test_e] + "):\n" + (" " * ret.col_offset) + ret_text
                out.append(_splice(source, node, new_if))
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: `return len(seq) + 1` -> `return len(seq)`
# ---------------------------------------------------------------------------
def _fix_len_plus_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if (isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp)
                    and isinstance(node.value.op, ast.Add)):
                left, right = node.value.left, node.value.right
                if (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                        and left.func.id == "len" and isinstance(right, ast.Constant)
                        and right.value == 1):
                    ls, le = _span(source, left)
                    out.append(_splice(source, node.value, source[ls:le]))
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: a for-loop is the last reachable statement with no trailing return
# ---------------------------------------------------------------------------
def _add_missing_trailing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        parent_map = {}
        for parent in ast.walk(tree):
            for field, value in ast.iter_fields(parent):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            parent_map[item] = (parent, field)

        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            seqparam = _first_param(fn, 1)
            if seqparam is None:
                continue
            for node in ast.walk(fn):
                if not isinstance(node, ast.For) or node.orelse:
                    continue
                parent, field = parent_map.get(node, (None, None))
                if parent is None:
                    continue
                body_list = getattr(parent, field)
                if node not in body_list:
                    continue
                idx = body_list.index(node)
                siblings_after = body_list[idx + 1:]
                has_return_after = any(isinstance(s, ast.Return) for s in siblings_after)
                if not has_return_after:
                    node_s, node_e = _span(source, node)
                    indent = " " * node.col_offset
                    insertion = "\n" + indent + f"return len({seqparam})"
                    out.append(source[:node_e] + insertion + source[node_e:])
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: a bare `return` (returns None) should return len(seq)
# ---------------------------------------------------------------------------
def _fix_bare_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            seqparam = _first_param(fn, 1)
            if seqparam is None:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Return) and node.value is None:
                    s, e = _span(source, node)
                    out.append(source[:s] + f"return len({seqparam})" + source[e:])
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: an emptiness check as the first condition *inside* the loop (dead
# code, since an empty sequence never enters the loop) should be hoisted out.
# ---------------------------------------------------------------------------
def _hoist_empty_check_out_of_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not isinstance(node, ast.For) or len(node.body) != 1:
                continue
            outer_if = node.body[0]
            if not isinstance(outer_if, ast.If):
                continue
            if not _is_empty_check(outer_if.test):
                continue
            if len(outer_if.orelse) != 1 or not isinstance(outer_if.orelse[0], ast.If):
                continue
            if not outer_if.body:
                continue
            inner_if = outer_if.orelse[0]

            test_s, test_e = _span(source, outer_if.test)
            b0s, _ = _span(source, outer_if.body[0])
            _, blaste = _span(source, outer_if.body[-1])
            outer_test_text = source[test_s:test_e]
            outer_body_text = source[b0s:blaste]

            for_indent = " " * node.col_offset
            inner_indent = " " * outer_if.body[0].col_offset
            pre_check = f"if {outer_test_text}:\n{inner_indent}{outer_body_text}\n{for_indent}"

            inner_if_s, inner_if_e = _span(source, inner_if)
            inner_if_text = source[inner_if_s:inner_if_e]

            node_s, node_e = _span(source, node)
            body_start_s, _ = _span(source, node.body[0])
            for_header_text = source[node_s:body_start_s]
            new_for_block = for_header_text + inner_if_text
            new_source = source[:node_s] + pre_check + new_for_block + source[node_e:]
            out.append(new_source)
    except Exception:
        return []
    return out


# ---------------------------------------------------------------------------
# Rule: off-by-one on range bound (remove a spurious `-1`)
# ---------------------------------------------------------------------------
def _fix_range_minus_one_remove(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if (isinstance(node, ast.For) and isinstance(node.iter, ast.Call)
                    and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range"
                    and len(node.iter.args) == 1):
                arg = node.iter.args[0]
                if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
                        and isinstance(arg.right, ast.Constant) and arg.right.value == 1):
                    ls, le = _span(source, arg.left)
                    out.append(_splice(source, arg, source[ls:le]))
    except Exception:
        return []
    return out


def _is_plus_one_index(sl, tgt):
    idx = _subscript_index(sl)
    return (isinstance(idx, ast.BinOp) and isinstance(idx.op, ast.Add)
            and isinstance(idx.left, ast.Name) and idx.left.id == tgt
            and isinstance(idx.right, ast.Constant) and idx.right.value == 1)


def _fix_range_minus_one_add(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.For) and isinstance(node.iter, ast.Call)
                    and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range"
                    and len(node.iter.args) == 1):
                continue
            if not isinstance(node.target, ast.Name):
                continue
            tgt = node.target.id
            arg = node.iter.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                continue
            uses_next = any(
                isinstance(n, ast.Subscript) and _is_plus_one_index(n.slice, tgt)
                for n in ast.walk(node)
            )
            if uses_next:
                s, e = _span(source, arg)
                out.append(source[:s] + f"({source[s:e]})-1" + source[e:])
    except Exception:
        return []
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="add_empty_sequence_guard",
                apply=_add_empty_guard,
                symptoms=("wrong", "err:IndexError", "err:TypeError"),
            ),
            Rule(
                name="relax_strict_lt_on_search_value",
                apply=_fix_strict_lt,
                symptoms=("wrong",),
            ),
            Rule(
                name="last_element_boundary_ge_to_gt",
                apply=_fix_last_elem_ge_to_gt,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_or_bare_empty_literal_precedence",
                apply=_fix_or_bare_empty_literal,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_missing_list_empty_check",
                apply=_add_missing_list_empty_check,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="reorder_unsafe_or_conditions",
                apply=_fix_unsafe_or_order,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="return_index_not_value",
                apply=_fix_return_x_instead_of_index,
                symptoms=("wrong",),
            ),
            Rule(
                name="swap_count_loop_comparison_operands",
                apply=_fix_swapped_count_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="move_early_return_out_of_loop",
                apply=_move_return_out_of_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="strip_redundant_else_continue",
                apply=_strip_redundant_else_continue,
                symptoms=("wrong",),
            ),
            Rule(
                name="invert_if_continue_else_return",
                apply=_invert_if_continue_else_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_len_plus_one",
                apply=_fix_len_plus_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_missing_trailing_return",
                apply=_add_missing_trailing_return,
                symptoms=("wrong", "err:UnboundLocalError", "err:NameError"),
            ),
            Rule(
                name="fix_bare_return_none",
                apply=_fix_bare_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="hoist_empty_check_out_of_loop",
                apply=_hoist_empty_check_out_of_loop,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="range_bound_off_by_one_remove",
                apply=_fix_range_minus_one_remove,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_bound_off_by_one_add",
                apply=_fix_range_minus_one_add,
                symptoms=("wrong", "err:IndexError"),
            ),
        ]