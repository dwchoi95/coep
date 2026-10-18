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


def _dedup(fn):
    def wrapped(source):
        try:
            results = fn(source)
        except Exception:
            return []
        out = []
        for r in results:
            if isinstance(r, str) and r != source and r not in out:
                out.append(r)
        return out
    return wrapped


def _looks_like_emptiness_test(node):
    if isinstance(node, ast.BoolOp):
        return any(_looks_like_emptiness_test(v) for v in node.values)
    if isinstance(node, ast.Compare):
        elems = [node.left] + list(node.comparators)
        for e in elems:
            if isinstance(e, (ast.Tuple, ast.List)) and len(e.elts) == 0:
                return True
            if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == 'len':
                return True
        return False
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    return False


# ---------------------------------------------------------------------------
# Rule A: an emptiness check returns something other than 0
# ---------------------------------------------------------------------------
def _empty_check_wrong_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _looks_like_emptiness_test(node.test):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                ret = node.body[0]
                val = ret.value
                is_zero = isinstance(val, ast.Constant) and val.value == 0
                if is_zero:
                    continue
                if val is None:
                    out.append(_splice(source, ret, "return 0"))
                else:
                    vs, ve = _span(source, val)
                    out.append(source[:vs] + "0" + source[ve:])
    return out


# ---------------------------------------------------------------------------
# Rule B: `if <empty-check>: pass` -> `return 0`
# ---------------------------------------------------------------------------
def _pass_to_return0(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _looks_like_emptiness_test(node.test):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                out.append(_splice(source, node.body[0], "return 0"))
    return out


# ---------------------------------------------------------------------------
# Rule C: `seq == () or []` style bare-literal operator precedence bug
# ---------------------------------------------------------------------------
def _bare_literal_or_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            name = None
            for v in node.values:
                if (isinstance(v, ast.Compare) and isinstance(v.left, ast.Name)
                        and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq)):
                    name = v.left.id
                    break
            if name is None:
                continue
            edits = []
            for v in node.values:
                if isinstance(v, (ast.Tuple, ast.List)):
                    vs, ve = _span(source, v)
                    lit_text = source[vs:ve]
                    edits.append((vs, ve, f"{name} == {lit_text}"))
            if edits:
                edits.sort(key=lambda t: t[0], reverse=True)
                new_source = source
                for s, e, text in edits:
                    new_source = new_source[:s] + text + new_source[e:]
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule D: combining two emptiness checks with `and` instead of `or`
# ---------------------------------------------------------------------------
def _and_to_or_emptiness(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            if all(_looks_like_emptiness_test(v) or isinstance(v, (ast.Tuple, ast.List))
                   for v in node.values):
                parts = []
                for v in node.values:
                    vs, ve = _span(source, v)
                    parts.append(source[vs:ve])
                out.append(_splice(source, node, " or ".join(parts)))
    return out


# ---------------------------------------------------------------------------
# Rule E: mutate comparisons involving `x` (strict<->non-strict, direction
# reversal, operand swap) -- covers a large family of off-by-one / flipped
# boundary misconceptions.
# ---------------------------------------------------------------------------
_STRICT_TOGGLE = {ast.Lt: '<=', ast.LtE: '<', ast.Gt: '>=', ast.GtE: '>'}
_REVERSE_DIR = {ast.Lt: '>', ast.LtE: '>=', ast.Gt: '<', ast.GtE: '<='}
_OP_TEXT = {ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>='}


def _compare_mutations(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op_type = type(node.ops[0])
            if op_type not in _STRICT_TOGGLE:
                continue
            left, right = node.left, node.comparators[0]
            left_is_x = isinstance(left, ast.Name) and left.id == 'x'
            right_is_x = isinstance(right, ast.Name) and right.id == 'x'
            if not (left_is_x or right_is_x):
                continue
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            left_text = source[ls:le]
            right_text = source[rs:re_]
            variants = [
                left_text + " " + _STRICT_TOGGLE[op_type] + " " + right_text,
                left_text + " " + _REVERSE_DIR[op_type] + " " + right_text,
                right_text + " " + _OP_TEXT[op_type] + " " + left_text,
            ]
            for v in variants:
                out.append(_splice(source, node, v))
    return out


# ---------------------------------------------------------------------------
# Rule F: function ends with a loop that may fall through without a return
# ---------------------------------------------------------------------------
def _missing_loop_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        if not body:
            continue
        idx = len(body) - 1
        while idx >= 0 and isinstance(body[idx], ast.Expr) \
                and isinstance(getattr(body[idx], 'value', None), ast.Constant) \
                and isinstance(body[idx].value.value, str):
            idx -= 1
        if idx < 0:
            continue
        last = body[idx]
        if not isinstance(last, (ast.For, ast.While)):
            continue
        if last.orelse:
            continue
        has_return_inside = any(isinstance(n, ast.Return) for n in ast.walk(last))
        if not has_return_inside:
            continue
        indent = ' ' * last.col_offset
        insertion_point = _span(source, body[-1])[1]
        new_source = (source[:insertion_point] + "\n" + indent
                      + "return len(seq)\n" + source[insertion_point:])
        out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule G: `position += position` self-increment instead of `+= 1`
# ---------------------------------------------------------------------------
def _self_increment_bug(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if (isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name)
                    and node.target.id == node.value.id):
                out.append(_splice(source, node.value, "1"))
    return out


# ---------------------------------------------------------------------------
# Rule H: `count==0` typo for assignment
# ---------------------------------------------------------------------------
def _eq_typo_assign(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if (len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq)
                    and isinstance(cmp.left, ast.Name)):
                ls, le = _span(source, cmp.left)
                rs, re_ = _span(source, cmp.comparators[0])
                new_stmt = source[ls:le] + " = " + source[rs:re_]
                out.append(_splice(source, node, new_stmt))
    return out


# ---------------------------------------------------------------------------
# Rule I: strip a spurious `+1` / `-1` on a returned value
# ---------------------------------------------------------------------------
def _strip_off_by_one_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp):
            b = node.value
            if (isinstance(b.op, (ast.Add, ast.Sub))
                    and isinstance(b.right, ast.Constant) and b.right.value == 1):
                ls, le = _span(source, b.left)
                out.append(_splice(source, b, source[ls:le]))
    return out


# ---------------------------------------------------------------------------
# Rule J: `return i + 1` tail case should be `return len(seq)`
# ---------------------------------------------------------------------------
def _return_iplus1_to_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) \
                and isinstance(node.value.op, ast.Add):
            b = node.value
            if (isinstance(b.right, ast.Constant) and b.right.value == 1
                    and isinstance(b.left, ast.Name)):
                out.append(_splice(source, b, "len(seq)"))
    return out


# ---------------------------------------------------------------------------
# Rule K: `result = i; return` (bare return) should be `break`
# ---------------------------------------------------------------------------
def _iter_blocks(node):
    for field in ('body', 'orelse', 'finalbody'):
        block = getattr(node, field, None)
        if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
            yield block
            for child in block:
                yield from _iter_blocks(child)


def _bare_return_to_break(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for block in _iter_blocks(fn):
            for i in range(len(block) - 1):
                a, b = block[i], block[i + 1]
                if isinstance(a, ast.Assign) and isinstance(b, ast.Return) and b.value is None:
                    out.append(_splice(source, b, "break"))
    return out


# ---------------------------------------------------------------------------
# Rule L: insert a leading `if not seq: return 0` guard when the function
# indexes seq[0]/seq[-1] without first checking for an empty sequence.
# ---------------------------------------------------------------------------
def _insert_not_seq_guard(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        body = fn.body
        if not body:
            continue
        start_idx = 0
        if (isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], 'value', None), ast.Constant)
                and isinstance(body[0].value.value, str)):
            start_idx = 1
        if start_idx >= len(body):
            continue
        first = body[start_idx]
        fs, fe = _span(source, fn)
        fn_src = source[fs:fe]
        if isinstance(first, ast.If):
            ts, te = _span(source, first.test)
            test_src = source[ts:te]
            markers = ['()', '[]', 'len(', 'not seq']
            if any(m in test_src for m in markers):
                continue
        if 'seq[0]' not in fn_src and 'seq[-1]' not in fn_src:
            continue
        indent = ' ' * first.col_offset
        insert_pos = _span(source, first)[0]
        guard_text = f"if not seq:\n{indent}    return 0\n{indent}"
        out.append(source[:insert_pos] + guard_text + source[insert_pos:])
    return out


