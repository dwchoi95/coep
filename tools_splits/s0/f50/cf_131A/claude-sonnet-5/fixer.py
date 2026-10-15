"""
Repair module for the "cAPS lOCK" assignment.

Each rule targets one structural misconception seen across the buggy
submissions and performs a small, local AST-located, source-spliced edit.
Rules never rewrite whole functions/modules; they only touch the specific
expression/attribute responsible for the bug.
"""

import ast

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# Generic span / splice helpers
# ---------------------------------------------------------------------------

def _span(source, node):
    """(start, end) char offsets of node in source."""
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _apply_edits(source, edits):
    """edits: list of (start, end, replacement); applied right-to-left."""
    edits = sorted(edits, key=lambda x: x[0], reverse=True)
    out = source
    for s, e, rep in edits:
        out = out[:s] + rep + out[e:]
    return out


def _dedup_nonempty(source, candidates):
    uniq, seen = [], set()
    for c in candidates:
        if c != source and c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq


def _get_slice_tail_name(node):
    """If `node` is a Subscript of the form NAME[1:], return NAME (str)."""
    if not isinstance(node, ast.Subscript):
        return None
    sl = node.slice
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):  # py < 3.9
        sl = sl.value
    if isinstance(sl, ast.Slice) and sl.upper is None and sl.step is None:
        lower = sl.lower
        if isinstance(lower, ast.Constant) and lower.value == 1:
            if isinstance(node.value, ast.Name):
                return node.value.id
    return None


# ---------------------------------------------------------------------------
# Rule 1: missing single-character clause on tail-isupper conditions
# ---------------------------------------------------------------------------

def _has_len_eq_one(test_node, varname):
    for n in ast.walk(test_node):
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Eq):
            left, right = n.left, n.comparators[0]
            for a, b in ((left, right), (right, left)):
                if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id == "len":
                    if a.args and isinstance(a.args[0], ast.Name) and a.args[0].id == varname:
                        if isinstance(b, ast.Constant) and b.value == 1:
                            return True
    return False


def rule_add_len_one_clause(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    matches = []
    for node in ast.walk(tree):
        test = None
        if isinstance(node, ast.If):
            test = node.test
        elif isinstance(node, ast.IfExp):
            test = node.test
        if test is None:
            continue

        found_var = None
        for sub in ast.walk(test):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "isupper":
                var = _get_slice_tail_name(sub.func.value)
                if var:
                    found_var = var
                    break
        if found_var is None:
            continue
        if _has_len_eq_one(test, found_var):
            continue
        matches.append((test, found_var))

    if not matches:
        return []

    candidates = []
    all_edits = []
    for test, var in matches:
        s, e = _span(source, test)
        orig_text = source[s:e]
        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
            new_text = orig_text + " or len(%s) == 1" % var
        else:
            new_text = "(" + orig_text + ") or len(%s) == 1" % var
        candidates.append(_apply_edits(source, [(s, e, new_text)]))
        all_edits.append((s, e, new_text))

    if len(matches) > 1:
        candidates.append(_apply_edits(source, all_edits))

    return _dedup_nonempty(source, candidates)


# ---------------------------------------------------------------------------
# Rule 2: bare attribute access instead of a method call (missing parens)
# ---------------------------------------------------------------------------

_CASE_METHODS = {
    "isupper", "islower", "upper", "lower",
    "capitalize", "swapcase", "title",
    "isalpha", "isdigit", "isalnum",
}


def rule_bare_attr_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    called_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_ids.add(id(node.func))

    matches = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _CASE_METHODS:
            if id(node) in called_ids:
                continue
            matches.append(node)

    if not matches:
        return []

    candidates = []
    all_edits = []
    for node in matches:
        _, e = _span(source, node)
        candidates.append(_apply_edits(source, [(e, e, "()")]))
        all_edits.append((e, e, "()"))

    if len(matches) > 1:
        candidates.append(_apply_edits(source, all_edits))

    return _dedup_nonempty(source, candidates)


# ---------------------------------------------------------------------------
# Rule 3: .upper()/.lower() used directly as a truthy condition
# ---------------------------------------------------------------------------

def rule_bool_truth_case_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    matches = []
    for node in ast.walk(tree):
        test = None
        if isinstance(node, ast.If):
            test = node.test
        elif isinstance(node, ast.IfExp):
            test = node.test
        if test is None:
            continue

        inside_compare_ids = set()
        for sub in ast.walk(test):
            if isinstance(sub, ast.Compare):
                for d in ast.walk(sub):
                    inside_compare_ids.add(id(d))

        for sub in ast.walk(test):
            if id(sub) in inside_compare_ids:
                continue
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr in ("upper", "lower") and not sub.args):
                matches.append(sub.func)

    if not matches:
        return []

    candidates = []
    all_edits = []
    for func_node in matches:
        s, e = _span(source, func_node)
        value_text = _text(source, func_node.value)
        new_attr = "is" + func_node.attr
        new_text = value_text + "." + new_attr
        candidates.append(_apply_edits(source, [(s, e, new_text)]))
        all_edits.append((s, e, new_text))

    if len(matches) > 1:
        candidates.append(_apply_edits(source, all_edits))

    return _dedup_nonempty(source, candidates)


