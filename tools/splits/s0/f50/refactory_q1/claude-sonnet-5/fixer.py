"""
Repair rules for the "Sequential Search" assignment.

Each rule performs a single, local, structural edit located via the AST and
spliced into the original source text (never a full rewrite).
"""

import ast

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# Generic span / splice helpers
# ---------------------------------------------------------------------------

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
    except SyntaxError:
        return None


def _param_name(fn, idx, default=None):
    args = fn.args.args
    if len(args) > idx:
        return args[idx].arg
    return default


def _slice_val(s):
    if isinstance(s, ast.Index):  # py < 3.9 compatibility
        return s.value
    return s


def _is_len_call(node, seqname):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == seqname
    )


def _is_last_elem(node, seqname):
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == seqname:
        val = _slice_val(node.slice)
        if (
            isinstance(val, ast.UnaryOp)
            and isinstance(val.op, ast.USub)
            and isinstance(val.operand, ast.Constant)
            and val.operand.value == 1
        ):
            return True
        if (
            isinstance(val, ast.BinOp)
            and isinstance(val.op, ast.Sub)
            and _is_len_call(val.left, seqname)
            and isinstance(val.right, ast.Constant)
            and val.right.value == 1
        ):
            return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "max"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == seqname
    ):
        return True
    return False


def _is_first_elem(node, seqname):
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == seqname:
        val = _slice_val(node.slice)
        if isinstance(val, ast.Constant) and val.value == 0:
            return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "min"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == seqname
    ):
        return True
    return False


def _is_empty_literal(node):
    return isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) == 0


def _is_emptiness_test(node):
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.Is)):
        l, r = node.left, node.comparators[0]
        if isinstance(l, ast.Name) and _is_empty_literal(r):
            return True
        if isinstance(r, ast.Name) and _is_empty_literal(l):
            return True
        if (
            isinstance(l, ast.Call)
            and isinstance(l.func, ast.Name)
            and l.func.id == "len"
            and isinstance(r, ast.Constant)
            and r.value == 0
        ):
            return True
        if (
            isinstance(r, ast.Call)
            and isinstance(r.func, ast.Name)
            and r.func.id == "len"
            and isinstance(l, ast.Constant)
            and l.value == 0
        ):
            return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Name):
        return True
    if isinstance(node, ast.BoolOp):
        return any(_is_emptiness_test(v) for v in node.values)
    return False


def _name_and_empty_lit(cmp):
    l, r = cmp.left, cmp.comparators[0]
    if isinstance(l, ast.Name) and _is_empty_literal(r):
        return l, r
    if isinstance(r, ast.Name) and _is_empty_literal(l):
        return r, l
    return None


def _direct_boundary_subscript(test, seqname):
    for n in ast.walk(test):
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == seqname:
            val = _slice_val(n.slice)
            if isinstance(val, ast.Constant) and val.value == 0:
                return True
            if (
                isinstance(val, ast.UnaryOp)
                and isinstance(val.op, ast.USub)
                and isinstance(val.operand, ast.Constant)
                and val.operand.value == 1
            ):
                return True
    return False


def _iter_stmt_lists(tree):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(node, field, None)
            if isinstance(lst, list):
                yield lst


# ---------------------------------------------------------------------------
# Rule 1: `seq == () or []`  (bare empty literal instead of a comparison)
# ---------------------------------------------------------------------------

