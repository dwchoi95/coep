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


def _multi_splice(source, spans_texts):
    """spans_texts: list of (start, end, replacement); non-overlapping."""
    new_src = source
    for s, e, rep in sorted(spans_texts, key=lambda x: x[0], reverse=True):
        new_src = new_src[:s] + rep + new_src[e:]
    return new_src


def _mod_var_swap(source):
    """In a digit-extraction while loop, `a = n % 10` then `if n==4 or n==7`
    should compare the extracted digit `a`, not the original `n`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        mod_pairs = []
        for stmt in ast.walk(node):
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.BinOp)
                    and isinstance(stmt.value.op, ast.Mod)
                    and isinstance(stmt.value.left, ast.Name)):
                mod_pairs.append((stmt.value.left.id, stmt.targets[0].id))
        if not mod_pairs:
            continue
        for int_var, mod_var in mod_pairs:
            if int_var == mod_var:
                continue
            targets = []
            for cmp in ast.walk(node):
                if (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1
                        and isinstance(cmp.ops[0], ast.Eq)
                        and isinstance(cmp.left, ast.Name) and cmp.left.id == int_var
                        and isinstance(cmp.comparators[0], ast.Constant)
                        and cmp.comparators[0].value in (4, 7)):
                    targets.append(cmp.left)
            if targets:
                spans = [(*(_span(source, t)), mod_var) for t in targets]
                new_src = _multi_splice(source, spans)
                if new_src != source:
                    out.append(new_src)
    return out


def _digit_char_int_to_str(source):
    """Comparing a character (from iterating a string) against the ints
    4/7 instead of the strings '4'/'7'."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        target = node.target
        it = node.iter
        mode = None
        var_id = None
        base_id = None
        idx_id = None
        if isinstance(target, ast.Name):
            if (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                    and it.func.id == 'range'):
                if (len(it.args) == 1 and isinstance(it.args[0], ast.Call)
                        and isinstance(it.args[0].func, ast.Name)
                        and it.args[0].func.id == 'len'
                        and len(it.args[0].args) == 1
                        and isinstance(it.args[0].args[0], ast.Name)):
                    mode = 'subscript'
                    base_id = it.args[0].args[0].id
                    idx_id = target.id
                else:
                    mode = None
            else:
                mode = 'name'
                var_id = target.id
        if mode is None:
            continue
        consts = []
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Compare) and len(sub.ops) == 1
                    and isinstance(sub.ops[0], ast.Eq)):
                continue
            sides = [sub.left, sub.comparators[0]]
            const_node = None
            other = None
            for s in sides:
                if isinstance(s, ast.Constant) and isinstance(s.value, int) and s.value in (4, 7):
                    const_node = s
                else:
                    other = s
            if const_node is None or other is None:
                continue
            match = False
            if mode == 'name' and isinstance(other, ast.Name) and other.id == var_id:
                match = True
            if mode == 'subscript' and isinstance(other, ast.Subscript):
                val = other.value
                sl = other.slice
                if isinstance(sl, ast.Index):
                    sl = sl.value
                if (isinstance(val, ast.Name) and val.id == base_id
                        and isinstance(sl, ast.Name) and sl.id == idx_id):
                    match = True
            if match:
                consts.append(const_node)
        if consts:
            spans = []
            for c in consts:
                s, e = _span(source, c)
                spans.append((s, e, "'" + source[s:e] + "'"))
            new_src = _multi_splice(source, spans)
            if new_src != source:
                out.append(new_src)
    return out


def _yesno_case(source):
    """Print 'Yes'/'No' (or lowercase) should be 'YES'/'NO'."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    mapping = {'Yes': 'YES', 'No': 'NO', 'yes': 'YES', 'no': 'NO'}
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in mapping:
            edits.append(node)
    if not edits:
        return []
    spans = []
    for node in edits:
        s, e = _span(source, node)
        spans.append((s, e, repr(mapping[node.value])))
    new_src = _multi_splice(source, spans)
    return [new_src] if new_src != source else []


def _duplicate_count_arg(source):
    """Two `.count("4")` calls summed together; second one should count "7"."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute) and call.func.attr == 'count'
                    and len(call.args) == 1 and isinstance(call.args[0], ast.Constant)
                    and call.args[0].value == '4'):
                calls.append(call)
    if len(calls) < 2:
        return []
    second = calls[1]
    arg = second.args[0]
    return [_splice(source, arg, "'7'")]


