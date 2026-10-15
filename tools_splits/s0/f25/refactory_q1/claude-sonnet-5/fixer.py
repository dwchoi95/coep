"""
Repair rules for the "Sequential Search" assignment.

Each rule inspects the AST of a buggy submission, locates a specific
structural misconception, and splices a small, local textual edit into
the original source (never rebuilding via ast.unparse).
"""

import ast

from src.core.repair import Rule


# ---------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------

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


def _get_search_fn(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "search":
            return node
    return None


def _contains_name(node, name):
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == name:
            return True
    return False


def _subscript_index_value(sub):
    sl = sub.slice
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        sl = sl.value
    return sl


def _is_risky_subscript(idxval):
    if isinstance(idxval, ast.Constant) and idxval.value == 0:
        return True
    if (
        isinstance(idxval, ast.UnaryOp)
        and isinstance(idxval.op, ast.USub)
        and isinstance(idxval.operand, ast.Constant)
        and idxval.operand.value == 1
    ):
        return True
    return False


def _segment(source, node):
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------
# Rule 1: `seq == () or []` style precedence slip
# ---------------------------------------------------------------------

def _fix_or_empty_precedence(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            vals = node.values
            cmp_left_text = None
            has_bare_empty = False
            for v in vals:
                if (
                    isinstance(v, ast.Compare)
                    and len(v.ops) == 1
                    and isinstance(v.ops[0], ast.Eq)
                ):
                    ls, le = _span(source, v.left)
                    cmp_left_text = source[ls:le]
                elif isinstance(v, (ast.List, ast.Tuple)) and len(v.elts) == 0:
                    has_bare_empty = True
            if cmp_left_text is None or not has_bare_empty:
                continue
            parts = []
            for v in vals:
                if isinstance(v, (ast.List, ast.Tuple)) and len(v.elts) == 0:
                    s, e = _span(source, v)
                    parts.append(f"{cmp_left_text} == {source[s:e]}")
                else:
                    s, e = _span(source, v)
                    parts.append(source[s:e])
            new_text = " or ".join(parts)
            candidate = _splice(source, node, new_text)
            if candidate != source:
                out.append(candidate)
    return out


# ---------------------------------------------------------------------
# Rule 2: append `return len(seq)` fallback when a terminal loop can
# fall through without returning.
# ---------------------------------------------------------------------

def _append_return_len(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    fn = _get_search_fn(tree)
    if fn is None or not fn.body:
        return []
    body = fn.body
    idx = len(body) - 1
    # ignore trailing bare string-literal statements (dangling docstrings)
    while idx >= 0 and isinstance(body[idx], ast.Expr) and isinstance(
        getattr(body[idx], "value", None), ast.Constant
    ) and isinstance(body[idx].value.value, str):
        idx -= 1
    if idx < 0:
        return []
    last_effective = body[idx]
    if not isinstance(last_effective, (ast.For, ast.While)):
        return []
    has_return = any(isinstance(n, ast.Return) for n in ast.walk(last_effective))
    if not has_return:
        return []
    params = fn.args.args
    seq_name = params[1].arg if len(params) > 1 else "seq"
    indent = " " * fn.body[0].col_offset
    insertion = f"\n{indent}return len({seq_name})"
    end_node = body[-1]
    _, e = _span(source, end_node)
    candidate = source[:e] + insertion + source[e:]
    if candidate != source:
        return [candidate]
    return []


# ---------------------------------------------------------------------
# Rule 3: final `return <loopvar>` should be `return len(X)`
# ---------------------------------------------------------------------

def _resolve_len_text(arg_node, fn, source):
    if (
        isinstance(arg_node, ast.Call)
        and isinstance(arg_node.func, ast.Name)
        and arg_node.func.id == "len"
        and arg_node.args
    ):
        s, e = _span(source, arg_node.args[0])
        return source[s:e]
    if isinstance(arg_node, ast.Name):
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == arg_node.id
            ):
                val = node.value
                if (
                    isinstance(val, ast.Call)
                    and isinstance(val.func, ast.Name)
                    and val.func.id == "len"
                    and val.args
                ):
                    s, e = _span(source, val.args[0])
                    return source[s:e]
    return None


def _fix_final_return_loopvar(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    fn = _get_search_fn(tree)
    if fn is None or not fn.body:
        return []
    last = fn.body[-1]
    if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Name)):
        return []
    loopvar = last.value.id
    len_text = None
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and node.target.id == loopvar
        ):
            it = node.iter
            if (
                isinstance(it, ast.Call)
                and isinstance(it.func, ast.Name)
                and it.func.id == "range"
                and it.args
            ):
                candidate_text = _resolve_len_text(it.args[-1], fn, source)
                if candidate_text is not None:
                    len_text = candidate_text
    if len_text is None:
        return []
    new_text = f"return len({len_text})"
    candidate = _splice(source, last, new_text)
    if candidate != source:
        return [candidate]
    return []