def _or_literal_emptiness_bug(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and len(node.values) == 2:
            a, b = node.values
            for cmp_side, lit_side in ((a, b), (b, a)):
                if (
                    isinstance(cmp_side, ast.Compare)
                    and len(cmp_side.ops) == 1
                    and isinstance(cmp_side.ops[0], ast.Eq)
                    and _is_empty_literal(lit_side)
                ):
                    pair = _name_and_empty_lit(cmp_side)
                    if pair is None:
                        continue
                    name_node, lit_a = pair
                    ns, ne = _span(source, name_node)
                    la_s, la_e = _span(source, lit_a)
                    lb_s, lb_e = _span(source, lit_side)
                    name_text = source[ns:ne]
                    new_text = "{0} == {1} or {0} == {2}".format(
                        name_text, source[la_s:la_e], source[lb_s:lb_e]
                    )
                    cand = _splice(source, node, new_text)
                    if cand != source:
                        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 2: empty-check branch returns the wrong sentinel instead of 0
# ---------------------------------------------------------------------------

def _empty_check_wrong_sentinel(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_emptiness_test(node.test) and len(node.body) == 1:
            stmt = node.body[0]
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                val = stmt.value
                bad = False
                if isinstance(val, ast.Constant) and val.value != 0:
                    bad = True
                elif isinstance(val, (ast.Tuple, ast.List)):
                    bad = True
                if bad:
                    cand = _splice(source, stmt, "return 0")
                    if cand != source:
                        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 3: `if <empty check>: pass` instead of returning 0
# ---------------------------------------------------------------------------

def _pass_in_empty_check(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and _is_emptiness_test(node.test)
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Pass)
        ):
            cand = _splice(source, node.body[0], "return 0")
            if cand != source:
                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 4: trailing `return i + 1` at the end of the function -> `return len(seq)`
# ---------------------------------------------------------------------------

def _trailing_index_plus_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.body:
            last = fn.body[-1]
            if (
                isinstance(last, ast.Return)
                and isinstance(last.value, ast.BinOp)
                and isinstance(last.value.op, ast.Add)
                and isinstance(last.value.left, ast.Name)
                and isinstance(last.value.right, ast.Constant)
                and last.value.right.value == 1
            ):
                seqname = _param_name(fn, 1, "seq")
                cand = _splice(source, last, "return len({0})".format(seqname))
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 5: function ends with a for/while loop and no fallback return
# ---------------------------------------------------------------------------

def _terminal_loop_missing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.body:
            last = fn.body[-1]
            if isinstance(last, (ast.For, ast.While)):
                seqname = _param_name(fn, 1, "seq")
                indent = " " * last.col_offset
                _, e = _span(source, last)
                cand = source[:e] + "\n" + indent + "return len({0})".format(seqname) + source[e:]
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 6: `x >= <last elem>: return len(seq)` should be strict `>`
# ---------------------------------------------------------------------------

def _boundary_last_elem_strict(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        seqname = _param_name(fn, 1, "seq")
        for node in ast.walk(fn):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                test = node.test
                if (
                    isinstance(test.ops[0], ast.GtE)
                    and _is_last_elem(test.comparators[0], seqname)
                    and len(node.body) == 1
                ):
                    stmt = node.body[0]
                    if isinstance(stmt, ast.Return) and stmt.value is not None and _is_len_call(stmt.value, seqname):
                        ls, le = _span(source, test.left)
                        rs, re_ = _span(source, test.comparators[0])
                        new_cmp = source[ls:le] + " > " + source[rs:re_]
                        cand = _splice(source, test, new_cmp)
                        if cand != source:
                            out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 7: `x <= <first elem>: return 0` should be strict `<`
# ---------------------------------------------------------------------------

def _boundary_first_elem_strict(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        seqname = _param_name(fn, 1, "seq")
        for node in ast.walk(fn):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                test = node.test
                if (
                    isinstance(test.ops[0], ast.LtE)
                    and _is_first_elem(test.comparators[0], seqname)
                    and len(node.body) == 1
                ):
                    stmt = node.body[0]
                    if (
                        isinstance(stmt, ast.Return)
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value == 0
                    ):
                        ls, le = _span(source, test.left)
                        rs, re_ = _span(source, test.comparators[0])
                        new_cmp = source[ls:le] + " < " + source[rs:re_]
                        cand = _splice(source, test, new_cmp)
                        if cand != source:
                            out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 8: `range(len(seq) - 1)` drops the last index -> `range(len(seq))`
# ---------------------------------------------------------------------------

def _range_off_by_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        seqname = _param_name(fn, 1, "seq")
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.For)
                and isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"
                and len(node.iter.args) == 1
            ):
                arg = node.iter.args[0]
                if (
                    isinstance(arg, ast.BinOp)
                    and isinstance(arg.op, ast.Sub)
                    and _is_len_call(arg.left, seqname)
                    and isinstance(arg.right, ast.Constant)
                    and arg.right.value == 1
                ):
                    cand = _splice(source, arg, "len({0})".format(seqname))
                    if cand != source:
                        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 9: `name == value` as a bare statement is an assignment typo
# ---------------------------------------------------------------------------

def _eq_assignment_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq) and isinstance(cmp.left, ast.Name):
                ns, ne = _span(source, cmp.left)
                vs, ve = _span(source, cmp.comparators[0])
                new_text = "{0} = {1}".format(source[ns:ne], source[vs:ve])
                cand = _splice(source, node, new_text)
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 10: `if x < elem: continue` followed by an unconditional `return i`
# has the comparison direction backwards; should skip while elem < x.
# ---------------------------------------------------------------------------

