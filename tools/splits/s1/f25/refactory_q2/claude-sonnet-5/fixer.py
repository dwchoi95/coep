import ast

from src.core.repair import Rule


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


def _apply_edits(source, edits):
    new_src = source
    for node, new_text in sorted(edits, key=lambda e: _span(source, e[0])[0], reverse=True):
        s, e = _span(source, node)
        new_src = new_src[:s] + new_text + new_src[e:]
    return new_src


def _names_in_target(t):
    out = []
    if isinstance(t, ast.Name):
        out.append(t.id)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for e in t.elts:
            out.extend(_names_in_target(e))
    return out


def _bound_names(fn):
    names = set(a.arg for a in fn.args.args)
    if fn.args.vararg:
        names.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        names.add(fn.args.kwarg.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                names.update(_names_in_target(t))
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.For):
            names.update(_names_in_target(node.target))
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.comprehension):
            names.update(_names_in_target(node.target))
    return names


def _fix_undefined_day_date(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or fn.name != 'unique_day':
            continue
        if not fn.args.args:
            continue
        param = fn.args.args[0].arg
        if param not in ('day', 'date'):
            continue
        wrong = 'date' if param == 'day' else 'day'
        bound = _bound_names(fn)
        if wrong in bound:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == wrong:
                edits.append((node, param))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


def _fix_count_threshold(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            comp = node.comparators[0]
            if isinstance(comp, ast.Constant) and isinstance(comp.value, int) and not isinstance(comp.value, bool):
                val = comp.value
                left_s, left_e = _span(source, node.left)
                left_text = source[left_s:left_e]
                if (isinstance(op, ast.Gt) and val == 1) or (isinstance(op, ast.GtE) and val == 2):
                    edits.append((node, left_text + " != 1"))
                elif (isinstance(op, ast.LtE) and val == 1) or (isinstance(op, ast.Lt) and val == 2):
                    edits.append((node, left_text + " == 1"))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


def _fix_typo_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = {a.arg for a in fn.args.args}
        bound = _bound_names(fn)
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in bound:
                    continue
                candidates = [p for p in params if p == node.id + 's' or node.id == p + 's']
                if len(candidates) == 1:
                    edits.append((node, candidates[0]))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


def _fix_bool_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    mapping = {'Flase': 'False', 'Fasle': 'False', 'Ture': 'True', 'Treu': 'True'}
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in mapping:
            edits.append((node, mapping[node.id]))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


def _fix_while_le_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            t = node.test
            if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.LtE):
                right = t.comparators[0]
                if isinstance(right, ast.Call) and isinstance(right.func, ast.Name) and right.func.id == 'len':
                    left_s, left_e = _span(source, t.left)
                    right_s, right_e = _span(source, right)
                    new_text = source[left_s:left_e] + " < " + source[right_s:right_e]
                    edits.append((t, new_text))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


def _fix_undefined_call_arg(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        bound = _bound_names(fn)
        for node in ast.walk(fn):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loopvar = node.target.id
                for call in ast.walk(node):
                    if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                            and call.func.id == 'unique_day' and call.args):
                        arg0 = call.args[0]
                        if isinstance(arg0, ast.Name) and arg0.id not in bound and arg0.id != loopvar:
                            edits.append((arg0, "%s[1]" % loopvar))
    if not edits:
        return []
    return [_apply_edits(source, edits)]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="undefined_day_date_var",
                apply=_fix_undefined_day_date,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="count_threshold_off_by_one",
                apply=_fix_count_threshold,
                symptoms=("wrong",),
            ),
            Rule(
                name="typo_plural_param",
                apply=_fix_typo_param,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="boolean_literal_typo",
                apply=_fix_bool_typo,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="while_le_len_off_by_one",
                apply=_fix_while_le_len,
                symptoms=("wrong", "err:IndexError", "timeout"),
            ),
            Rule(
                name="undefined_call_arg_in_loop",
                apply=_fix_undefined_call_arg,
                symptoms=("wrong", "err:NameError"),
            ),
        ]