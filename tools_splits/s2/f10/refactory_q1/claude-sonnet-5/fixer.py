"""
Repair rules for the "Sequential Search" assignment.

Each rule inspects the AST of a submission, looks for one specific,
narrow misconception pattern, and if found returns one or more
candidate sources produced by a small, local text splice (never a
full rewrite).
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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _enclosing_function(node):
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, ast.FunctionDef):
            return cur
        cur = getattr(cur, "parent", None)
    return None


def _enclosing_for(node):
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, ast.For):
            return cur
        cur = getattr(cur, "parent", None)
    return None


def _first_param(func):
    if func.args.args:
        return func.args.args[0].arg
    return None


def _target_names(target):
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names = set()
        for e in target.elts:
            names |= _target_names(e)
        return names
    return set()


def _mentions_names(stmt, names):
    for n in ast.walk(stmt):
        if isinstance(n, ast.Name) and n.id in names:
            return True
    return False


def _get_slice_expr(sl):
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _line_indent(line):
    return len(line) - len(line.lstrip(" "))


def _dedupe(cands, source):
    out = []
    for c in cands:
        if c and c != source and c not in out:
            out.append(c)
    return out


# ----------------------------------------------------------------------
# Rule 1: `seq == [] or ()` style boolean-or missing comparison
# ----------------------------------------------------------------------

def _fix_missing_or_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if (isinstance(a, ast.Compare) and len(a.ops) == 1 and isinstance(a.ops[0], ast.Eq)
                    and not isinstance(b, ast.Compare)):
                left_text = ast.get_source_segment(source, a.left)
                right_text = ast.get_source_segment(source, a.comparators[0])
                b_text = ast.get_source_segment(source, b)
                if left_text and right_text and b_text:
                    new_text = "{0} == {1} or {0} == {2}".format(left_text, right_text, b_text)
                    out.append(_splice(source, node, new_text))
            elif (isinstance(b, ast.Compare) and len(b.ops) == 1 and isinstance(b.ops[0], ast.Eq)
                    and not isinstance(a, ast.Compare)):
                left_text = ast.get_source_segment(source, b.left)
                right_text = ast.get_source_segment(source, b.comparators[0])
                a_text = ast.get_source_segment(source, a)
                if left_text and right_text and a_text:
                    new_text = "{0} == {1} or {0} == {2}".format(left_text, a_text, right_text)
                    out.append(_splice(source, node, new_text))
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Rule 2: strict `x < elem` should be `x <= elem`
# ----------------------------------------------------------------------

def _strict_lt_x_to_le(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            func = _enclosing_function(node)
            if func is None:
                continue
            xparam = _first_param(func)
            if not xparam:
                continue
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and left.id == xparam:
                rsrc = ast.get_source_segment(source, right) or ""
                if "len(" in rsrc:
                    continue
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " <= " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Rule 3: comparison direction swapped: `elem > x` should be `x > elem`
# ----------------------------------------------------------------------

def _swap_elem_x_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Gt, ast.Lt)):
            func = _enclosing_function(node)
            if func is None:
                continue
            xparam = _first_param(func)
            if not xparam:
                continue
            left, right = node.left, node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Name) and right.id == xparam and left.id != xparam:
                forloop = _enclosing_for(node)
                if forloop is not None and isinstance(forloop.target, ast.Name) and forloop.target.id == left.id:
                    op_sym = ">" if isinstance(node.ops[0], ast.Gt) else "<"
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    new_cmp = source[rs:re_] + " " + op_sym + " " + source[ls:le]
                    out.append(_splice(source, node, new_cmp))
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Rule 4: premature return inside a for-loop (fires every iteration
# instead of only after the loop finishes)
# ----------------------------------------------------------------------

def _hoist_premature_loop_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    lines = source.splitlines(keepends=True)
    out = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        body = node.body

        # Case 1: [..., If(returns, no orelse), Return(...)]
        if len(body) >= 2 and isinstance(body[-1], ast.Return) and body[-1].lineno == body[-1].end_lineno:
            prev = body[-2]
            if (isinstance(prev, ast.If) and not prev.orelse
                    and any(isinstance(n, ast.Return) for s in prev.body for n in ast.walk(s))):
                names = _target_names(node.target)
                if not _mentions_names(body[-1], names):
                    cand = _hoist_trailing_stmt(lines, node, body[-1])
                    if cand:
                        out.append(cand)

        # Case 2: For body is a single If with an orelse that returns
        if len(body) == 1 and isinstance(body[0], ast.If):
            ifn = body[0]
            if (len(ifn.orelse) == 1 and isinstance(ifn.orelse[0], ast.Return)
                    and ifn.orelse[0].lineno == ifn.orelse[0].end_lineno):
                names = _target_names(node.target)
                if not _mentions_names(ifn.orelse[0], names):
                    cand = _hoist_else_return(lines, node, ifn)
                    if cand:
                        out.append(cand)

    return _dedupe(out, source)


def _hoist_trailing_stmt(lines, for_node, ret_node):
    try:
        for_start = for_node.lineno - 1
        for_end = for_node.end_lineno - 1
        ret_idx = ret_node.lineno - 1
        if not (for_start < ret_idx <= for_end):
            return None
        new_lines = lines[:]
        stripped = new_lines[ret_idx].strip("\n").lstrip()
        for_indent = _line_indent(new_lines[for_start])
        new_stmt_line = " " * for_indent + stripped + "\n"
        del new_lines[ret_idx]
        new_for_end = for_end - 1
        new_lines.insert(new_for_end + 1, new_stmt_line)
        return "".join(new_lines)
    except Exception:
        return None


def _hoist_else_return(lines, for_node, ifn):
    try:
        for_start = for_node.lineno - 1
        for_end = for_node.end_lineno - 1
        or_idx = ifn.orelse[0].lineno - 1
        else_idx = None
        lower_bound = ifn.body[-1].end_lineno - 1
        for idx in range(or_idx - 1, lower_bound - 1, -1):
            if lines[idx].strip().startswith("else"):
                else_idx = idx
                break
        if else_idx is None:
            return None
        new_lines = lines[:]
        stripped = new_lines[or_idx].strip("\n").lstrip()
        for_indent = _line_indent(new_lines[for_start])
        new_stmt_line = " " * for_indent + stripped + "\n"
        num_removed = or_idx - else_idx + 1
        del new_lines[else_idx: or_idx + 1]
        new_for_end = for_end - num_removed
        new_lines.insert(new_for_end + 1, new_stmt_line)
        return "".join(new_lines)
    except Exception:
        return None


# ----------------------------------------------------------------------
# Rule 5: for-loop that searches but never falls back to `return len(seq)`
# ----------------------------------------------------------------------

def _infer_seq_text(source, iter_node):
    if isinstance(iter_node, ast.Call):
        fname = getattr(iter_node.func, "id", None)
        if fname == "range" and len(iter_node.args) == 1:
            arg = iter_node.args[0]
            if isinstance(arg, ast.Call) and getattr(arg.func, "id", None) == "len" and len(arg.args) == 1:
                return ast.get_source_segment(source, arg.args[0])
        if fname == "enumerate" and len(iter_node.args) >= 1:
            return ast.get_source_segment(source, iter_node.args[0])
    if isinstance(iter_node, ast.Name):
        return ast.get_source_segment(source, iter_node)
    return None


def _append_missing_fallback_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    lines = source.splitlines(keepends=True)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        body = node.body
        if not body:
            continue
        last = body[-1]
        if not isinstance(last, ast.For) or last.orelse:
            continue
        has_return = any(isinstance(n, ast.Return) for s in last.body for n in ast.walk(s))
        if not has_return:
            continue
        seq_text = _infer_seq_text(source, last.iter)
        if not seq_text:
            continue
        try:
            for_indent = _line_indent(lines[last.lineno - 1])
            new_line = " " * for_indent + "return len({0})\n".format(seq_text)
            new_lines = lines[:]
            insert_idx = last.end_lineno
            new_lines.insert(insert_idx, new_line)
            out.append("".join(new_lines))
        except Exception:
            continue
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Rule 6: `return len(seq) + 1` (or `- 1`) off-by-one
# ----------------------------------------------------------------------

def _is_len_call(n):
    return isinstance(n, ast.Call) and getattr(n.func, "id", None) == "len" and len(n.args) == 1


def _is_const_one(n):
    return isinstance(n, ast.Constant) and n.value == 1


def _len_offset_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) \
                and isinstance(node.value.op, (ast.Add, ast.Sub)):
            bn = node.value
            left, right = bn.left, bn.right
            if _is_len_call(left) and _is_const_one(right):
                new_text = ast.get_source_segment(source, left)
                if new_text:
                    out.append(_splice(source, bn, new_text))
            elif _is_len_call(right) and _is_const_one(left) and isinstance(bn.op, ast.Add):
                new_text = ast.get_source_segment(source, right)
                if new_text:
                    out.append(_splice(source, bn, new_text))
    return _dedupe(out, source)


def _len_var_offset_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) \
                and isinstance(node.value.op, (ast.Add, ast.Sub)):
            bn = node.value
            left, right = bn.left, bn.right
            name_node = None
            if isinstance(left, ast.Name) and _is_const_one(right):
                name_node = left
            elif isinstance(right, ast.Name) and _is_const_one(left) and isinstance(bn.op, ast.Add):
                name_node = right
            if name_node is None:
                continue
            func = _enclosing_function(node)
            if func is None:
                continue
            len_arg = None
            for st in func.body:
                if (isinstance(st, ast.Assign) and len(st.targets) == 1
                        and isinstance(st.targets[0], ast.Name) and st.targets[0].id == name_node.id):
                    val = st.value
                    if _is_len_call(val):
                        len_arg = val.args[0]
                    break
            if len_arg is not None:
                arg_text = ast.get_source_segment(source, len_arg)
                if arg_text:
                    out.append(_splice(source, bn, "len({0})".format(arg_text)))
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Rule 7: normalize `seq[len(seq) - 1]` to `seq[-1]`
# ----------------------------------------------------------------------

def _normalize_last_index(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            val = node.value
            sl = _get_slice_expr(node.slice)
            if isinstance(sl, ast.BinOp) and isinstance(sl.op, ast.Sub):
                l, r = sl.left, sl.right
                if (_is_len_call(l) and isinstance(l.args[0], ast.Name)
                        and isinstance(val, ast.Name) and val.id == l.args[0].id
                        and _is_const_one(r)):
                    val_text = ast.get_source_segment(source, val)
                    if val_text:
                        out.append(_splice(source, node, "{0}[-1]".format(val_text)))
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Rule 8: off-by-one boundary comparison `x >= <last elem>` -> `x > <last elem>`
# ----------------------------------------------------------------------

def _boundary_gte_to_gt(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
            func = _enclosing_function(node)
            if func is None:
                continue
            xparam = _first_param(func)
            left, right = node.left, node.comparators[0]
            if not (isinstance(left, ast.Name) and left.id == xparam):
                continue
            is_boundary = False
            if isinstance(right, ast.Subscript):
                sl = _get_slice_expr(right.slice)
                if (isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub)
                        and isinstance(sl.operand, ast.Constant) and sl.operand.value == 1):
                    is_boundary = True
                if isinstance(sl, ast.BinOp) and isinstance(sl.op, ast.Sub):
                    ln, rn = sl.left, sl.right
                    if _is_len_call(ln) and _is_const_one(rn):
                        is_boundary = True
            if isinstance(right, ast.Call) and getattr(right.func, "id", None) == "max" and len(right.args) == 1:
                is_boundary = True
            if is_boundary:
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " > " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Rule 9: `range(len(seq) - 1)` misses the last index
# ----------------------------------------------------------------------

def _extend_range_bound(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                l, r = arg.left, arg.right
                if _is_len_call(l) and _is_const_one(r):
                    new_text = ast.get_source_segment(source, l)
                    if new_text:
                        out.append(_splice(source, arg, new_text))
    return _dedupe(out, source)


# ----------------------------------------------------------------------
# Fixer
# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_missing_or_compare",
                apply=_fix_missing_or_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_x_to_le",
                apply=_strict_lt_x_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="swap_elem_x_compare",
                apply=_swap_elem_x_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="hoist_premature_loop_return",
                apply=_hoist_premature_loop_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="append_missing_fallback_return",
                apply=_append_missing_fallback_return,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="len_offset_fix",
                apply=_len_offset_fix,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="len_var_offset_fix",
                apply=_len_var_offset_fix,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="normalize_last_index",
                apply=_normalize_last_index,
                symptoms=("wrong",),
            ),
            Rule(
                name="boundary_gte_to_gt",
                apply=_boundary_gte_to_gt,
                symptoms=("wrong",),
            ),
            Rule(
                name="extend_range_bound",
                apply=_extend_range_bound,
                symptoms=("wrong", "err:IndexError"),
            ),
        ]