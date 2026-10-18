"""
Repair rules for the Sequential Search assignment.

Each rule is a small, local, structural AST-guided source transformation.
Rules never rewrite whole functions; they splice a small replacement text
into the original source at the span of a located AST node (or a nearby
line/statement boundary), leaving everything else byte-identical.
"""

import ast

from src.core.repair import Rule


# ----------------------------------------------------------------------
# generic span/splice helpers
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


def _indent_at(source, node):
    """whitespace prefix on the line where `node` starts (assumes node
    is the first token on its own line, true for compound statements)."""
    s, _ = _span(source, node)
    line_start = source.rfind("\n", 0, s) + 1
    return source[line_start:s]


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _dedup(source, candidates):
    out = []
    seen = set()
    for c in candidates:
        if c is None or c == source:
            continue
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


_IndexType = getattr(ast, "Index", None)


def _slice_expr(sl):
    if _IndexType is not None and isinstance(sl, _IndexType):
        return sl.value
    return sl


# ----------------------------------------------------------------------
# 1. comparison-strictness toggle (< <-> <=, > <-> >=)
# ----------------------------------------------------------------------

_STRICT_FLIP = {ast.Lt: "<=", ast.LtE: "<", ast.Gt: ">=", ast.GtE: ">"}


def _toggle_strictness(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if type(op) in _STRICT_FLIP:
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " " + _STRICT_FLIP[type(op)] + " " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 2. comparison-direction flip (< <-> >, <= <-> >=), operands unchanged
# ----------------------------------------------------------------------

_DIR_FLIP = {ast.Lt: ">", ast.Gt: "<", ast.LtE: ">=", ast.GtE: "<="}


def _flip_direction(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if type(op) in _DIR_FLIP:
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " " + _DIR_FLIP[type(op)] + " " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 3. "seq == () or []" style bug: bare falsy literal instead of a real check
# ----------------------------------------------------------------------

def _is_bare_empty(node):
    return isinstance(node, (ast.List, ast.Tuple)) and len(node.elts) == 0


def _fix_empty_boolop_literal(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and len(node.values) == 2:
            a, b = node.values
            compare, bare = None, None
            if isinstance(a, ast.Compare) and _is_bare_empty(b):
                compare, bare = a, b
            elif isinstance(b, ast.Compare) and _is_bare_empty(a):
                compare, bare = b, a
            if compare is None:
                continue
            if len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Eq):
                continue
            ls, le = _span(source, compare.left)
            left_text = source[ls:le]
            cs, ce = _span(source, compare)
            cmp_text = source[cs:ce]
            other_kind = "[]" if isinstance(bare, ast.Tuple) else "()"
            new_bool = f"{cmp_text} or {left_text} == {other_kind}"
            out.append(_splice(source, node, new_bool))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 4. single-sided empty check missing the list/tuple alternative
#    e.g. `if seq == ():` should be `if seq == () or seq == []:`
# ----------------------------------------------------------------------

def _fix_single_empty_check(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], (ast.Eq, ast.Is)):
            left = node.test.left
            comp = node.test.comparators[0]
            if isinstance(left, ast.Name) and _is_bare_empty(comp):
                other_kind = "[]" if isinstance(comp, ast.Tuple) else "()"
                s, e = _span(source, node.test)
                new_test = source[s:e] + f" or {left.id} == {other_kind}"
                out.append(_splice(source, node.test, new_test))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 5. emptiness check guards the wrong thing (returns None/garbage, or `pass`)
# ----------------------------------------------------------------------

def _looks_like_empty_check(test):
    for node in ast.walk(test):
        if isinstance(node, ast.Compare):
            for c in node.comparators:
                if _is_bare_empty(c):
                    return True
            if isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name) \
                    and node.left.func.id == "len":
                for c in node.comparators:
                    if isinstance(c, ast.Constant) and c.value == 0:
                        return True
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return True
    return False


def _fix_empty_check_wrong_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _looks_like_empty_check(node.test):
            for stmt in node.body:
                if isinstance(stmt, ast.Return):
                    if stmt.value is None:
                        out.append(_splice(source, stmt, "return 0"))
                    elif not (isinstance(stmt.value, ast.Constant) and stmt.value.value == 0):
                        s, e = _span(source, stmt.value)
                        out.append(source[:s] + "0" + source[e:])
                elif isinstance(stmt, ast.Pass):
                    out.append(_splice(source, stmt, "return 0"))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 6. fallback `return len(seq)` wrongly placed inside the loop body
