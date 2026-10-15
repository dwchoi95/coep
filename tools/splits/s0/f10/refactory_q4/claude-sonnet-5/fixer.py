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


def _subscript_index(node):
    sl = node.slice
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        sl = sl.value
    if isinstance(sl, ast.Constant):
        return sl.value
    if hasattr(ast, "Num") and isinstance(sl, ast.Num):
        return sl.n
    return None


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Rule 1: the accumulator list used in `.append()` doesn't match the Name
# used in the final `return` statement (typo / undefined variable).
def _fix_return_name_mismatch(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if not any(isinstance(n, ast.While) for n in ast.walk(fn)):
            continue
        append_names = [n.func.value.id for n in ast.walk(fn)
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and n.func.attr == "append" and isinstance(n.func.value, ast.Name)]
        if not append_names:
            continue
        majority = max(set(append_names), key=append_names.count)
        for n in ast.walk(fn):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id != majority:
                out.append(_splice(source, n.value, majority))
    return out


# ---------------------------------------------------------------------------
# Rule 2: `X.remove(...)` where X is not the list being iterated by the
# enclosing `while <list>:` loop (undefined/wrong name).
def _fix_remove_target_mismatch(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for wn in ast.walk(tree):
        if not isinstance(wn, ast.While):
            continue
        if not isinstance(wn.test, ast.Name):
            continue
        correct = wn.test.id
        for n in ast.walk(wn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "remove" \
               and isinstance(n.func.value, ast.Name) and n.func.value.id != correct:
                out.append(_splice(source, n.func.value, correct))
    return out


# ---------------------------------------------------------------------------
# Rule 3: after a for-loop that tracks the extremum element in a separate
# variable, later statements mistakenly use the raw loop variable instead.
def _fix_loopvar_instead_of_tracked(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for wn in ast.walk(fn):
            if not isinstance(wn, ast.While):
                continue
            body = wn.body
            for idx, stmt in enumerate(body):
                if not isinstance(stmt, ast.For) or not isinstance(stmt.target, ast.Name):
                    continue
                loopvar = stmt.target.id
                tracked = None
                for inner in stmt.body:
                    if isinstance(inner, ast.If) and len(inner.body) == 1:
                        a = inner.body[0]
                        if isinstance(a, ast.Assign) and len(a.targets) == 1 \
                           and isinstance(a.targets[0], ast.Name) and isinstance(a.value, ast.Name) \
                           and a.value.id == loopvar:
                            tracked = a.targets[0].id
                if tracked is None or tracked == loopvar:
                    continue
                for later in body[idx + 1:]:
                    for n in ast.walk(later):
                        if isinstance(n, ast.Name) and n.id == loopvar and isinstance(n.ctx, ast.Load):
                            out.append(_splice(source, n, tracked))
    return out


# ---------------------------------------------------------------------------
# Rule 4: extremum-tracking comparison uses `<` (finds the minimum) when the
# task needs the maximum (oldest person first).
def _flip_extremum_lt_to_gt(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for forn in ast.walk(fn):
            if not isinstance(forn, ast.For):
                continue
            for inner in forn.body:
                if not (isinstance(inner, ast.If) and len(inner.body) == 1):
                    continue
                a = inner.body[0]
                if not (isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Name)):
                    continue
                trackvar = a.targets[0].id
                cmp = inner.test
                if not (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Lt)):
                    continue
                names_in_cmp = [n.id for n in ast.walk(cmp) if isinstance(n, ast.Name)]
                if trackvar not in names_in_cmp:
                    continue
                ls, le = _span(source, cmp.left)
                rs, re_ = _span(source, cmp.comparators[0])
                new_cmp = source[ls:le] + " > " + source[rs:re_]
                out.append(_splice(source, cmp, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule 5: comparison between whole tuples instead of their age field.
def _add_missing_subscript_compare(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for forn in ast.walk(fn):
            if not isinstance(forn, ast.For):
                continue
            for inner in forn.body:
                if not (isinstance(inner, ast.If) and len(inner.body) == 1):
                    continue
                a = inner.body[0]
                if not (isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Name)):
                    continue
                cmp = inner.test
                if not (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1
                        and isinstance(cmp.left, ast.Name) and len(cmp.comparators) == 1
                        and isinstance(cmp.comparators[0], ast.Name)):
                    continue
                op = cmp.ops[0]
                opstr = {ast.Gt: ">", ast.Lt: "<", ast.GtE: ">=", ast.LtE: "<="}.get(type(op))
                if opstr is None:
                    continue
                ls, le = _span(source, cmp.left)
                rs, re_ = _span(source, cmp.comparators[0])
                new_cmp = source[ls:le] + "[1] " + opstr + " " + source[rs:re_] + "[1]"
                out.append(_splice(source, cmp, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule 6: a `return` statement accidentally placed as the last line inside
# the `while` loop body, so only one iteration runs.
def _dedent_return_from_while(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for wn in ast.walk(tree):
        if not isinstance(wn, ast.While) or not wn.body:
            continue
        last = wn.body[-1]
        if not isinstance(last, ast.Return) or last.lineno != last.end_lineno:
            continue
        lines = source.splitlines(keepends=True)
        idx = last.lineno - 1
        if idx >= len(lines):
            continue
        stmt_text = lines[idx].strip("\n").lstrip()
        indent = " " * wn.col_offset
        new_lines = lines[:idx] + lines[idx + 1:]
        new_lines.insert(idx, indent + stmt_text + "\n")
        out.append("".join(new_lines))
    return out


# ---------------------------------------------------------------------------
# Rule 7: an unused `X = []` initializer whose name doesn't match the
# accumulator actually referenced by `.append()`/`return` (typo in init).
def _fix_unused_accumulator_init_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        all_names = [n.id for n in ast.walk(fn) if isinstance(n, ast.Name)]
        append_names = [n.func.value.id for n in ast.walk(fn)
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and n.func.attr == "append" and isinstance(n.func.value, ast.Name)]
        if not append_names:
            continue
        target_name = max(set(append_names), key=append_names.count)
        assigned_names = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        assigned_names.add(t.id)
        if target_name in assigned_names:
            continue
        for n in fn.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
               and isinstance(n.value, ast.List) and len(n.value.elts) == 0:
                name = n.targets[0].id
                if name == target_name:
                    continue
                if all_names.count(name) == 1:
                    out.append(_splice(source, n.targets[0], target_name))
    return out


# ---------------------------------------------------------------------------
# Rule 8: `acc += (x,)` / `acc += x` used instead of `acc.append(x)`.
def _fix_augassign_append(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) and isinstance(n.target, ast.Name):
            val = n.value
            inner = None
            if isinstance(val, ast.Tuple) and len(val.elts) == 1:
                inner = val.elts[0]
            elif isinstance(val, ast.Name):
                inner = val
            if inner is None:
                continue
            is_, ie = _span(source, inner)
            new_stmt = f"{n.target.id}.append({source[is_:ie]})"
            out.append(_splice(source, n, new_stmt))
    return out


# ---------------------------------------------------------------------------
# Rule 9: the accumulator is built but the function never returns it.
def _add_missing_return_statement(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if any(isinstance(n, ast.Return) for n in ast.walk(fn)):
            continue
        append_names = [n.func.value.id for n in ast.walk(fn)
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and n.func.attr == "append" and isinstance(n.func.value, ast.Name)]
        aug_names = [n.target.id for n in ast.walk(fn)
                     if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)]
        candidates = append_names + aug_names
        if not candidates or not fn.body:
            continue
        name = max(set(candidates), key=candidates.count)
        indent = " " * fn.body[0].col_offset
        s, e = _span(source, fn)
        out.append(source[:e] + "\n" + indent + f"return {name}" + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 10: a selection pass (find extremum, remove, append) with no
# enclosing `while` loop, so only one element ever gets sorted.
def _wrap_bare_selection_pass_in_while(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if any(isinstance(n, ast.While) for n in ast.walk(fn)):
            continue
        if not fn.args.args:
            continue
        param = fn.args.args[0].arg
        body = fn.body
        start_idx = None
        for i, st in enumerate(body):
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                val = st.value
                if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) and val.value.id == param:
                    if _subscript_index(val) == 0:
                        start_idx = i
                        break
        if start_idx is None:
            continue
        has_for = False
        end_idx = None
        for j in range(start_idx, len(body)):
            st = body[j]
            if isinstance(st, ast.Return):
                end_idx = j - 1
                break
            if isinstance(st, ast.For):
                has_for = True
        if end_idx is None or not has_for or end_idx < start_idx:
            continue
        has_remove = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "remove"
            for j in range(start_idx, end_idx + 1) for n in ast.walk(body[j])
        )
        if not has_remove:
            continue
        start_stmt = body[start_idx]
        end_stmt = body[end_idx]
        lines = source.splitlines(keepends=True)
        s_line = start_stmt.lineno - 1
        e_line = end_stmt.end_lineno - 1
        indent = " " * start_stmt.col_offset
        new_block = [indent + f"while {param}:\n"]
        for ln in lines[s_line:e_line + 1]:
            new_block.append("    " + ln)
        new_lines = lines[:s_line] + new_block + lines[e_line + 1:]
        out.append("".join(new_lines))
    return out


# ---------------------------------------------------------------------------
# Rule 11: single-pass bubble-sort (for-loop with a compare+swap) that never
# repeats, so the list only gets partially sorted.
def _wrap_bubble_single_pass_in_while(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if any(isinstance(n, ast.While) for n in ast.walk(fn)):
            continue
        for st in fn.body:
            if not isinstance(st, ast.For):
                continue
            if not (isinstance(st.iter, ast.Call) and isinstance(st.iter.func, ast.Name) and st.iter.func.id == "range"):
                continue
            if len(st.body) != 1 or not isinstance(st.body[0], ast.If):
                continue
            ifn = st.body[0]
            if not ifn.body:
                continue
            last_stmt = ifn.body[-1]
            lines = source.splitlines(keepends=True)
            for_start = st.lineno - 1
            for_end = st.end_lineno - 1
            indent = " " * st.col_offset
            swap_indent = " " * ifn.body[0].col_offset
            insert_after_line = last_stmt.end_lineno - 1
            new_block_lines = []
            for i in range(for_start, for_end + 1):
                new_block_lines.append(lines[i])
                if i == insert_after_line:
                    new_block_lines.append(swap_indent + "swap = True\n")
            wrapped = [indent + "swap = True\n", indent + "while swap:\n", indent + "    swap = False\n"]
            for ln in new_block_lines:
                wrapped.append("    " + ln)
            new_lines = lines[:for_start] + wrapped + lines[for_end + 1:]
            out.append("".join(new_lines))
    return out


# ---------------------------------------------------------------------------
# Rule 12: bubble-sort swap condition compares with `>` (ascending) when the
# task needs descending order.
def _flip_bubble_gt_to_lt(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for forn in ast.walk(tree):
        if not isinstance(forn, ast.For):
            continue
        for ifn in ast.walk(forn):
            if not isinstance(ifn, ast.If):
                continue
            cmp = ifn.test
            if not (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Gt)):
                continue
            subs = []
            for n in ast.walk(ifn):
                if isinstance(n, ast.Assign):
                    for t in n.targets:
                        for sub in ast.walk(t):
                            if isinstance(sub, ast.Subscript):
                                subs.append(sub)
            if len(subs) < 2:
                continue
            ls, le = _span(source, cmp.left)
            rs, re_ = _span(source, cmp.comparators[0])
            new_cmp = source[ls:le] + " < " + source[rs:re_]
            out.append(_splice(source, cmp, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule 13: swap only the age field (`lst[i][1], lst[j][1] = ...`) instead of
# swapping the whole tuples, which corrupts the gender field.
def _fix_partial_tuple_swap(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign):
            continue
        if len(n.targets) != 1 or not isinstance(n.targets[0], ast.Tuple):
            continue
        tgt = n.targets[0]
        val = n.value
        if not isinstance(val, ast.Tuple) or len(tgt.elts) != 2 or len(val.elts) != 2:
            continue

        def _is_double_sub(x):
            return isinstance(x, ast.Subscript) and isinstance(x.value, ast.Subscript)

        if not all(_is_double_sub(e) for e in tgt.elts):
            continue
        a_outer = tgt.elts[0].value
        b_outer = tgt.elts[1].value
        as_, ae = _span(source, a_outer)
        bs, be = _span(source, b_outer)
        new_stmt = f"{source[as_:ae]}, {source[bs:be]} = {source[bs:be]}, {source[as_:ae]}"
        out.append(_splice(source, n, new_stmt))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="fix_return_name_mismatch",
                 apply=_fix_return_name_mismatch,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="fix_remove_target_mismatch",
                 apply=_fix_remove_target_mismatch,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="fix_loopvar_instead_of_tracked",
                 apply=_fix_loopvar_instead_of_tracked,
                 symptoms=("wrong",)),
            Rule(name="flip_extremum_lt_to_gt",
                 apply=_flip_extremum_lt_to_gt,
                 symptoms=("wrong",)),
            Rule(name="add_missing_subscript_compare",
                 apply=_add_missing_subscript_compare,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="dedent_return_from_while",
                 apply=_dedent_return_from_while,
                 symptoms=("wrong",)),
            Rule(name="fix_unused_accumulator_init_name",
                 apply=_fix_unused_accumulator_init_name,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="fix_augassign_append",
                 apply=_fix_augassign_append,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="add_missing_return_statement",
                 apply=_add_missing_return_statement,
                 symptoms=("wrong",)),
            Rule(name="wrap_bare_selection_pass_in_while",
                 apply=_wrap_bare_selection_pass_in_while,
                 symptoms=("wrong",)),
            Rule(name="wrap_bubble_single_pass_in_while",
                 apply=_wrap_bubble_single_pass_in_while,
                 symptoms=("wrong",)),
            Rule(name="flip_bubble_gt_to_lt",
                 apply=_flip_bubble_gt_to_lt,
                 symptoms=("wrong",)),
            Rule(name="fix_partial_tuple_swap",
                 apply=_fix_partial_tuple_swap,
                 symptoms=("wrong",)),
        ]