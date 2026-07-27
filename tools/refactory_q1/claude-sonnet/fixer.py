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


def _indent_of(source, node):
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[: len(line) - len(line.lstrip())]


def _parents(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _dedup(source, candidates):
    out = []
    seen = set()
    for c in candidates:
        if c == source:
            continue
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _none_to_zero(source):
    """Replace `return None` with `return 0`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.Constant)
            and node.value.value is None
        ):
            out.append(_splice(source, node, "return 0"))
    return _dedup(source, out)


def _assign_none_to_zero(source):
    """Replace `name = None` initializers with `name = 0`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and node.value.value is None
        ):
            out.append(_splice(source, node.value, "0"))
    return _dedup(source, out)


def _fix_seq_truthiness(source):
    """Fix `seq == () or []` style truthiness bugs to `seq == () or seq == []`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            left_name = None
            for v in node.values:
                if isinstance(v, ast.Compare) and isinstance(v.left, ast.Name):
                    left_name = v.left.id
            if left_name is None:
                continue
            changed = False
            texts = []
            for v in node.values:
                if isinstance(v, (ast.List, ast.Tuple)):
                    s, e = _span(source, v)
                    texts.append(f"{left_name} == {source[s:e]}")
                    changed = True
                else:
                    s, e = _span(source, v)
                    texts.append(source[s:e])
            if changed:
                out.append(_splice(source, node, " or ".join(texts)))
    return _dedup(source, out)


def _generalize_empty_check(source):
    """Replace `seq == ()` / `seq == []` sole checks with `len(seq) == 0`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
        ):
            left, right = node.left, node.comparators[0]
            if (
                isinstance(right, (ast.Tuple, ast.List))
                and len(right.elts) == 0
                and isinstance(left, ast.Name)
            ):
                out.append(_splice(source, node, f"len({left.id}) == 0"))
    return _dedup(source, out)


def _toggle_compare_strictness(source):
    """Toggle strict/non-strict comparisons involving `x` (boundary off-by-ones)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    swap = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt}
    op_text = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and type(node.ops[0]) in swap
        ):
            involves_x = any(
                isinstance(n, ast.Name) and n.id == "x" for n in ast.walk(node)
            )
            if not involves_x:
                continue
            new_op = swap[type(node.ops[0])]
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " " + op_text[new_op] + " " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return _dedup(source, out)


def _remove_off_by_one(source):
    """Fix `return count - 1` style off-by-one to `return count`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.BinOp)
            and isinstance(node.value.op, ast.Sub)
        ):
            right = node.value.right
            if isinstance(right, ast.Constant) and right.value == 1:
                left = node.value.left
                ls, le = _span(source, left)
                out.append(_splice(source, node.value, source[ls:le]))
    return _dedup(source, out)


def _bare_return_to_break(source):
    """Replace a bare `return` inside a loop with `break`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    parents = _parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is None:
            cur = parents.get(node)
            in_loop = False
            while cur is not None and not isinstance(cur, ast.FunctionDef):
                if isinstance(cur, (ast.For, ast.While)):
                    in_loop = True
                    break
                cur = parents.get(cur)
            if in_loop:
                out.append(_splice(source, node, "break"))
    return _dedup(source, out)


def _dedent_trailing_return_via_else(source):
    """Fix a return that is wrongly indented as part of the loop body (runs once
    only) by attaching it via a `for ... else:` clause instead."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for stmt in ast.walk(func):
            if isinstance(stmt, ast.For) and len(stmt.body) >= 2:
                last = stmt.body[-1]
                prev = stmt.body[-2]
                if isinstance(last, ast.Return) and isinstance(prev, ast.If):
                    for_indent = _indent_of(source, stmt)
                    ls, _ = _span(source, last)
                    line_start = source.rfind("\n", 0, ls) + 1
                    insertion = for_indent + "else:\n"
                    out.append(source[:line_start] + insertion + source[line_start:])
    return _dedup(source, out)


def _init_missing_var(source):
    """Insert a `name = 0` initializer before a for-loop when a variable that is
    only assigned inside the loop (or is the loop counter) is used afterward,
    guarding against the empty-sequence case."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        body = func.body
        for i, stmt in enumerate(body):
            if not isinstance(stmt, ast.For):
                continue
            names = set()
            tgt = stmt.target
            if isinstance(tgt, ast.Name):
                names.add(tgt.id)
            elif isinstance(tgt, ast.Tuple):
                for e in tgt.elts:
                    if isinstance(e, ast.Name):
                        names.add(e.id)
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            names.add(t.id)
            for later in body[i + 1:]:
                for node in ast.walk(later):
                    if (
                        isinstance(node, ast.Name)
                        and node.id in names
                        and isinstance(node.ctx, ast.Load)
                    ):
                        already = any(
                            isinstance(s, ast.Assign)
                            and any(
                                isinstance(t, ast.Name) and t.id == node.id
                                for t in s.targets
                            )
                            for s in body[:i]
                        )
                        if not already:
                            indent = _indent_of(source, stmt)
                            s_off, _ = _span(source, stmt)
                            insertion = f"{node.id} = 0\n{indent}"
                            out.append(source[:s_off] + insertion + source[s_off:])
    return _dedup(source, out)


def _add_helper_call(source):
    """Add a missing call to a nested helper function at the end of the outer
    function (recursive helper pattern defined but never invoked)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for outer in ast.walk(tree):
        if not isinstance(outer, ast.FunctionDef):
            continue
        for stmt in outer.body:
            if isinstance(stmt, ast.FunctionDef):
                inner = stmt
                calls_inner = any(
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == inner.name
                    for node in outer.body
                    for n in ast.walk(node)
                )
                if calls_inner:
                    continue
                args = [a.arg for a in inner.args.args]
                call_args = ", ".join(args)
                indent = _indent_of(source, outer.body[0])
                _, e = _span(source, outer)
                insertion = f"\n{indent}return {inner.name}({call_args})"
                out.append(source[:e] + insertion + source[e:])
    return _dedup(source, out)


def _append_default_return(source):
    """If a function ends with a bare for/while loop with no fallback return,
    append one (two variants: `len(seq)` and `0`)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, (ast.For, ast.While)):
            indent = _indent_of(source, last)
            _, e = _span(source, func)
            out.append(source[:e] + f"\n{indent}return len(seq)" + source[e:])
            out.append(source[:e] + f"\n{indent}return 0" + source[e:])
    return _dedup(source, out)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="return_none_to_zero",
                apply=_none_to_zero,
                symptoms=("wrong",),
            ),
            Rule(
                name="assign_none_to_zero",
                apply=_assign_none_to_zero,
                symptoms=("wrong",),
            ),
            Rule(
                name="seq_truthiness_fix",
                apply=_fix_seq_truthiness,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="generalize_empty_check",
                apply=_generalize_empty_check,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="toggle_boundary_compare_strictness",
                apply=_toggle_compare_strictness,
                symptoms=("wrong",),
            ),
            Rule(
                name="remove_off_by_one_subtraction",
                apply=_remove_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_return_to_break",
                apply=_bare_return_to_break,
                symptoms=("wrong",),
            ),
            Rule(
                name="dedent_trailing_return_via_else",
                apply=_dedent_trailing_return_via_else,
                symptoms=("wrong",),
            ),
            Rule(
                name="init_missing_var_before_loop",
                apply=_init_missing_var,
                symptoms=("err:NameError", "err:UnboundLocalError", "wrong"),
            ),
            Rule(
                name="add_missing_helper_call",
                apply=_add_helper_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="append_default_return_after_loop",
                apply=_append_default_return,
                symptoms=("wrong",),
            ),
        ]