#    (fires on first iteration only) -> move it to after the loop
# ----------------------------------------------------------------------

def _fix_misplaced_loop_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        body = node.body
        indent = _indent_at(source, node)
        if len(body) == 2 and isinstance(body[0], ast.If) and not body[0].orelse \
                and isinstance(body[1], ast.Return):
            ret_stmt = body[1]
            ret_s, ret_e = _span(source, ret_stmt)
            line_start = source.rfind("\n", 0, ret_s) + 1
            ret_text = source[ret_s:ret_e]
            new_source = source[:line_start] + "\n" + indent + ret_text + source[ret_e:]
            out.append(new_source)
        elif len(body) == 1 and isinstance(body[0], ast.If) and len(body[0].orelse) == 1 \
                and isinstance(body[0].orelse[0], ast.Return) and body[0].body:
            if_stmt = body[0]
            ret_stmt = if_stmt.orelse[0]
            last_body_stmt = if_stmt.body[-1]
            _, after_body_end = _span(source, last_body_stmt)
            ret_s, ret_e = _span(source, ret_stmt)
            ret_text = source[ret_s:ret_e]
            new_source = source[:after_body_end] + "\n" + indent + ret_text + source[ret_e:]
            out.append(new_source)
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 7. function falls off the end of a terminal for-loop without a fallback
#    return -> append `return len(seq)` at function-body indentation
# ----------------------------------------------------------------------

def _append_missing_fallback_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.body:
            continue
        last = node.body[-1]
        if not isinstance(last, ast.For) or last.orelse:
            continue
        seq_name = "seq"
        if len(node.args.args) >= 2:
            seq_name = node.args.args[1].arg
        indent = _indent_at(source, last)
        _, e = _span(source, last)
        insertion = "\n" + indent + f"return len({seq_name})"
        out.append(source[:e] + insertion + source[e:])
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 8. range()/len() mis-wiring: `len(range(x))`, `range(seq)`, `for i in len(seq)`
# ----------------------------------------------------------------------

def _fix_range_len_wrapping(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        it = node.iter
        new_text = None
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name):
            if it.func.id == "len" and len(it.args) == 1:
                inner = it.args[0]
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) \
                        and inner.func.id == "range" and len(inner.args) == 1:
                    xs, xe = _span(source, inner.args[0])
                    new_text = "range(len(" + source[xs:xe] + "))"
                else:
                    s, e = _span(source, it)
                    new_text = "range(" + source[s:e] + ")"
            elif it.func.id == "range" and len(it.args) == 1:
                arg = it.args[0]
                if not (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "len"):
                    s, e = _span(source, arg)
                    new_text = "range(len(" + source[s:e] + "))"
        if new_text:
            out.append(_splice(source, it, new_text))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 9. `position += position` doubling instead of incrementing by one
# ----------------------------------------------------------------------

def _fix_double_increment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) \
                and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name) \
                and node.target.id == node.value.id:
            out.append(_splice(source, node.value, "1"))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 10. stray +-1 offset on a returned loop index
# ----------------------------------------------------------------------

def _fix_off_by_one_return_offset(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp):
            bo = node.value
            if isinstance(bo.op, (ast.Sub, ast.Add)) and isinstance(bo.right, ast.Constant) \
                    and bo.right.value == 1:
                s, e = _span(source, bo.left)
                out.append(_splice(source, bo, source[s:e]))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 11. loop-index primed with 0 but an empty-sequence fallback needs -1
#     (i = 0; for i in range(len(seq)): ...; return i + 1)
# ----------------------------------------------------------------------

def _fix_zero_init_before_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        for idx in range(len(body) - 1):
            a, b = body[idx], body[idx + 1]
            if isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Name) \
                    and isinstance(a.value, ast.Constant) and a.value.value == 0 \
                    and isinstance(b, ast.For) and isinstance(b.target, ast.Name) \
                    and b.target.id == a.targets[0].id:
                name = a.targets[0].id
                found = False
                for node in ast.walk(fn):
                    if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) \
                            and isinstance(node.value.op, ast.Add) \
                            and isinstance(node.value.left, ast.Name) and node.value.left.id == name \
                            and isinstance(node.value.right, ast.Constant) and node.value.right.value == 1:
                        found = True
                        break
                if found:
                    out.append(_splice(source, a.value, "-1"))
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 12. iterating over values but using the loop variable as an index
#     (for i in seq: ... seq[i] ...) -> for i in range(len(seq))
# ----------------------------------------------------------------------

