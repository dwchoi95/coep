"""Repair module for the cAPS lOCK (Codeforces 131A) assignment.

Each Rule below targets one recurring misconception seen across buggy
submissions for this problem, and edits only the offending sub-expression
in place (via source-span splicing), leaving everything else untouched.
"""

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


def _build_parent_map(tree):
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _is_bool_context(node, parent):
    if parent is None:
        return False
    if isinstance(parent, ast.BoolOp) and node in parent.values:
        return True
    if isinstance(parent, ast.If) and parent.test is node:
        return True
    if isinstance(parent, ast.While) and parent.test is node:
        return True
    if isinstance(parent, ast.IfExp) and parent.test is node:
        return True
    if isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.Not) and parent.operand is node:
        return True
    if isinstance(parent, ast.Assert) and parent.test is node:
        return True
    return False


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source)
        except SyntaxError:
            return []
        except Exception:
            return []
    return wrapped


@_safe
def _rule_slice_case_to_equality(source):
    """`slice.isupper()`/`slice.islower()` fails on empty slices (single
    char words). Replace with the equality form that behaves correctly
    even when the slice is empty, and also fixes the common isupper/
    islower mix-up on the tail slice."""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and not node.args and not node.keywords
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("isupper", "islower")
                and isinstance(node.func.value, ast.Subscript)):
            value = node.func.value
            vs, ve = _span(source, value)
            value_text = source[vs:ve]
            new_text = "%s.upper() == %s" % (value_text, value_text)
            candidate = _splice(source, node, new_text)
            if candidate != source:
                out.append(candidate)
    return out


@_safe
def _rule_capitalize_title_to_swapcase(source):
    """`.capitalize()` / `.title()` used where case-toggling (`.swapcase()`)
    was intended."""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and not node.args and not node.keywords
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("capitalize", "title")):
            fs, fe = _span(source, node.func)
            attr_len = len(node.func.attr)
            attr_s = fe - attr_len
            candidate = source[:attr_s] + "swapcase" + source[fe:]
            if candidate != source:
                out.append(candidate)
    return out


@_safe
def _rule_add_missing_parens(source):
    """`x.isupper` / `x.islower` etc. used without calling them - always
    truthy (bound method), never actually checks anything."""
    tree = ast.parse(source)
    parents = _build_parent_map(tree)
    out = []
    targets = {"isupper", "islower", "isalpha", "istitle", "isdigit"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in targets:
            parent = parents.get(node)
            if isinstance(parent, ast.Call) and parent.func is node:
                continue
            s, e = _span(source, node)
            candidate = source[:e] + "()" + source[e:]
            if candidate != source:
                out.append(candidate)
    return out


@_safe
def _rule_upper_lower_bool_to_ischeck(source):
    """`.upper()`/`.lower()` (case-conversion, always truthy for a
    non-empty string) used directly as a boolean condition where a case
    *check* (`.isupper()`/`.islower()`) was intended."""
    tree = ast.parse(source)
    parents = _build_parent_map(tree)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and not node.args and not node.keywords
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("upper", "lower")):
            parent = parents.get(node)
            if _is_bool_context(node, parent):
                new_attr = "isupper" if node.func.attr == "upper" else "islower"
                fs, fe = _span(source, node.func)
                attr_len = len(node.func.attr)
                attr_s = fe - attr_len
                candidate = source[:attr_s] + new_attr + source[fe:]
                if candidate != source:
                    out.append(candidate)
    return out


@_safe
def _rule_wrap_len1(source):
    """An `if` condition built around `var.isupper()`/`var.islower()`
    checks but with no `len(...)` special-casing at all misses the
    single-character-word edge case. Wrap the whole test with an
    explicit `len(var) == 1 or (...)` clause."""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            has_len = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "len"
                for n in ast.walk(test)
            )
            if has_len:
                continue
            varname = None
            for n in ast.walk(test):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr in ("isupper", "islower")
                        and isinstance(n.func.value, ast.Name)):
                    varname = n.func.value.id
                    break
            if varname is None:
                continue
            ts, te = _span(source, test)
            test_text = source[ts:te]
            new_test = "(len(%s) == 1 or (%s))" % (varname, test_text)
            candidate = source[:ts] + new_test + source[te:]
            if candidate != source:
                out.append(candidate)
    return out


@_safe
def _rule_typo_uppercase(source):
    """`.uppercase()` is not a real str method (typo for `.upper()`),
    causes AttributeError at run time."""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "uppercase":
            s, e = _span(source, node)
            attr_len = len(node.attr)
            attr_s = e - attr_len
            candidate = source[:attr_s] + "upper" + source[e:]
            if candidate != source:
                out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="slice_case_check_to_equality",
                apply=_rule_slice_case_to_equality,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_title_to_swapcase",
                apply=_rule_capitalize_title_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_missing_call_parens",
                apply=_rule_add_missing_parens,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="upper_lower_bool_to_ischeck",
                apply=_rule_upper_lower_bool_to_ischeck,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrap_len1_missing_edge_case",
                apply=_rule_wrap_len1,
                symptoms=("wrong",),
            ),
            Rule(
                name="typo_uppercase_to_upper",
                apply=_rule_typo_uppercase,
                symptoms=("err:AttributeError",),
            ),
        ]