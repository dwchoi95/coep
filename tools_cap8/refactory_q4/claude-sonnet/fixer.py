import ast
import builtins

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
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Rule 1: comparing a list parameter against an empty tuple instead of []
# ---------------------------------------------------------------------------
def _fix_empty_tuple_check(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Eq):
            comparator = node.comparators[0]
            if isinstance(comparator, ast.Tuple) and len(comparator.elts) == 0:
                out.append(_splice(source, comparator, "[]"))
    return out


# ---------------------------------------------------------------------------
# Rule 2: using min() instead of max() to pick the "largest" element
# ---------------------------------------------------------------------------
def _fix_min_should_be_max(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "min":
            spans.append(_span(source, node.func))
    if not spans:
        return []
    new_source = source
    for s, e in sorted(spans, key=lambda x: -x[0]):
        new_source = new_source[:s] + "max" + new_source[e:]
    return [new_source]


# ---------------------------------------------------------------------------
# Rule 3: popping from the wrong end of a list (merge step of merge sort)
# ---------------------------------------------------------------------------
def _fix_pop_wrong_end(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "pop" and len(node.args) == 0 \
           and len(node.keywords) == 0:
            spans.append(_span(source, node))
    if not spans:
        return []
    new_source = source
    for s, e in sorted(spans, key=lambda x: -x[0]):
        segment = new_source[s:e]
        if segment.endswith("()"):
            new_segment = segment[:-1] + "0)"
            new_source = new_source[:s] + new_segment + new_source[e:]
    if new_source == source:
        return []
    return [new_source]


# ---------------------------------------------------------------------------
# Rule 4: index not reset to 0 after mutating the list in a while-loop
#          (element gets moved to the end but the scan pointer isn't reset,
#           so later comparisons are skipped)
# ---------------------------------------------------------------------------
def _fix_missing_index_reset(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        incr_var = None
        for stmt in node.orelse:
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) \
               and isinstance(stmt.op, ast.Add):
                incr_var = stmt.target.id
        if incr_var is None:
            continue
        already_reset = any(
            isinstance(s, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == incr_var for t in s.targets)
            for s in node.body
        )
        if already_reset:
            continue
        has_mutation = any(isinstance(s, ast.Delete) for s in node.body)
        if not has_mutation:
            continue
        last_stmt = node.body[-1]
        s, e = _span(source, last_stmt)
        indent = " " * last_stmt.col_offset
        insertion = "\n" + indent + f"{incr_var} = 0"
        out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 5: use of an undefined variable name (typo) where the function
#          parameter was clearly meant
# ---------------------------------------------------------------------------
def _fix_undefined_var_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    builtin_names = set(dir(builtins))
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        params = {a.arg for a in func.args.args}
        if len(params) != 1:
            continue
        assigned = set(params)
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                assigned.add(n.id)
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                assigned.add(n.target.id)
        loads = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in assigned and n.id not in builtin_names \
                   and n.id not in func_names:
                    loads.add(n.id)
        if len(loads) != 1:
            continue
        bad = next(iter(loads))
        good = next(iter(params))
        edits = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and n.id == bad and isinstance(n.ctx, ast.Load):
                edits.append(_span(source, n))
        if not edits:
            continue
        new_source = source
        for s, e in sorted(edits, key=lambda x: -x[0]):
            new_source = new_source[:s] + good + new_source[e:]
        out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 6: sort built in ascending order (a ">"-based swap/selection) but the
#          result is never reversed before being returned
# ---------------------------------------------------------------------------
def _fix_missing_reverse_on_ascending(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    has_gt = any(
        isinstance(n, ast.Compare) and any(isinstance(op, ast.Gt) for op in n.ops)
        for n in ast.walk(tree)
    )
    if not has_gt:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None \
           and isinstance(node.value, ast.Name):
            val = node.value
            s, e = _span(source, val)
            appended = source[s:e] + "[::-1]"
            out.append(source[:s] + appended + source[e:])

            rs, _ = _span(source, node)
            indent = " " * node.col_offset
            insertion = f"{val.id}.reverse()\n{indent}"
            out.append(source[:rs] + insertion + source[rs:])
    return out


# ---------------------------------------------------------------------------
# Rule 7: generic comparison direction flip (Lt <-> Gt) — cheap fallback
# ---------------------------------------------------------------------------
def _flip_compare_direction(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            new_op_text = None
            if isinstance(op, ast.Lt):
                new_op_text = ">"
            elif isinstance(op, ast.Gt):
                new_op_text = "<"
            if new_op_text is None:
                continue
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + f" {new_op_text} " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="empty_tuple_vs_empty_list_check",
                apply=_fix_empty_tuple_check,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="min_should_be_max",
                apply=_fix_min_should_be_max,
                symptoms=("wrong",),
            ),
            Rule(
                name="pop_wrong_end_of_list",
                apply=_fix_pop_wrong_end,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_index_reset_after_mutation",
                apply=_fix_missing_index_reset,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="undefined_variable_typo",
                apply=_fix_undefined_var_typo,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="missing_reverse_on_ascending_sort",
                apply=_fix_missing_reverse_on_ascending,
                symptoms=("wrong",),
            ),
            Rule(
                name="flip_compare_direction",
                apply=_flip_compare_direction,
                symptoms=("wrong",),
            ),
        ]