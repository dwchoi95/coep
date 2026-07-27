import ast
import difflib
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


def _multi_splice(source, edits):
    """edits: list of (start, end, new_text). Applies right-to-left."""
    edits = sorted(edits, key=lambda x: x[0], reverse=True)
    out = source
    for s, e, t in edits:
        out = out[:s] + t + out[e:]
    return out


def _get_slice_expr(sl):
    if isinstance(sl, ast.Index):
        return sl.value
    return sl


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _fix_while_bound(source):
    """Fix off-by-one bounds in while loop tests comparing to k or 0 (<=/>= -> </>)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            test = node.test
            op = test.ops[0]
            left = test.left
            right = test.comparators[0]
            if isinstance(op, ast.LtE):
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_test = source[ls:le] + " < " + source[rs:re_]
                cand = _splice(source, test, new_test)
                if cand != source:
                    out.append(cand)
            elif isinstance(op, ast.GtE) and isinstance(right, ast.Constant) and right.value == 0:
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_test = source[ls:le] + " > " + source[rs:re_]
                cand = _splice(source, test, new_test)
                if cand != source:
                    out.append(cand)
    return out


def _fix_slice_bound(source):
    """Fix wrong slice upper bound: [:k-1] -> [:k], or a stray literal -> [:k]."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if len(params) < 2:
            continue
        k_name = params[1]
        for node in ast.walk(func):
            if isinstance(node, ast.Subscript):
                sl = _get_slice_expr(node.slice)
                if isinstance(sl, ast.Slice) and sl.upper is not None:
                    upper = sl.upper
                    if isinstance(upper, ast.BinOp) and isinstance(upper.op, ast.Sub) \
                       and isinstance(upper.left, ast.Name) and upper.left.id == k_name:
                        cand = _splice(source, upper, k_name)
                        if cand != source:
                            out.append(cand)
                    elif isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                        cand = _splice(source, upper, k_name)
                        if cand != source:
                            out.append(cand)
    return out


def _fix_return_name(source):
    """Fix return statement referencing wrong accumulator variable name."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        list_names = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        list_names.add(t.id)
        if len(list_names) != 1:
            continue
        good = next(iter(list_names))
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and node.value is not None:
                val = node.value
                target = val.value if isinstance(val, ast.Subscript) else val
                if isinstance(target, ast.Name) and target.id != good:
                    cand = _splice(source, target, good)
                    if cand != source:
                        out.append(cand)
    return out


def _fix_bracket_call(source):
    """Fix using [] instead of () for .append/.remove/.extend/.pop/.insert calls."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
           and node.value.attr in ('append', 'remove', 'extend', 'insert', 'pop'):
            idx = _get_slice_expr(node.slice)
            if isinstance(idx, ast.Slice):
                continue
            vs, ve = _span(source, node.value)
            iss, ie = _span(source, idx)
            new_text = source[vs:ve] + "(" + source[iss:ie] + ")"
            s, e = _span(source, node)
            edits.append((s, e, new_text))
    if not edits:
        return []
    cand = _multi_splice(source, edits)
    if cand == source:
        return []
    return [cand]


def _fix_index_in_condition(source):
    """Fix `if i == max(lst)` (loop index compared directly) -> `if lst[i] == max(lst)`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loop_var = node.target.id
                iter_node = node.iter
                list_name = None
                if isinstance(iter_node, ast.Call) and isinstance(iter_node.func, ast.Name) \
                   and iter_node.func.id == 'range' and len(iter_node.args) == 1:
                    arg0 = iter_node.args[0]
                    if isinstance(arg0, ast.Call) and isinstance(arg0.func, ast.Name) \
                       and arg0.func.id == 'len' and len(arg0.args) == 1 \
                       and isinstance(arg0.args[0], ast.Name):
                        list_name = arg0.args[0].id
                if list_name is None:
                    continue
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Compare) and len(inner.ops) == 1 \
                       and isinstance(inner.ops[0], ast.Eq):
                        left = inner.left
                        if isinstance(left, ast.Name) and left.id == loop_var:
                            new_left = f"{list_name}[{loop_var}]"
                            cand = _splice(source, left, new_left)
                            if cand != source:
                                out.append(cand)
    return out


def _fix_extend_arg(source):
    """Fix `.extend([i])` -> `.extend([lst[i]])` when i is an index variable."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
               and node.func.attr == 'extend' and len(node.args) == 1 \
               and isinstance(node.args[0], ast.List) and len(node.args[0].elts) == 1:
                elt = node.args[0].elts[0]
                if isinstance(elt, ast.Name):
                    base_obj = node.func.value
                    if isinstance(base_obj, ast.Name):
                        new_elt = f"{base_obj.id}[{elt.id}]"
                        cand = _splice(source, elt, new_elt)
                        if cand != source:
                            out.append(cand)
    return out