# ---------------------------------------------------------------------------
# Rule M: `sorted(seq)` result discarded, later `.index` used on original seq
# ---------------------------------------------------------------------------
def _sorted_not_assigned(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        used_names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        varname = 'a' if 'a' not in used_names else '_srt'
        for node in ast.walk(fn):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if (isinstance(call.func, ast.Name) and call.func.id == 'sorted'
                        and len(call.args) == 1 and isinstance(call.args[0], ast.Name)):
                    xname = call.args[0].id
                    edits = []
                    s, e = _span(source, node)
                    edits.append((s, e, f"{varname} = sorted({xname})"))
                    for idx_call in ast.walk(fn):
                        if (isinstance(idx_call, ast.Call)
                                and isinstance(idx_call.func, ast.Attribute)
                                and idx_call.func.attr == 'index'
                                and isinstance(idx_call.func.value, ast.Name)
                                and idx_call.func.value.id == xname):
                            vs, ve = _span(source, idx_call.func.value)
                            edits.append((vs, ve, varname))
                    edits.sort(key=lambda t: t[0], reverse=True)
                    new_source = source
                    for s2, e2, txt in edits:
                        new_source = new_source[:s2] + txt + new_source[e2:]
                    out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule N: `range(seq)` should be `range(len(seq))`
# ---------------------------------------------------------------------------
def _wrap_range_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[id(child)] = node
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'range' and len(node.args) == 1):
            arg = node.args[0]
            if isinstance(arg, ast.Name) and arg.id == 'seq':
                p = parent.get(id(node))
                if isinstance(p, ast.Call) and isinstance(p.func, ast.Name) and p.func.id == 'len':
                    continue
                vs, ve = _span(source, arg)
                out.append(source[:vs] + f"len({source[vs:ve]})" + source[ve:])
    return out


