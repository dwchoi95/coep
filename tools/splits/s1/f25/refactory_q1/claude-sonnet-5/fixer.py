"""
Repair rules for the "Sequential Search" assignment.

Each rule performs a small, local, AST-located, text-spliced edit that
reproduces a common misconception transformation observed across buggy
submissions. Rules are intentionally narrow in trigger but broad in the
sense that they key on *shape*, not on specific identifiers/literals.
"""

import ast

from src.core.repair import Rule


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

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


def _indent_of(source, node):
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[:node.col_offset]


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _dedup_nonempty(source, outs):
    seen = []
    for o in outs:
        if o and o != source and o not in seen:
            seen.append(o)
    return seen


# ----------------------------------------------------------------------
# Rule 1: strict '<' comparison should be '<=' (off-by-one on boundary)
# ----------------------------------------------------------------------

def _strict_lt_to_le(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 2: '>=' against an upper-bound element (seq[-1] style) should be '>'
# ----------------------------------------------------------------------

def _gte_to_gt_upper_bound(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.GtE):
            right = node.comparators[0]
            if isinstance(right, ast.Subscript):
                ls, le = _span(source, node.left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " > " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 3: comparison operands swapped relative to the first parameter
# (e.g. "i > x" should be "x > i")
# ----------------------------------------------------------------------

def _swap_compare_sides(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    op_text = {ast.Gt: ">", ast.Lt: "<", ast.GtE: ">=", ast.LtE: "<="}
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args:
            continue
        xparam = fn.args.args[0].arg
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 \
               and type(node.ops[0]) in op_text:
                left, right = node.left, node.comparators[0]
                if not (isinstance(left, (ast.Name, ast.Subscript)) and
                        isinstance(right, (ast.Name, ast.Subscript))):
                    continue
                lname = left.id if isinstance(left, ast.Name) else None
                rname = right.id if isinstance(right, ast.Name) else None
                if (lname == xparam) != (rname == xparam):
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    new_cmp = (source[rs:re_] + " " + op_text[type(node.ops[0])]
                               + " " + source[ls:le])
                    out.append(_splice(source, node, new_cmp))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 4: function falls off the end of a for-loop without a final
# "return len(seq)" style statement.
# ----------------------------------------------------------------------

def _missing_trailing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.body:
            continue
        last = fn.body[-1]
        if isinstance(last, ast.For) and not last.orelse:
            has_return = any(isinstance(n, ast.Return) for n in ast.walk(last))
            if not has_return:
                continue
            seqname = "seq"
            if len(fn.args.args) >= 2:
                seqname = fn.args.args[1].arg
            indent = _indent_of(source, last)
            s, e = _span(source, last)
            insertion = "\n" + indent + "return len(" + seqname + ")"
            out.append(source[:e] + insertion + source[e:])
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 5: an unconditional/else "return len(seq)"-like statement sits
# INSIDE the for loop, causing it to fire on the first iteration.
# Move it to after the loop.
# ----------------------------------------------------------------------

def _deloop_early_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        body = node.body
        try:
            # Case A: [If(no-orelse, body ends in Return), Return] sibling
            if (len(body) == 2 and isinstance(body[0], ast.If)
                    and not body[0].orelse and isinstance(body[1], ast.Return)
                    and body[0].body and isinstance(body[0].body[-1], ast.Return)):
                if_node = body[0]
                escaping = body[1]
                if_end = _span(source, if_node)[1]
                for_start, for_end = _span(source, node)
                esc_start, esc_end = _span(source, escaping)
                esc_text = source[esc_start:esc_end]
                indent = _indent_of(source, node)
                new_for_text = source[for_start:if_end]
                new_after = "\n" + indent + esc_text + source[for_end:]
                out.append(source[:for_start] + new_for_text + new_after)
            # Case B: [If(body ends in Return, orelse=[Return])]
            elif (len(body) == 1 and isinstance(body[0], ast.If)
                    and len(body[0].orelse) == 1
                    and isinstance(body[0].orelse[0], ast.Return)
                    and body[0].body and isinstance(body[0].body[-1], ast.Return)):
                if_node = body[0]
                escaping = if_node.orelse[0]
                after_body_end = _span(source, if_node.body[-1])[1]
                for_start, for_end = _span(source, node)
                esc_start, esc_end = _span(source, escaping)
                esc_text = source[esc_start:esc_end]
                indent = _indent_of(source, node)
                new_for_text = source[for_start:after_body_end]
                new_after = "\n" + indent + esc_text + source[for_end:]
                out.append(source[:for_start] + new_for_text + new_after)
        except Exception:
            continue
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 6: "return i + 1" after a loop over range(len(X)) / enumerate(X)
# is an off-by-one; should be "return len(X)".
# ----------------------------------------------------------------------

def _offbyone_return_plus_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for for_node in ast.walk(fn):
            if not isinstance(for_node, ast.For):
                continue
            var = None
            length_text = None
            it = for_node.iter
            if isinstance(for_node.target, ast.Name) and isinstance(it, ast.Call) \
               and isinstance(it.func, ast.Name) and it.func.id == "range" \
               and len(it.args) == 1:
                arg = it.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) \
                   and arg.func.id == "len":
                    var = for_node.target.id
                    s, e = _span(source, arg)
                    length_text = source[s:e]
            elif isinstance(for_node.target, ast.Tuple) and len(for_node.target.elts) == 2 \
                    and isinstance(for_node.target.elts[0], ast.Name) \
                    and isinstance(it, ast.Call) and isinstance(it.func, ast.Name) \
                    and it.func.id == "enumerate" and len(it.args) >= 1:
                var = for_node.target.elts[0].id
                s, e = _span(source, it.args[0])
                length_text = "len(" + source[s:e] + ")"
            if var is None or length_text is None:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) \
                   and isinstance(node.value.op, ast.Add) \
                   and isinstance(node.value.left, ast.Name) and node.value.left.id == var \
                   and isinstance(node.value.right, ast.Constant) \
                   and node.value.right.value == 1:
                    out.append(_splice(source, node.value, length_text))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 7: range(X + 1) should be range(X)
# ----------------------------------------------------------------------

def _range_plus_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add) \
               and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                ls, le = _span(source, arg.left)
                new_call = "range(" + source[ls:le] + ")"
                out.append(_splice(source, node, new_call))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 8: range(seq) should be range(len(seq))
