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


def _is_const(n, value):
    return isinstance(n, ast.Constant) and n.value == value


def _is_tail_slice(sl):
    """matches X[1:] exactly"""
    if isinstance(sl, ast.Slice) and sl.upper is None and sl.step is None:
        return isinstance(sl.lower, ast.Constant) and sl.lower.value == 1
    return False


def _is_zero_index(sl):
    if isinstance(sl, ast.Constant) and sl.value == 0:
        return True
    idx = getattr(ast, "Index", None)
    if idx is not None and isinstance(sl, idx):
        v = sl.value
        return isinstance(v, ast.Constant) and v.value == 0
    return False


def _collect_slice_vars(tree):
    """names assigned exactly as `Y = X[1:]`."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name):
                if _is_tail_slice(val.slice):
                    names.add(node.targets[0].id)
    return names


def _is_isupper_call(n):
    return isinstance(n, ast.Call) and not n.args and not n.keywords \
        and isinstance(n.func, ast.Attribute) and n.func.attr == 'isupper'


def _is_islower_call(n):
    return isinstance(n, ast.Call) and not n.args and not n.keywords \
        and isinstance(n.func, ast.Attribute) and n.func.attr == 'islower'


# ---------------------------------------------------------------------
# Rule: X[1:].isupper() (or a variable assigned from such a slice) does
# not account for the single-letter word case because ''.isupper() is
# False. Replace it with the equivalent equality comparison, which is
# True for the empty string too.
# ---------------------------------------------------------------------
def fix_sliced_isupper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    slice_vars = _collect_slice_vars(tree)
    matches = []
    for node in ast.walk(tree):
        if not _is_isupper_call(node):
            continue
        val = node.func.value
        expr = None
        if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) \
           and _is_tail_slice(val.slice):
            vs, ve = _span(source, val)
            expr = source[vs:ve]
        elif isinstance(val, ast.Name) and val.id in slice_vars:
            expr = val.id
        if expr is not None:
            matches.append((node, expr))
    if not matches:
        return []
    edits = []
    for node, expr in matches:
        s, e = _span(source, node)
        edits.append((s, e, "(%s == %s.upper())" % (expr, expr)))
    edits.sort(key=lambda x: x[0], reverse=True)
    new_source = source
    for s, e, text in edits:
        new_source = new_source[:s] + text + new_source[e:]
    return [new_source]


# ---------------------------------------------------------------------
# Rule: word[1:].islower() used by mistake instead of checking for
# upper-case, alongside a correct word.isupper() full-word check.
# ---------------------------------------------------------------------
def fix_sliced_islower_misuse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    full_upper_names = set()
    for node in ast.walk(tree):
        if _is_isupper_call(node) and isinstance(node.func.value, ast.Name):
            full_upper_names.add(node.func.value.id)
    if not full_upper_names:
        return []
    matches = []
    for node in ast.walk(tree):
        if not _is_islower_call(node):
            continue
        val = node.func.value
        if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) \
           and val.value.id in full_upper_names and _is_tail_slice(val.slice):
            vs, ve = _span(source, val)
            expr = source[vs:ve]
            matches.append((node, expr))
    if not matches:
        return []
    edits = []
    for node, expr in matches:
        s, e = _span(source, node)
        edits.append((s, e, "(%s == %s.upper())" % (expr, expr)))
    edits.sort(key=lambda x: x[0], reverse=True)
    new_source = source
    for s, e, text in edits:
        new_source = new_source[:s] + text + new_source[e:]
    return [new_source]


# ---------------------------------------------------------------------
# Rule: an `or` test checks `X.isupper()` and `X[1:].isupper()` (maybe
# nested inside an `and`) but forgets the single-letter special case.
# ---------------------------------------------------------------------
def add_len_one_to_or_test(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    seen = set()
    for node in ast.walk(tree):
        test = None
        if isinstance(node, ast.If):
            test = node.test
        elif isinstance(node, ast.IfExp):
            test = node.test
        if test is None or not isinstance(test, ast.BoolOp) or not isinstance(test.op, ast.Or):
            continue
        full_name = None
        sliced_name = None
        has_len_check = False
        for sub in ast.walk(test):
            if _is_isupper_call(sub):
                val = sub.func.value
                if isinstance(val, ast.Name):
                    full_name = full_name or val.id
                elif isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) \
                        and _is_tail_slice(val.slice):
                    sliced_name = sliced_name or val.value.id
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == 'len':
                has_len_check = True
        if full_name and sliced_name and full_name == sliced_name and not has_len_check:
            key = _span(source, test)
            if key in seen:
                continue
            seen.add(key)
            s, e = key
            orig = source[s:e]
            new_text = "(%s) or len(%s) == 1" % (orig, full_name)
            out.append(_splice(source, test, new_text))
    return out


# ---------------------------------------------------------------------
# Rule: an `or` test wrongly includes `X.islower()`, which fires the
# swap for plain lower-case words too. Drop that clause and make sure
# the single-letter case is still covered.
# ---------------------------------------------------------------------
def remove_islower_disjunct(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        test = None
        if isinstance(node, ast.If):
            test = node.test
        elif isinstance(node, ast.IfExp):
            test = node.test
        if test is None or not isinstance(test, ast.BoolOp) or not isinstance(test.op, ast.Or):
            continue
        values = test.values
        full_name = None
        has_islower = False
        has_len_check = False
        keep_idx = []
        for i, v in enumerate(values):
            if _is_isupper_call(v) and isinstance(v.func.value, ast.Name):
                full_name = full_name or v.func.value.id
                keep_idx.append(i)
                continue
            if _is_islower_call(v) and isinstance(v.func.value, ast.Name):
                has_islower = True
                continue
            if isinstance(v, ast.Compare) and isinstance(v.left, ast.Call) \
               and isinstance(v.left.func, ast.Name) and v.left.func.id == 'len':
                has_len_check = True
                keep_idx.append(i)
                continue
            keep_idx.append(i)
        if not has_islower or full_name is None:
            continue
        parts = []
        for i in keep_idx:
            vs, ve = _span(source, values[i])
            parts.append(source[vs:ve])
        if not has_len_check:
            parts.append("len(%s) == 1" % full_name)
        new_text = " or ".join(parts)
        out.append(_splice(source, test, new_text))
    return out


# ---------------------------------------------------------------------
# Rule: `len(word) > 1 and word[1:].isupper()` wrongly excludes the
# single-letter word from the fix. The equality form naturally covers
# it, so the length guard can be dropped.
# ---------------------------------------------------------------------
def drop_len_guard_with_sliced_isupper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And) and len(node.values) == 2):
            continue
        a, b = node.values

        def len_guard_target(n):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 \
               and isinstance(n.left, ast.Call) and isinstance(n.left.func, ast.Name) \
               and n.left.func.id == 'len' and n.left.args:
                op = n.ops[0]
                comp = n.comparators[0]
                if isinstance(comp, ast.Constant):
                    if isinstance(op, ast.Gt) and comp.value == 1:
                        return n.left.args[0]
                    if isinstance(op, ast.GtE) and comp.value == 2:
                        return n.left.args[0]
            return None

        def sliced_isupper(n):
            if _is_isupper_call(n):
                val = n.func.value
                if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) \
                   and _is_tail_slice(val.slice):
                    return val
            return None

        guard_target = len_guard_target(a) or len_guard_target(b)
        sliced = sliced_isupper(a) or sliced_isupper(b)
        if guard_target is not None and sliced is not None \
           and isinstance(guard_target, ast.Name) and isinstance(sliced.value, ast.Name) \
           and guard_target.id == sliced.value.id:
            vs, ve = _span(source, sliced)
            expr = source[vs:ve]
            new_text = "(%s == %s.upper())" % (expr, expr)
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------
# Rule: the program always capitalizes (`X[0].upper() + X[1:].lower()`)
# without ever checking whether the caps-lock rule applies. Guard the
# expression with the standard condition, using swapcase (which is
# correct for both the all-caps and the "all but first" cases).
# ---------------------------------------------------------------------
def _match_capitalize_binop(node):
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Add):
        return None
    left, right = node.left, node.right

    def left_name(n):
        if isinstance(n, ast.Call) and not n.args and not n.keywords \
           and isinstance(n.func, ast.Attribute) and n.func.attr == 'upper':
            sub = n.func.value
            if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) \
               and _is_zero_index(sub.slice):
                return sub.value.id
        return None

    def right_matches(n, name):
        if isinstance(n, ast.Call) and not n.args and not n.keywords \
           and isinstance(n.func, ast.Attribute) and n.func.attr == 'lower':
            sub = n.func.value
            if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name) \
               and sub.value.id == name and _is_tail_slice(sub.slice):
                return True
        return False

    name = left_name(left)
    if name and right_matches(right, name):
        return name
    return None


def wrap_unconditional_capitalize(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        name = _match_capitalize_binop(node)
        if name:
            new_text = (
                "({n}.swapcase() if ({n}.isupper() or ({n}[1:] == {n}[1:].upper()) "
                "or len({n}) == 1) else {n})"
            ).format(n=name)
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------
# Rule: the program unconditionally swapcases the whole word, with no
# surrounding condition at all.
# ---------------------------------------------------------------------
def wrap_unconditional_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    has_cond = any(isinstance(n, (ast.If, ast.IfExp)) for n in ast.walk(tree))
    if has_cond:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and not node.args and not node.keywords \
           and isinstance(node.func, ast.Attribute) and node.func.attr == 'swapcase' \
           and isinstance(node.func.value, ast.Name):
            name = node.func.value.id
            new_text = (
                "({n}.swapcase() if ({n}.isupper() or ({n}[1:] == {n}[1:].upper()) "
                "or len({n}) == 1) else {n})"
            ).format(n=name)
            out.append(_splice(source, node, new_text))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="sliced_isupper_missing_single_letter_case",
                apply=fix_sliced_isupper,
                symptoms=("wrong",),
            ),
            Rule(
                name="sliced_islower_wrong_method",
                apply=fix_sliced_islower_misuse,
                symptoms=("wrong",),
            ),
            Rule(
                name="or_test_missing_len_one_clause",
                apply=add_len_one_to_or_test,
                symptoms=("wrong",),
            ),
            Rule(
                name="or_test_spurious_islower_clause",
                apply=remove_islower_disjunct,
                symptoms=("wrong",),
            ),
            Rule(
                name="len_gt_one_guard_excludes_single_letter",
                apply=drop_len_guard_with_sliced_isupper,
                symptoms=("wrong",),
            ),
            Rule(
                name="unconditional_capitalize_formula",
                apply=wrap_unconditional_capitalize,
                symptoms=("wrong",),
            ),
            Rule(
                name="unconditional_swapcase",
                apply=wrap_unconditional_swapcase,
                symptoms=("wrong",),
            ),
        ]