def _notin_flip(source):
    """`if char not in ['4','7']` used to count lucky digits should be `in`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], ast.NotIn)):
            comparator = node.comparators[0]
            if isinstance(comparator, (ast.List, ast.Tuple)):
                vals = {e.value for e in comparator.elts if isinstance(e, ast.Constant)}
                if vals == {'4', '7'}:
                    ls, le = _span(source, node.left)
                    cs, ce = _span(source, comparator)
                    new_cmp = source[ls:le] + " in " + source[cs:ce]
                    out.append(_splice(source, node, new_cmp))
    return out


def _demorgan_or_ne(source):
    """`S != 4 or S != 7` (always true) should be `S not in (4, 7)`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if (isinstance(a, ast.Compare) and isinstance(b, ast.Compare)
                    and len(a.ops) == 1 and len(b.ops) == 1
                    and isinstance(a.ops[0], ast.NotEq) and isinstance(b.ops[0], ast.NotEq)):
                la, ra = a.left, a.comparators[0]
                lb, rb = b.left, b.comparators[0]
                if (isinstance(ra, ast.Constant) and isinstance(rb, ast.Constant)
                        and isinstance(la, ast.Name) and isinstance(lb, ast.Name)
                        and la.id == lb.id):
                    ls, le = _span(source, la)
                    new_expr = source[ls:le] + " not in (%r, %r)" % (ra.value, rb.value)
                    out.append(_splice(source, node, new_expr))
    return out


def _mod_zero_to_eq(source):
    """`c % 4 == 0 or c % 7 == 0` should be `c == 4 or c == 7`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def is_mod_zero(cmp, val):
        return (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1
                and isinstance(cmp.ops[0], ast.Eq)
                and isinstance(cmp.left, ast.BinOp) and isinstance(cmp.left.op, ast.Mod)
                and isinstance(cmp.left.right, ast.Constant) and cmp.left.right.value == val
                and isinstance(cmp.comparators[0], ast.Constant)
                and cmp.comparators[0].value == 0)

    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if is_mod_zero(a, 4) and is_mod_zero(b, 7):
                bs, be = _span(source, a.left.left)
                base_txt = source[bs:be]
                new_expr = "%s==4 or %s==7" % (base_txt, base_txt)
                out.append(_splice(source, node, new_expr))
    return out


def _break_to_continue_and_len_check(source):
    """Counting loop that `break`s on non-lucky digit (undercounting) and
    then compares the count to `len(...)` instead of 4/7."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    break_targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Break):
            break_targets.append(node.orelse[0])
    len_targets = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and isinstance(node.comparators[0], ast.Call)
                and isinstance(node.comparators[0].func, ast.Name)
                and node.comparators[0].func.id == 'len'):
            len_targets.append(node)
    if not break_targets or not len_targets:
        return []
    spans = []
    for n in break_targets:
        s, e = _span(source, n)
        spans.append((s, e, "continue"))
    for n in len_targets:
        ls, le = _span(source, n.left)
        left_txt = source[ls:le]
        s, e = _span(source, n)
        spans.append((s, e, "%s==4 or %s==7" % (left_txt, left_txt)))
    new_src = _multi_splice(source, spans)
    return [new_src] if new_src != source else []


class Fixer:
    def rules(self):
        return [
            Rule(name="mod_var_swap", apply=_mod_var_swap, symptoms=("wrong",)),
            Rule(name="digit_char_int_to_str", apply=_digit_char_int_to_str, symptoms=("wrong",)),
            Rule(name="yesno_case", apply=_yesno_case, symptoms=("wrong",)),
            Rule(name="duplicate_count_arg", apply=_duplicate_count_arg, symptoms=("wrong",)),
            Rule(name="notin_flip", apply=_notin_flip, symptoms=("wrong",)),
            Rule(name="demorgan_or_ne", apply=_demorgan_or_ne, symptoms=("wrong",)),
            Rule(name="mod_zero_to_eq", apply=_mod_zero_to_eq, symptoms=("wrong",)),
            Rule(name="break_to_continue_and_len_check", apply=_break_to_continue_and_len_check,
                 symptoms=("wrong",)),
        ]