# ---------------------------------------------------------------------------
# Rule O: `len(range(seq))` should be `range(len(seq))`
# ---------------------------------------------------------------------------
def _len_range_swap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'len' and len(node.args) == 1):
            inner = node.args[0]
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == 'range' and len(inner.args) == 1):
                x = inner.args[0]
                xs, xe = _span(source, x)
                xtext = source[xs:xe]
                out.append(_splice(source, node, f"range(len({xtext}))"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="empty_check_wrong_return",
                 apply=_dedup(_empty_check_wrong_return),
                 symptoms=("wrong",)),
            Rule(name="pass_in_empty_check_to_return0",
                 apply=_dedup(_pass_to_return0),
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="bare_literal_or_precedence_bug",
                 apply=_dedup(_bare_literal_or_fix),
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="and_should_be_or_for_emptiness",
                 apply=_dedup(_and_to_or_emptiness),
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="boundary_comparison_mutation",
                 apply=_dedup(_compare_mutations),
                 symptoms=("wrong",)),
            Rule(name="missing_trailing_loop_return",
                 apply=_dedup(_missing_loop_return),
                 symptoms=("wrong",)),
            Rule(name="self_increment_instead_of_plus_one",
                 apply=_dedup(_self_increment_bug),
                 symptoms=("timeout", "wrong")),
            Rule(name="eq_typo_for_assignment",
                 apply=_dedup(_eq_typo_assign),
                 symptoms=("err:NameError", "err:UnboundLocalError", "wrong")),
            Rule(name="strip_spurious_off_by_one",
                 apply=_dedup(_strip_off_by_one_return),
                 symptoms=("wrong",)),
            Rule(name="return_i_plus_one_to_len_seq",
                 apply=_dedup(_return_iplus1_to_len),
                 symptoms=("wrong",)),
            Rule(name="bare_return_should_be_break",
                 apply=_dedup(_bare_return_to_break),
                 symptoms=("wrong",)),
            Rule(name="insert_not_seq_guard",
                 apply=_dedup(_insert_not_seq_guard),
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="sorted_result_not_assigned",
                 apply=_dedup(_sorted_not_assigned),
                 symptoms=("wrong",)),
            Rule(name="range_missing_len_wrap",
                 apply=_dedup(_wrap_range_len),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="len_range_swapped",
                 apply=_dedup(_len_range_swap),
                 symptoms=("err:TypeError", "wrong")),
        ]