def _fix_k_zero_guard(source):
    """Add `or k == 0` guard when checking for an empty input list."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if len(params) < 2:
            continue
        k_name = params[1]
        for node in ast.walk(func):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                test = node.test
                left = test.left
                right = test.comparators[0]
                if isinstance(test.ops[0], ast.Eq) and isinstance(right, ast.List) and len(right.elts) == 0:
                    ts, te = _span(source, test)
                    cond_src = source[ts:te]
                    if k_name not in cond_src:
                        new_test = cond_src + f" or {k_name} == 0"
                        cand = _splice(source, test, new_test)
                        if cand != source:
                            out.append(cand)
    return out


def _is_append_max_stmt(stmt):
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and call.func.attr in ('append', 'extend'):
            for a in call.args:
                if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id == 'max':
                    return True
                if isinstance(a, ast.List):
                    for e in a.elts:
                        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == 'max':
                            return True
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.value, ast.List):
        for e in stmt.value.elts:
            if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == 'max':
                return True
    return False


def _is_remove_call(stmt):
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and call.func.attr == 'remove':
            return True
    return False


def _fix_missing_remove(source):
    """Insert lst.remove(max(lst)) after an append(max(lst)) with no removal in the loop."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        lst_name = params[0]
        for node in ast.walk(func):
            if isinstance(node, ast.While):
                body = node.body
                append_stmt = None
                has_remove = False
                for stmt in body:
                    if _is_append_max_stmt(stmt):
                        append_stmt = stmt
                    if _is_remove_call(stmt):
                        has_remove = True
                if append_stmt is not None and not has_remove:
                    s, e = _span(source, append_stmt)
                    indent = " " * append_stmt.col_offset
                    insertion = source[s:e] + "\n" + indent + f"{lst_name}.remove(max({lst_name}))"
                    cand = _splice(source, append_stmt, insertion)
                    if cand != source:
                        out.append(cand)
    return out


def _collect_defined_names(func):
    defined = set(a.arg for a in func.args.args)
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defined.add(t.id)
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)
        if isinstance(node, ast.FunctionDef):
            defined.add(node.name)
    return defined


def _fix_typo_name(source):
    """Fix an undefined-name typo by replacing it with the closest defined name."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    builtin_names = set(dir(builtins))
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = _collect_defined_names(func)
        used_loads = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in defined and node.id not in builtin_names:
                    used_loads.add(node.id)
        for bad in used_loads:
            matches = difflib.get_close_matches(bad, list(defined), n=1, cutoff=0.6)
            if not matches:
                continue
            good = matches[0]
            edits = []
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and node.id == bad and isinstance(node.ctx, ast.Load):
                    s, e = _span(source, node)
                    edits.append((s, e, good))
            if edits:
                cand = _multi_splice(source, edits)
                if cand != source:
                    out.append(cand)
    return out


def _fix_missing_break(source):
    """Insert `break` at the end of an if-block inside a for loop that pops a match, when no break exists."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for fnode in ast.walk(func):
            if not isinstance(fnode, ast.For):
                continue
            for inner in fnode.body:
                if isinstance(inner, ast.If):
                    body = inner.body
                    has_pop = any(
                        isinstance(s, (ast.Expr,))
                        and isinstance(getattr(s, 'value', None), ast.Call)
                        and isinstance(s.value.func, ast.Attribute)
                        and s.value.func.attr == 'pop'
                        or (isinstance(s, ast.Assign) and isinstance(s.value, ast.Call)
                            and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == 'pop')
                        or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                            and any(isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)
                                    and a.func.attr == 'pop' for a in s.value.args))
                        for s in body
                    )
                    has_break = any(isinstance(s, ast.Break) for s in body)
                    if has_pop and not has_break and body:
                        last = body[-1]
                        s, e = _span(source, last)
                        indent = " " * last.col_offset
                        insertion = source[s:e] + "\n" + indent + "break"
                        cand = _splice(source, last, insertion)
                        if cand != source:
                            out.append(cand)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="while_bound_off_by_one_k",
                apply=_fix_while_bound,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="slice_bound_should_be_k",
                apply=_fix_slice_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_wrong_accumulator_name",
                apply=_fix_return_name,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="bracket_call_should_be_paren",
                apply=_fix_bracket_call,
                symptoms=("err:TypeError",),
            ),
            Rule(
                name="index_compared_directly_instead_of_indexed",
                apply=_fix_index_in_condition,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="extend_arg_should_be_indexed",
                apply=_fix_extend_arg,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="missing_k_zero_guard",
                apply=_fix_k_zero_guard,
                symptoms=("wrong", "err:ValueError"),
            ),
            Rule(
                name="missing_remove_after_append",
                apply=_fix_missing_remove,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="undefined_name_typo",
                apply=_fix_typo_name,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="missing_break_after_pop_match",
                apply=_fix_missing_break,
                symptoms=("wrong", "timeout", "err:IndexError"),
            ),
        ]