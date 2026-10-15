import ast
import re

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


def _normalize(text):
    return re.sub(r"\s+", "", text)


def _test_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _find_input_var(tree):
    """Find `NAME = input()` (optionally `.strip()` chained) at module level."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            v = node.value
            while isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute):
                v = v.func.value
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "input":
                return node.targets[0].id, node
    return None, None


def _trailing(tree, assign_node):
    """Statements after the input-reading assignment, at module level."""
    body = tree.body
    try:
        idx = body.index(assign_node)
    except ValueError:
        return None
    rest = body[idx + 1:]
    if not rest:
        return None
    # Don't touch programs that wrap the logic in a function/class -- too risky
    # to splice safely without covering a whole FunctionDef body.
    if any(isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for s in rest):
        return None
    return rest


CANON_FMT = "if {v}[1:]=={v}[1:].upper():\n    print({v}.swapcase())\nelse:\n    print({v})"


def _canonical_patch(source, rest, varname):
    s, _ = _span(source, rest[0])
    _, e = _span(source, rest[-1])
    new_text = CANON_FMT.format(v=varname)
    patch = source[:s] + new_text + source[e:]
    if patch == source:
        return None
    return patch


def _canon_variants(v):
    return {
        f"{v}[1:]=={v}[1:].upper()",
        f"{v}[1:].upper()=={v}[1:]",
    }


def _rule_no_condition_case_flip(source):
    """
    Programs that read a word and unconditionally call .capitalize()/.swapcase()
    on it (no branching at all), e.g. `print(s.swapcase())` or
    `res = s.capitalize(); print(res)`. Replace the whole unconditional logic
    with the canonical conditional transform.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    v, assign = _find_input_var(tree)
    if v is None:
        return []
    rest = _trailing(tree, assign)
    if not rest:
        return []
    if any(isinstance(n, ast.If) for n in rest):
        return []
    has_case_call = False
    for n in rest:
        for sub in ast.walk(n):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
               and sub.func.attr in ("swapcase", "capitalize"):
                has_case_call = True
                break
        if has_case_call:
            break
    if not has_case_call:
        return []
    patch = _canonical_patch(source, rest, v)
    return [patch] if patch else []


def _rule_wrong_if_condition(source):
    """
    Programs whose main branch is an `if` (possibly elif/else chain) that
    tests truthiness of a bare `.lower()/.upper()/.isupper()/.islower()` call
    (or a BoolOp of such calls), or compares the wrong operands, instead of
    comparing `word[1:]` to its own `.upper()`. Replace the whole decision
    block (and anything depending on it) with the canonical comparison.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    v, assign = _find_input_var(tree)
    if v is None:
        return []
    rest = _trailing(tree, assign)
    if not rest:
        return []
    if_node = next((n for n in rest if isinstance(n, ast.If)), None)
    if if_node is None:
        return []
    test = if_node.test
    if isinstance(test, ast.Compare):
        norm = _normalize(_test_text(source, test))
        if norm in _canon_variants(v):
            return []
    patch = _canonical_patch(source, rest, v)
    return [patch] if patch else []


def _rule_loop_attempt(source):
    """
    Programs that try to detect the caps-lock pattern with a manual
    for/while loop (counting letters, scanning indices, etc). Replace the
    whole loop-based attempt (and trailing logic) with the canonical check.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    v, assign = _find_input_var(tree)
    if v is None:
        return []
    rest = _trailing(tree, assign)
    if not rest:
        return []
    if not any(isinstance(n, (ast.For, ast.While)) for n in rest):
        return []
    patch = _canonical_patch(source, rest, v)
    return [patch] if patch else []


class Fixer:
    def rules(self):
        return [
            Rule(
                name="capslock_unconditional_case_flip",
                apply=_rule_no_condition_case_flip,
                symptoms=("wrong",),
            ),
            Rule(
                name="capslock_wrong_if_condition",
                apply=_rule_wrong_if_condition,
                symptoms=("wrong", "err:AttributeError"),
            ),
            Rule(
                name="capslock_loop_based_attempt",
                apply=_rule_loop_attempt,
                symptoms=("wrong", "timeout"),
            ),
        ]