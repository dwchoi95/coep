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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Rule: `.title()` used instead of `.swapcase()`
# ---------------------------------------------------------------------------
def _title_to_swapcase(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'title'):
            vs, ve = _span(source, node.func.value)
            value_text = source[vs:ve]
            new_text = value_text + '.swapcase'
            out.append(_splice(source, node.func, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: `.capitalize()` used instead of `.swapcase()` when the guarding `if`
# compares a `[1:]` slice against its uppercased form.
# ---------------------------------------------------------------------------
def _capitalize_to_swapcase_in_slice_if(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        ts, te = _span(source, node.test)
        test_text = source[ts:te]
        has_slice = '[1:' in test_text
        has_upper_call = '.upper()' in test_text
        if has_slice and not has_upper_call:
            names_in_test = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
            for n2 in ast.walk(tree):
                if (isinstance(n2, ast.Assign) and len(n2.targets) == 1
                        and isinstance(n2.targets[0], ast.Name)
                        and n2.targets[0].id in names_in_test
                        and isinstance(n2.value, ast.Call)
                        and isinstance(n2.value.func, ast.Attribute)
                        and n2.value.func.attr == 'upper'):
                    has_upper_call = True
                    break
        if has_slice and has_upper_call:
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == 'capitalize'):
                    vs, ve = _span(source, sub.func.value)
                    value_text = source[vs:ve]
                    new_text = value_text + '.swapcase'
                    out.append(_splice(source, sub.func, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: missing `len(word) == 1` disjunct in `X.isupper() or Y[1:].isupper()`
# ---------------------------------------------------------------------------
def _is_isupper_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'isupper')


def _get_base_name(node):
    n = node
    while isinstance(n, ast.Call):
        n = n.func
    while isinstance(n, ast.Attribute):
        n = n.value
    while isinstance(n, ast.Subscript):
        n = n.value
    if isinstance(n, ast.Name):
        return n.id
    return None


def _contains_len(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == 'len':
            return True
    return False


def _add_len_one_or_clause(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            if (all(_is_isupper_call(v) for v in node.values)
                    and not any(_contains_len(v) for v in node.values)):
                var = _get_base_name(node.values[0])
                if var:
                    s, e = _span(source, node)
                    new_text = source[s:e] + f' or len({var}) == 1'
                    out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: the `if` condition only checks per-character case with `.capitalize()`
# and lacks an `else` branch; should use `.upper()` (with `[1:]` slicing) and
# print the word unchanged otherwise.
# ---------------------------------------------------------------------------
def _fix_capitalize_condition_with_else(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        has_capitalize_in_test = any(
            isinstance(n, ast.Attribute) and n.attr == 'capitalize'
            for n in ast.walk(node.test)
        )
        if not has_capitalize_in_test:
            continue
        has_for_capitalize = False
        for_iter_name = None
        for n in ast.walk(node):
            if isinstance(n, ast.For):
                for m in ast.walk(n):
                    if isinstance(m, ast.Attribute) and m.attr == 'capitalize':
                        has_for_capitalize = True
                if isinstance(n.iter, ast.Name):
                    for_iter_name = n.iter.id
        if not has_for_capitalize:
            continue
        if node.orelse:
            continue
        s, e = _span(source, node)
        block = source[s:e]
        new_block = block.replace('.capitalize()', '.upper()')
        new_block = new_block.replace('[0:]', '[1:]')
        if for_iter_name:
            new_block = new_block + f"\nelse:\n    print({for_iter_name})"
        if new_block != block:
            out.append(source[:s] + new_block + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule: `X[1:].isupper()` used alone, missing the `X.isupper() or
# (X[0].islower() and ...)` framing.
# ---------------------------------------------------------------------------
def _fix_missing_isupper_clause(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'isupper'):
            continue
        obj = node.func.value
        if not isinstance(obj, ast.Subscript):
            continue
        sl = obj.slice
        if isinstance(sl, ast.Slice):
            lower_ok = (sl.lower is not None and isinstance(sl.lower, ast.Constant)
                        and sl.lower.value == 1)
            upper_ok = sl.upper is None
        else:
            lower_ok = upper_ok = False
        if not (lower_ok and upper_ok):
            continue
        if not isinstance(obj.value, ast.Name):
            continue
        var = obj.value.id
        s, e = _span(source, node)
        prefix_start = max(0, s - 200)
        prefix = source[prefix_start:s]
        if f'{var}.isupper()' in prefix or f'{var}[0].islower()' in prefix:
            continue
        original_text = source[s:e]
        new_text = f'{var}.isupper() or ({var}[0].islower() and {original_text})'
        out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: bare `.isupper`/`.islower` attribute access used as a boolean value
# instead of calling it.
# ---------------------------------------------------------------------------
def _fix_bare_bool_attr_calls(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    call_func_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_func_ids.add(id(node.func))
    edits = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr in ('isupper', 'islower')
                and id(node) not in call_func_ids):
            s, e = _span(source, node)
            edits.append((s, e))
    if not edits:
        return []
    new_source = source
    for s, e in sorted(edits, key=lambda t: -t[0]):
        new_source = new_source[:e] + '()' + new_source[e:]
    return [new_source] if new_source != source else []


# ---------------------------------------------------------------------------
# Generic fallback: relax a strict comparison to non-strict (cheap, generic).
# ---------------------------------------------------------------------------
def _lt_to_le(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Lt)):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="capitalize_condition_should_be_upper_with_else",
                apply=_fix_capitalize_condition_with_else,
                symptoms=("wrong", "err:UnboundLocalError"),
            ),
            Rule(
                name="missing_global_isupper_and_first_lower_clause",
                apply=_fix_missing_isupper_clause,
                symptoms=("wrong",),
            ),
            Rule(
                name="title_should_be_swapcase",
                apply=_title_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_should_be_swapcase_in_slice_if",
                apply=_capitalize_to_swapcase_in_slice_if,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_len_one_or_clause",
                apply=_add_len_one_or_clause,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="bare_bool_attribute_missing_call",
                apply=_fix_bare_bool_attr_calls,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]