def _continue_direction_flip(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args:
            continue
        xname = fn.args.args[0].arg
        for lst in _iter_stmt_lists(fn):
            for i in range(len(lst) - 1):
                cur, nxt = lst[i], lst[i + 1]
                if (
                    isinstance(cur, ast.If)
                    and not cur.orelse
                    and len(cur.body) == 1
                    and isinstance(cur.body[0], ast.Continue)
                ):
                    test = cur.test
                    if (
                        isinstance(test, ast.Compare)
                        and len(test.ops) == 1
                        and isinstance(test.left, ast.Name)
                        and test.left.id == xname
                        and isinstance(nxt, ast.Return)
                        and isinstance(nxt.value, ast.Name)
                    ):
                        op = test.ops[0]
                        new_op = None
                        if isinstance(op, ast.Lt):
                            new_op = " > "
                        elif isinstance(op, ast.LtE):
                            new_op = " >= "
                        if new_op is not None:
                            ls, le = _span(source, test.left)
                            rs, re_ = _span(source, test.comparators[0])
                            new_cmp = source[ls:le] + new_op + source[rs:re_]
                            cand = _splice(source, test, new_cmp)
                            if cand != source:
                                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 11: first statement indexes seq[0]/seq[-1] with no emptiness guard
# ---------------------------------------------------------------------------

def _insert_empty_guard(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.body:
            continue
        first = fn.body[0]
        if not isinstance(first, ast.If) or _is_emptiness_test(first.test):
            continue
        seqname = _param_name(fn, 1, None)
        if seqname is None:
            continue
        if not _direct_boundary_subscript(first.test, seqname):
            continue
        s, _ = _span(source, first)
        indent = " " * first.col_offset
        prefix = "if not {0}:\n{1}    return 0\n{1}el".format(seqname, indent)
        cand = source[:s] + prefix + source[s:]
        if cand != source:
            out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 12: `if x < elem: return i` (no equality case) should be `<=`
# ---------------------------------------------------------------------------

def _lt_to_le_loop_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.Lt)
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Return)
            and isinstance(node.body[0].value, ast.Name)
        ):
            test = node.test
            ls, le = _span(source, test.left)
            rs, re_ = _span(source, test.comparators[0])
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            cand = _splice(source, test, new_cmp)
            if cand != source:
                out.append(cand)
    return out


# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="or_literal_emptiness_bug",
                apply=_or_literal_emptiness_bug,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="empty_check_wrong_sentinel",
                apply=_empty_check_wrong_sentinel,
                symptoms=("wrong",),
            ),
            Rule(
                name="pass_in_empty_check",
                apply=_pass_in_empty_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="trailing_index_plus_one",
                apply=_trailing_index_plus_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="terminal_loop_missing_return",
                apply=_terminal_loop_missing_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="boundary_last_elem_strict",
                apply=_boundary_last_elem_strict,
                symptoms=("wrong",),
            ),
            Rule(
                name="boundary_first_elem_strict",
                apply=_boundary_first_elem_strict,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_off_by_one",
                apply=_range_off_by_one,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="eq_assignment_typo",
                apply=_eq_assignment_typo,
                symptoms=("err:NameError", "wrong", "timeout"),
            ),
            Rule(
                name="continue_direction_flip",
                apply=_continue_direction_flip,
                symptoms=("wrong",),
            ),
            Rule(
                name="insert_empty_guard",
                apply=_insert_empty_guard,
                symptoms=("err:IndexError", "wrong"),
            ),
            Rule(
                name="lt_to_le_loop_return",
                apply=_lt_to_le_loop_return,
                symptoms=("wrong",),
            ),
        ]