# ---------------------------------------------------------------------
# Rule 4 & 5: relax / tighten strict comparisons involving x
# ---------------------------------------------------------------------

def _first_param(fn):
    if fn.args.args:
        return fn.args.args[0].arg
    return "x"


def _relax_strict_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    fn = _get_search_fn(tree)
    if fn is None:
        return []
    xname = _first_param(fn)
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Compare):
            continue
        sides = [node.left] + list(node.comparators)
        for i, op in enumerate(node.ops):
            if isinstance(op, (ast.Lt, ast.Gt)):
                left, right = sides[i], sides[i + 1]
                if _contains_name(left, xname) or _contains_name(right, xname):
                    new_op = "<=" if isinstance(op, ast.Lt) else ">="
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    sub_text = source[ls:le] + f" {new_op} " + source[rs:re_]
                    candidate = source[:ls] + sub_text + source[re_:]
                    if candidate != source:
                        out.append(candidate)
    return out


def _tighten_loose_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    fn = _get_search_fn(tree)
    if fn is None:
        return []
    xname = _first_param(fn)
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Compare):
            continue
        sides = [node.left] + list(node.comparators)
        for i, op in enumerate(node.ops):
            if isinstance(op, (ast.LtE, ast.GtE)):
                left, right = sides[i], sides[i + 1]
                if _contains_name(left, xname) or _contains_name(right, xname):
                    new_op = "<" if isinstance(op, ast.LtE) else ">"
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    sub_text = source[ls:le] + f" {new_op} " + source[rs:re_]
                    candidate = source[:ls] + sub_text + source[re_:]
                    if candidate != source:
                        out.append(candidate)
    return out


# ---------------------------------------------------------------------
# Rule 6: swap operand order in a strict compare between loop var & x
# ---------------------------------------------------------------------

def _swap_operand_order(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    fn = _get_search_fn(tree)
    if fn is None:
        return []
    xname = _first_param(fn)
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.For):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        loopvar = node.target.id
        if loopvar == xname:
            continue
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Compare)
                and len(sub.ops) == 1
                and isinstance(sub.ops[0], (ast.Gt, ast.Lt))
            ):
                left, right = sub.left, sub.comparators[0]
                if (
                    isinstance(left, ast.Name)
                    and left.id == loopvar
                    and isinstance(right, ast.Name)
                    and right.id == xname
                ):
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    op_text = ">" if isinstance(sub.ops[0], ast.Gt) else "<"
                    new_text = source[rs:re_] + f" {op_text} " + source[ls:le]
                    candidate = _splice(source, sub, new_text)
                    if candidate != source:
                        out.append(candidate)
    return out


# ---------------------------------------------------------------------
# Rule 7: range(len(x) - 1) -> range(len(x))  (off-by-one bound)
# ---------------------------------------------------------------------

def _fix_range_off_by_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "range"
            and node.args
        ):
            last = node.args[-1]
            if (
                isinstance(last, ast.BinOp)
                and isinstance(last.op, ast.Sub)
                and isinstance(last.right, ast.Constant)
                and last.right.value == 1
                and isinstance(last.left, ast.Call)
                and isinstance(last.left.func, ast.Name)
                and last.left.func.id == "len"
            ):
                s, e = _span(source, last.left)
                len_text = source[s:e]
                other_text = ""
                if len(node.args) == 2:
                    s0, e0 = _span(source, node.args[0])
                    other_text = source[s0:e0] + ", "
                new_text = f"range({other_text}{len_text})"
                candidate = _splice(source, node, new_text)
                if candidate != source:
                    out.append(candidate)
    return out


# ---------------------------------------------------------------------
# Rule 8: use-before-definition of a derived sequence variable
# ---------------------------------------------------------------------