# ----------------------------------------------------------------------

def _range_missing_len(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Name):
                s, e = _span(source, arg)
                new_arg = "len(" + source[s:e] + ")"
                out.append(_splice(source, arg, new_arg))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 9: "for i in len(seq):" should be "for i in range(len(seq)):"
# ----------------------------------------------------------------------

def _missing_range_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) \
               and it.func.id == "len":
                s, e = _span(source, it)
                new_iter = "range(" + source[s:e] + ")"
                out.append(_splice(source, it, new_iter))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 10: "seq == () or []" (precedence slip): the literal in the
# second operand is never compared against seq.
# ----------------------------------------------------------------------

def _fix_or_bare_literal(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            vals = node.values
            for i in range(len(vals) - 1):
                left = vals[i]
                right = vals[i + 1]
                if isinstance(left, ast.Compare) and isinstance(left.left, ast.Name) \
                   and len(left.ops) == 1 and isinstance(left.ops[0], ast.Eq) \
                   and isinstance(right, (ast.List, ast.Tuple)):
                    seqname = left.left.id
                    rs, re_ = _span(source, right)
                    new_text = seqname + " == " + source[rs:re_]
                    out.append(_splice(source, right, new_text))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 11: "name==0" used as a statement, meant to be "name = 0"
# ----------------------------------------------------------------------

def _eq_typo_assign(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare) \
           and len(node.value.ops) == 1 and isinstance(node.value.ops[0], ast.Eq) \
           and isinstance(node.value.left, ast.Name):
            left = node.value.left
            right = node.value.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_stmt = source[ls:le] + " = " + source[rs:re_]
            out.append(_splice(source, node, new_stmt))
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 12: for-loop with "if cond: break" then "return <loopvar>" after
# the loop -- break should be a return, and the trailing return should
# use the loop bound, not the last seen index.
# ----------------------------------------------------------------------

def _break_to_return_len(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        for idx, stmt in enumerate(body):
            if not (isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name)):
                continue
            var = stmt.target.id
            if not (len(stmt.body) == 1 and isinstance(stmt.body[0], ast.If)
                    and len(stmt.body[0].body) == 1
                    and isinstance(stmt.body[0].body[0], ast.Break)
                    and not stmt.body[0].orelse):
                continue
            if idx + 1 >= len(body):
                continue
            nxt = body[idx + 1]
            if not (isinstance(nxt, ast.Return) and isinstance(nxt.value, ast.Name)
                    and nxt.value.id == var):
                continue
            it = stmt.iter
            if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                    and it.func.id == "range" and len(it.args) == 1):
                continue
            try:
                ls, le = _span(source, it.args[0])
                length_text = source[ls:le]
                brk = stmt.body[0].body[0]
                bs, be = _span(source, brk)
                new_source = source[:bs] + ("return " + var) + source[be:]
                shift = len("return " + var) - (be - bs)
                rs, re_ = _span(source, nxt)
                rs += shift
                re_ += shift
                new_source = new_source[:rs] + ("return " + length_text) + new_source[re_:]
                out.append(new_source)
            except Exception:
                continue
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------
# Rule 13: top-level function not named "search"
# ----------------------------------------------------------------------

def _rename_to_search(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name != "search":
            lines = source.splitlines(keepends=True)
            starts = [0]
            for ln in lines:
                starts.append(starts[-1] + len(ln))
            line_start = starts[node.lineno - 1]
            line = lines[node.lineno - 1]
            needle = "def " + node.name
            idx = line.find(needle)
            if idx == -1:
                continue
            name_start = line_start + idx + len("def ")
            name_end = name_start + len(node.name)
            out.append(source[:name_start] + "search" + source[name_end:])
    return _dedup_nonempty(source, out)


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="strict_lt_to_le", apply=_strict_lt_to_le,
                 symptoms=("wrong",)),
            Rule(name="gte_to_gt_upper_bound", apply=_gte_to_gt_upper_bound,
                 symptoms=("wrong",)),
            Rule(name="swap_compare_sides", apply=_swap_compare_sides,
                 symptoms=("wrong",)),
            Rule(name="missing_trailing_return", apply=_missing_trailing_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="deloop_early_return", apply=_deloop_early_return,
                 symptoms=("wrong",)),
            Rule(name="offbyone_return_plus_one", apply=_offbyone_return_plus_one,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="range_plus_one", apply=_range_plus_one,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="range_missing_len", apply=_range_missing_len,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="missing_range_call", apply=_missing_range_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_or_bare_literal", apply=_fix_or_bare_literal,
                 symptoms=("wrong",)),
            Rule(name="eq_typo_assign", apply=_eq_typo_assign,
                 symptoms=("err:UnboundLocalError", "err:NameError", "wrong")),
            Rule(name="break_to_return_len", apply=_break_to_return_len,
                 symptoms=("wrong",)),
            Rule(name="rename_to_search", apply=_rename_to_search,
                 symptoms=("err:NameError", "wrong")),
        ]