def _fix_value_iteration_as_index(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Name):
            iname = node.target.id
            seqname = node.iter.id
            uses_index = False
            for sub in ast.walk(node):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) and sub.value.id == seqname:
                    target_expr = _slice_expr(sub.slice)
                    if isinstance(target_expr, ast.Name) and target_expr.id == iname:
                        uses_index = True
                        break
            if uses_index:
                s, e = _span(source, node.iter)
                out.append(source[:s] + f"range(len({seqname}))" + source[e:])
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 13. a local `newvar = list(seq)` assignment, used earlier (before its
#     own assignment) via the wrong name -> replace premature uses with
#     the actual parameter name
# ----------------------------------------------------------------------

def _fix_premature_var_reference(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        assigns = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                    and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) \
                    and node.value.func.id == "list" and len(node.value.args) == 1 \
                    and isinstance(node.value.args[0], ast.Name):
                newname = node.targets[0].id
                param = node.value.args[0].id
                assign_s, _ = _span(source, node)
                assigns.append((newname, param, assign_s))
        for newname, param, assign_pos in assigns:
            bad_spans = []
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Name) and sub.id == newname and isinstance(sub.ctx, ast.Load):
                    s, e = _span(source, sub)
                    if s < assign_pos:
                        bad_spans.append((s, e))
            if bad_spans:
                bad_spans.sort(reverse=True)
                new_source = source
                for s, e in bad_spans:
                    new_source = new_source[:s] + param + new_source[e:]
                out.append(new_source)
    return _dedup(source, out)


# ----------------------------------------------------------------------
# 14. `for i, x in seq:` missing enumerate()
# ----------------------------------------------------------------------

def _fix_missing_enumerate(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and len(node.target.elts) == 2:
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "enumerate":
                continue
            if isinstance(it, ast.Name):
                s, e = _span(source, it)
                out.append(source[:s] + f"enumerate({source[s:e]})" + source[e:])
    return _dedup(source, out)


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="toggle_comparison_strictness",
                 apply=_toggle_strictness,
                 symptoms=("wrong",)),
            Rule(name="flip_comparison_direction",
                 apply=_flip_direction,
                 symptoms=("wrong",)),
            Rule(name="empty_check_bare_falsy_literal",
                 apply=_fix_empty_boolop_literal,
                 symptoms=("wrong",)),
            Rule(name="empty_check_missing_alternative",
                 apply=_fix_single_empty_check,
                 symptoms=("wrong",)),
            Rule(name="empty_check_wrong_return_value",
                 apply=_fix_empty_check_wrong_return,
                 symptoms=("wrong",)),
            Rule(name="loop_fallback_return_misplaced",
                 apply=_fix_misplaced_loop_return,
                 symptoms=("wrong",)),
            Rule(name="missing_fallback_return_after_loop",
                 apply=_append_missing_fallback_return,
                 symptoms=("wrong",)),
            Rule(name="range_len_mis_wiring",
                 apply=_fix_range_len_wrapping,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="double_increment_instead_of_plus_one",
                 apply=_fix_double_increment,
                 symptoms=("wrong", "timeout")),
            Rule(name="stray_offset_on_return",
                 apply=_fix_off_by_one_return_offset,
                 symptoms=("wrong",)),
            Rule(name="zero_init_should_be_neg_one",
                 apply=_fix_zero_init_before_loop,
                 symptoms=("wrong",)),
            Rule(name="value_iteration_used_as_index",
                 apply=_fix_value_iteration_as_index,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="premature_variable_reference",
                 apply=_fix_premature_var_reference,
                 symptoms=("err:UnboundLocalError", "err:NameError")),
            Rule(name="missing_enumerate_on_tuple_unpack",
                 apply=_fix_missing_enumerate,
                 symptoms=("err:TypeError", "err:ValueError", "wrong")),
        ]