def _fix_use_before_def(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    fn = _get_search_fn(tree)
    if fn is None:
        return []
    params = [a.arg for a in fn.args.args]
    if len(params) < 2:
        return []
    seq_param = params[1]
    assigns = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    assigns.setdefault(t.id, []).append(n.lineno)
    out = []
    for n in ast.walk(fn):
        if not isinstance(n, ast.If):
            continue
        bad_id = None
        for name_node in ast.walk(n.test):
            if isinstance(name_node, ast.Name) and name_node.id not in params:
                defs = assigns.get(name_node.id)
                if defs and all(d > n.lineno for d in defs):
                    bad_id = name_node.id
                    break
        if bad_id is None:
            continue
        spans = []
        for nn in ast.walk(n):
            if isinstance(nn, ast.Name) and nn.id == bad_id:
                spans.append(_span(source, nn))
        if not spans:
            continue
        spans.sort(key=lambda sp: -sp[0])
        new_src = source
        for s, e in spans:
            new_src = new_src[:s] + seq_param + new_src[e:]
        if new_src != source:
            out.append(new_src)
    return out


# ---------------------------------------------------------------------
# Rule 9: insert a missing `if not seq: return 0` guard before the
# first place an empty sequence would crash with an IndexError.
# ---------------------------------------------------------------------

_GUARD_MARKERS_TEMPLATE = ["==()", "==[]", "len({seq})==0", "not{seq}"]


def _is_guard_stmt(stmt, source, seq_name):
    if not isinstance(stmt, ast.If):
        return False
    text = _segment(source, stmt.test).replace(" ", "")
    markers = [m.format(seq=seq_name) for m in _GUARD_MARKERS_TEMPLATE]
    return any(m in text for m in markers)


def _insert_empty_guard(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    fn = _get_search_fn(tree)
    if fn is None:
        return []
    params = [a.arg for a in fn.args.args]
    if len(params) < 2:
        return []
    seq_name = params[1]
    body = fn.body
    idx0 = 0
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        idx0 = 1
    risky_idx = None
    for i in range(idx0, len(body)):
        stmt = body[i]
        if _is_guard_stmt(stmt, source, seq_name):
            return []  # already guarded before any risk found
        if risky_idx is None:
            found = False
            for n in ast.walk(stmt):
                if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
                    idxval = _subscript_index_value(n)
                    if _is_risky_subscript(idxval):
                        found = True
                        break
            if found:
                risky_idx = i
                break
    if risky_idx is None:
        return []
    stmt = body[risky_idx]
    indent = " " * stmt.col_offset
    guard = f"if not {seq_name}:\n{indent}    return 0\n{indent}"
    s, _ = _span(source, stmt)
    candidate = source[:s] + guard + source[s:]
    if candidate != source:
        return [candidate]
    return []


# ---------------------------------------------------------------------
# Rule 10: `return None` / `return False` for the empty-sequence case
# ---------------------------------------------------------------------

def _fix_wrong_empty_return_value(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        text = _segment(source, node.test).replace(" ", "")
        markers = ["==()", "==[]", "len(seq)==0", "notseq", "seq==0"]
        if not any(m in text for m in markers):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                val = stmt.value
                is_none = val is None or (
                    isinstance(val, ast.Constant) and val.value is None
                )
                is_false = isinstance(val, ast.Constant) and val.value is False
                if is_none or is_false:
                    candidate = _splice(source, stmt, "return 0")
                    if candidate != source:
                        out.append(candidate)
    return out


# ---------------------------------------------------------------------
# Fixer
# ---------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="or_empty_precedence",
                apply=_fix_or_empty_precedence,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="append_missing_return_len_seq",
                apply=_append_return_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="final_return_loopvar_to_len",
                apply=_fix_final_return_loopvar,
                symptoms=("wrong",),
            ),
            Rule(
                name="relax_strict_comparison_with_x",
                apply=_relax_strict_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="tighten_loose_comparison_with_x",
                apply=_tighten_loose_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="swap_compare_operand_order",
                apply=_swap_operand_order,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_len_minus_one_off_by_one",
                apply=_fix_range_off_by_one,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="use_before_def_sequence_var",
                apply=_fix_use_before_def,
                symptoms=("err:NameError", "err:UnboundLocalError"),
            ),
            Rule(
                name="insert_missing_empty_guard",
                apply=_insert_empty_guard,
                symptoms=("err:IndexError", "wrong"),
            ),
            Rule(
                name="fix_wrong_empty_return_value",
                apply=_fix_wrong_empty_return_value,
                symptoms=("wrong",),
            ),
        ]