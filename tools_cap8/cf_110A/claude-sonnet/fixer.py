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


def _multi_splice(source, replacements):
    reps = sorted(replacements, key=lambda r: r[0], reverse=True)
    out = source
    for s, e, t in reps:
        out = out[:s] + t + out[e:]
    return out


def _fix_duplicate_count(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    count_calls = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'count' and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value in ('4', '7')):
            count_calls.add(id(node))

    assigns = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and id(node.value) in count_calls):
            assigns.append(node)

    out = []
    for i in range(len(assigns)):
        for j in range(i + 1, len(assigns)):
            a1 = assigns[i].value.args[0]
            a2 = assigns[j].value.args[0]
            if a1.value == a2.value:
                other = '7' if a1.value == '4' else '4'
                out.append(_splice(source, a2, f'"{other}"'))
    return out


def _fix_mod_loop_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        modvar = None
        srcvar = None
        for stmt in node.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                val = stmt.value
                if (isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mod)
                        and isinstance(val.right, ast.Constant)
                        and val.right.value == 10
                        and isinstance(val.left, ast.Name)):
                    modvar = stmt.targets[0].id
                    srcvar = val.left.id
                    break
        if not modvar or not srcvar or modvar == srcvar:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.If):
                names_to_fix = []
                for cmp_node in ast.walk(sub.test):
                    if isinstance(cmp_node, ast.Compare):
                        sides = [cmp_node.left] + list(cmp_node.comparators)
                        for side in sides:
                            if isinstance(side, ast.Name) and side.id == srcvar:
                                names_to_fix.append(side)
                if names_to_fix:
                    reps = [(*_span(source, n), modvar) for n in names_to_fix]
                    out.append(_multi_splice(source, reps))
    return out


def _fix_char_int_literal(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    charvars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            it = node.iter
            is_range = (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                        and it.func.id == 'range')
            if not is_range:
                charvars.add(node.target.id)

    reps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            qualifies = False
            if isinstance(left, ast.Name) and left.id in charvars:
                qualifies = True
            elif isinstance(left, ast.Subscript):
                qualifies = True
            if (qualifies and isinstance(right, ast.Constant)
                    and isinstance(right.value, int)
                    and not isinstance(right.value, bool)
                    and right.value in (4, 7)):
                reps.append((*_span(source, right), f"'{right.value}'"))

    if not reps:
        return []
    return [_multi_splice(source, reps)]


def _fix_yes_no_case(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    mapping = {'Yes': 'YES', 'No': 'NO', 'yes': 'YES', 'no': 'NO'}
    reps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in mapping:
            reps.append((*_span(source, node), f'"{mapping[node.value]}"'))
    if not reps:
        return []
    return [_multi_splice(source, reps)]


def _fix_break_to_continue(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.If) and len(node.orelse) == 1
                and isinstance(node.orelse[0], ast.Break)):
            brk = node.orelse[0]
            out.append(_splice(source, brk, "continue"))
    return out


def _fix_count_eq_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if (isinstance(left, ast.Name) and isinstance(right, ast.Call)
                    and isinstance(right.func, ast.Name) and right.func.id == 'len'):
                name = left.id
                new_text = f"{name}==4 or {name}==7"
                out.append(_splice(source, node, new_text))
    return out


def _fix_notin_to_in(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
            right = node.comparators[0]
            if isinstance(right, (ast.List, ast.Tuple)):
                vals = set()
                ok = True
                for e in right.elts:
                    if isinstance(e, ast.Constant):
                        vals.add(e.value)
                    else:
                        ok = False
                if ok and vals in ({'4', '7'}, {4, 7}):
                    ls, le = _span(source, node.left)
                    rs, re_ = _span(source, right)
                    new_text = source[ls:le] + " in " + source[rs:re_]
                    out.append(_splice(source, node, new_text))
    return out


def _fix_or_ne_to_notin(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            c1, c2 = node.values
            if not (isinstance(c1, ast.Compare) and isinstance(c2, ast.Compare)):
                continue
            if not (len(c1.ops) == 1 and len(c2.ops) == 1):
                continue
            if not (isinstance(c1.ops[0], ast.NotEq) and isinstance(c2.ops[0], ast.NotEq)):
                continue
            l1, r1 = c1.left, c1.comparators[0]
            l2, r2 = c2.left, c2.comparators[0]
            if not (isinstance(l1, ast.Name) and isinstance(l2, ast.Name) and l1.id == l2.id):
                continue
            if not (isinstance(r1, ast.Constant) and isinstance(r2, ast.Constant)):
                continue
            vals = {r1.value, r2.value}
            if vals == {4, 7}:
                new_text = f"{l1.id} not in [4, 7]"
                out.append(_splice(source, node, new_text))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="duplicate_count_same_digit",
                apply=_fix_duplicate_count,
                symptoms=("wrong",),
            ),
            Rule(
                name="mod_loop_compares_wrong_var",
                apply=_fix_mod_loop_var,
                symptoms=("wrong",),
            ),
            Rule(
                name="char_compared_to_int_literal",
                apply=_fix_char_int_literal,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="yes_no_wrong_case",
                apply=_fix_yes_no_case,
                symptoms=("wrong",),
            ),
            Rule(
                name="break_should_be_continue",
                apply=_fix_break_to_continue,
                symptoms=("wrong",),
            ),
            Rule(
                name="count_eq_len_should_be_lucky_check",
                apply=_fix_count_eq_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="notin_should_be_in",
                apply=_fix_notin_to_in,
                symptoms=("wrong",),
            ),
            Rule(
                name="or_ne_always_true_should_be_notin",
                apply=_fix_or_ne_to_notin,
                symptoms=("wrong",),
            ),
        ]