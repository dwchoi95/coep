import ast


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


def _get_func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _fix_free_var_param_mismatch(source):
    """
    Fixes the misconception where a function's parameter is named
    'day' or 'date', but the body refers to the *other* one of those
    two names (an undefined free variable), e.g. def unique_day(date, ...)
    but body checks `birthday[1] == day`.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for fname in ("unique_day",):
        func = _get_func(tree, fname)
        if func is None or not func.args.args:
            continue
        param_name = func.args.args[0].arg
        candidates = {"day", "date"}
        if param_name not in candidates:
            continue
        other_name = (candidates - {param_name}).pop()

        # collect local names bound inside the function (assignments, for-targets, args)
        bound_names = {a.arg for a in func.args.args}
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                bound_names.add(n.id)
            if isinstance(n, ast.arg):
                bound_names.add(n.arg)

        if other_name in bound_names:
            continue

        targets = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and n.id == other_name and isinstance(n.ctx, ast.Load):
                targets.append(n)

        if not targets:
            continue

        targets.sort(key=lambda n: (n.lineno, n.col_offset), reverse=True)
        new_source = source
        for n in targets:
            new_source = _splice(new_source, n, param_name)
        out.append(new_source)

    return out


def _has_false_return(func):
    for n in ast.walk(func):
        if isinstance(n, ast.Return) and n.value is not None:
            val = n.value
            if isinstance(val, ast.Constant) and val.value is False:
                return True
            if isinstance(val, ast.NameConstant) and val.value is False:  # py<3.8 compat
                return True
    return False


def _fix_missing_return_false(source):
    """
    Fixes the misconception where a boolean-returning function only
    returns True inside an `if` block and falls through (implicit None)
    otherwise, instead of returning False.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for fname in ("unique_month", "unique_day"):
        func = _get_func(tree, fname)
        if func is None or not func.body:
            continue
        if _has_false_return(func):
            continue
        last_stmt = func.body[-1]
        if not isinstance(last_stmt, ast.If):
            continue
        if last_stmt.orelse:
            continue

        indent = " " * last_stmt.col_offset
        s, e = _span(source, last_stmt)
        insertion = "\n" + indent + "return False"
        new_source = source[:e] + insertion + source[e:]
        out.append(new_source)

    return out


def _fix_lt_to_le(source):
    """Relax a strict comparison to non-strict (generic slip)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
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
    return out


def _fix_eq_to_neq(source):
    """Flip == to != as a generic comparison-direction slip."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " != " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="free_var_param_mismatch_day_date",
                apply=_fix_free_var_param_mismatch,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="missing_return_false_fallthrough",
                apply=_fix_missing_return_false,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_fix_lt_to_le,
                symptoms=("wrong",),
            ),
            Rule(
                name="eq_should_be_neq",
                apply=_fix_eq_to_neq,
                symptoms=("wrong",),
            ),
        ]


from src.core.repair import Rule