# ---------------------------------------------------------------------------
# Rule 4: .capitalize() (optionally after .lower()) should be .swapcase()
# ---------------------------------------------------------------------------

def rule_capitalize_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    matches = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "capitalize" and not node.args):
            base = node.func.value
            name_node = None
            if isinstance(base, ast.Name):
                name_node = base
            elif (isinstance(base, ast.Call) and isinstance(base.func, ast.Attribute)
                    and base.func.attr == "lower" and not base.args
                    and isinstance(base.func.value, ast.Name)):
                name_node = base.func.value
            if name_node is not None:
                matches.append((node, name_node))

    if not matches:
        return []

    candidates = []
    all_edits = []
    for call_node, name_node in matches:
        s, e = _span(source, call_node)
        new_text = name_node.id + ".swapcase()"
        candidates.append(_apply_edits(source, [(s, e, new_text)]))
        all_edits.append((s, e, new_text))

    if len(matches) > 1:
        candidates.append(_apply_edits(source, all_edits))

    return _dedup_nonempty(source, candidates)


# ---------------------------------------------------------------------------
# Rule 5: nonexistent .uppercase()/.lowercase() methods
# ---------------------------------------------------------------------------

def rule_invalid_case_method(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    rename = {"uppercase": "upper", "lowercase": "lower"}
    matches = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in rename]

    if not matches:
        return []

    candidates = []
    all_edits = []
    for node in matches:
        s, e = _span(source, node)
        value_text = _text(source, node.value)
        new_text = value_text + "." + rename[node.attr]
        candidates.append(_apply_edits(source, [(s, e, new_text)]))
        all_edits.append((s, e, new_text))

    if len(matches) > 1:
        candidates.append(_apply_edits(source, all_edits))

    return _dedup_nonempty(source, candidates)


# ---------------------------------------------------------------------------
# Rule 6: tail[1:].islower() used where tail[1:].isupper() was meant
#         (only when the program also swapcases somewhere, a strong signal
#          that the intent was "rest of word is all caps")
# ---------------------------------------------------------------------------

def rule_islower_should_be_isupper_tailslice(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    has_swapcase = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "swapcase"
        for n in ast.walk(tree)
    )
    if not has_swapcase:
        return []

    matches = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "islower" and not node.args):
            var = _get_slice_tail_name(node.func.value)
            if var:
                matches.append(node.func)

    if not matches:
        return []

    candidates = []
    all_edits = []
    for func_node in matches:
        s, e = _span(source, func_node)
        value_text = _text(source, func_node.value)
        new_text = value_text + ".isupper"
        candidates.append(_apply_edits(source, [(s, e, new_text)]))
        all_edits.append((s, e, new_text))

    if len(matches) > 1:
        candidates.append(_apply_edits(source, all_edits))

    return _dedup_nonempty(source, candidates)


# ---------------------------------------------------------------------------
# Safe wrapper so a single bad input can't crash the harness
# ---------------------------------------------------------------------------

def _safe(fn):
    def wrapped(source):
        try:
            return fn(source) or []
        except Exception:
            return []
    return wrapped


class Fixer:
    def rules(self):
        return [
            Rule(
                name="add_len_one_clause_for_tail_isupper",
                apply=_safe(rule_add_len_one_clause),
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_case_method_missing_call_parens",
                apply=_safe(rule_bare_attr_call),
                symptoms=("wrong",),
            ),
            Rule(
                name="upper_lower_used_as_boolean_should_be_isupper_islower",
                apply=_safe(rule_bool_truth_case_call),
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_should_be_swapcase",
                apply=_safe(rule_capitalize_to_swapcase),
                symptoms=("wrong",),
            ),
            Rule(
                name="invalid_uppercase_lowercase_method_name",
                apply=_safe(rule_invalid_case_method),
                symptoms=("err:AttributeError", "wrong"),
            ),
            Rule(
                name="tailslice_islower_should_be_isupper",
                apply=_safe(rule_islower_should_be_isupper_tailslice),
                symptoms=("wrong",),
            ),
        ]