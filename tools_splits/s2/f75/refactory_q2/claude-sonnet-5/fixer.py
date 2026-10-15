"""
Repair rules for the "Unique dates and months" assignment.

Targets recurring misconceptions seen across many buggy submissions:

1. A function parameter (e.g. ``date``/``day``/``month``) is compared against a
   *different, undefined* identifier inside the body (NameError), or a locally
   defined variable is referenced under a typo'd name (``conter`` instead of
   ``counter``, ``unique_date`` instead of ``unique_day``, ``possible_birthday``
   instead of ``possible_birthdays``, lowercase ``true``/``false`` instead of
   the keywords). We rename the undefined use(s) to the closest bound name.

2. ``unique_day``/``unique_month`` compute a match counter correctly but test
   it with the wrong threshold/operator (``<=1``, ``>=2``, ``>1`` ...) instead
   of the correct ``== 1`` (or its complement ``!= 1`` when the branch sense is
   flipped). We normalize the comparison operator/constant in place.

3. A ``for`` loop whose single ``if`` branch returns ``True`` is paired with an
   ``else: return False`` that fires on the *first* non-matching element,
   terminating the loop prematurely instead of continuing to examine the rest
   of the collection. We drop the premature ``else`` branch and (if needed)
   append an unconditional ``return False`` after the loop.

4. A function whose body ends with a bare ``for`` loop (no trailing return)
   silently returns ``None`` instead of ``False`` when no match is found. We
   append a trailing ``return False`` after such a loop.
"""

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


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _levenshtein(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[lb]


_BUILTINS = {
    'True', 'False', 'None', 'len', 'range', 'str', 'int', 'float', 'bool',
    'list', 'tuple', 'dict', 'set', 'enumerate', 'map', 'filter', 'sum',
    'any', 'all', 'sorted', 'print', 'zip', 'reversed', 'isinstance', 'type',
    'min', 'max', 'abs', 'round', 'input',
}

_DAYLIKE = {'day', 'date', 'days', 'dates'}
_MONTHLIKE = {'month', 'months'}


def fix_undefined_names(source):
    """Rename undefined / typo'd identifiers to the closest bound name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)
    module_funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

    out = []
    seen = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = [a.arg for a in fn.args.args]
        bound = set(params)
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                bound.add(node.id)

        candidate_pool = bound | module_funcs | _BUILTINS

        first_param = None
        for p in params:
            if p != "possible_birthdays":
                first_param = p
                break

        undefined_nodes = {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in candidate_pool:
                    continue
                undefined_nodes.setdefault(node.id, []).append(node)

        for uid, nodes in undefined_nodes.items():
            target = None

            if fn.name in ("unique_day", "unique_month") and first_param:
                if uid in _DAYLIKE or uid in _MONTHLIKE:
                    target = first_param

            if target is None:
                best = None
                bestd = 999
                for cand in candidate_pool:
                    if not cand or cand[0].isupper() and cand not in ("True", "False", "None"):
                        pass
                    d = _levenshtein(uid, cand)
                    if 0 < d < bestd:
                        bestd = d
                        best = cand
                if best is not None and bestd <= 2:
                    target = best

            if target is None or target == uid:
                continue

            key = (fn.name, fn.lineno, uid, target)
            if key in seen:
                continue
            seen.add(key)

            ordered = sorted(nodes, key=lambda n: _span(source, n)[0], reverse=True)
            new_src = source
            for n in ordered:
                s, e = _span(source, n)
                new_src = new_src[:s] + target + new_src[e:]
            if new_src != source:
                out.append(new_src)
    return out


def fix_uniqueness_threshold(source):
    """Normalize count-threshold comparisons inside unique_day/unique_month."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)

    out = []
    for fn in ast.walk(tree):
        if not (isinstance(fn, ast.FunctionDef) and fn.name in ("unique_day", "unique_month")):
            continue
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.left, ast.Name)):
                continue
            comparator = node.comparators[0]
            if not (isinstance(comparator, ast.Constant)
                    and isinstance(comparator.value, int)
                    and not isinstance(comparator.value, bool)):
                continue

            op = node.ops[0]
            already_ok = isinstance(op, ast.Eq) and comparator.value == 1
            if already_ok:
                continue

            parent = getattr(node, "parent", None)
            new_text = None

            if isinstance(parent, ast.Return):
                new_text = f"{node.left.id} == 1"
            elif isinstance(parent, ast.If) and parent.test is node:
                if parent.body and isinstance(parent.body[0], ast.Return):
                    rv = parent.body[0].value
                    if isinstance(rv, ast.Constant) and rv.value is True:
                        new_text = f"{node.left.id} == 1"
                    elif isinstance(rv, ast.Constant) and rv.value is False:
                        new_text = f"{node.left.id} != 1"

            if new_text is not None:
                candidate = _splice(source, node, new_text)
                if candidate != source:
                    out.append(candidate)
    return out


def drop_premature_else_return(source):
    """Remove an else:-return that short-circuits a for-loop after one miss."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.If):
            continue
        ifnode = node.body[0]
        if not ifnode.orelse:
            continue
        if not (len(ifnode.orelse) == 1 and isinstance(ifnode.orelse[0], ast.Return)):
            continue
        if not ifnode.body:
            continue

        end_if_body = _span(source, ifnode.body[-1])[1]
        end_if_full = _span(source, ifnode)[1]
        if end_if_full <= end_if_body:
            continue

        new_source = source[:end_if_body] + source[end_if_full:]

        parent = getattr(node, "parent", None)
        parent_body = None
        if parent is not None:
            for attr in ("body", "orelse", "finalbody"):
                lst = getattr(parent, attr, None)
                if isinstance(lst, list) and node in lst:
                    parent_body = lst
                    break

        is_last = parent_body is not None and parent_body[-1] is node
        if is_last:
            end_for = _span(source, node)[1]
            removed = end_if_full - end_if_body
            new_end_for = end_for - removed
            indent = " " * node.col_offset
            new_source = (new_source[:new_end_for] + "\n" + indent + "return False"
                          + new_source[new_end_for:])

        if new_source != source:
            out.append(new_source)
    return out


def append_missing_return_false(source):
    """Append a trailing return False when a function falls off a bare for-loop."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for fn in ast.walk(tree):
        if not (isinstance(fn, ast.FunctionDef) and fn.body):
            continue
        last = fn.body[-1]
        if isinstance(last, ast.For) and not last.orelse:
            s, e = _span(source, last)
            indent = " " * last.col_offset
            new_source = source[:e] + "\n" + indent + "return False" + source[e:]
            if new_source != source:
                out.append(new_source)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_undefined_or_typo_name",
                apply=fix_undefined_names,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="normalize_uniqueness_threshold",
                apply=fix_uniqueness_threshold,
                symptoms=("wrong",),
            ),
            Rule(
                name="drop_premature_else_return_in_loop",
                apply=drop_premature_else_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="append_missing_return_false",
                apply=append_missing_return_false,
                symptoms=("wrong",),
            ),
        ]