"""
Repair module for the "Unique dates and months" assignment.

Each rule below targets a specific, commonly-observed misconception in
student submissions for unique_day / unique_month / contains_unique_day,
and produces small, localized source-span edits (never whole-function
rewrites).
"""

import ast
import builtins
import keyword

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# Generic AST helpers
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


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source) or []
        except Exception:
            return []
    wrapped.__name__ = getattr(fn, "__name__", "rule")
    return wrapped


def _edit_distance(a, b):
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


_BUILTIN_NAMES = set(dir(builtins)) | {"True", "False", "None"}


def _index_value(slice_node):
    """Return the Constant int node of a subscript slice, handling py3.8/3.9+."""
    n = slice_node
    if isinstance(n, ast.Index):  # python < 3.9
        n = n.value
    if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
        return n
    return None


def _is_const(node, value):
    return isinstance(node, ast.Constant) and node.value is value


def _collect_bound_names(func):
    bound = set()
    try:
        bound |= {a.arg for a in func.args.args}
        bound |= {a.arg for a in getattr(func.args, "posonlyargs", [])}
        bound |= {a.arg for a in func.args.kwonlyargs}
        if func.args.vararg:
            bound.add(func.args.vararg.arg)
        if func.args.kwarg:
            bound.add(func.args.kwarg.arg)
    except Exception:
        pass
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                        bound.add(n.id)
        elif isinstance(node, ast.For):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    bound.add(n.id)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for gen in node.generators:
                for n in ast.walk(gen.target):
                    if isinstance(n, ast.Name):
                        bound.add(n.id)
        elif isinstance(node, ast.FunctionDef) and node is not func:
            bound.add(node.name)
    return bound


# ---------------------------------------------------------------------------
# Rule 1: undefined-identifier typo fix (day/date mismatch, misspelled
# accumulator names, lowercase true/Flase, etc.)
# ---------------------------------------------------------------------------

def _fix_free_variable_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    top_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    seen = set()
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        bound = _collect_bound_names(func)
        pool = set(bound) | {"True", "False", "None"}

        free_nodes = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Name):
                if node.id in pool or node.id in top_funcs:
                    continue
                if node.id in _BUILTIN_NAMES or keyword.iskeyword(node.id):
                    continue
                if isinstance(node.ctx, ast.Load):
                    free_nodes.setdefault(node.id, []).append(node)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                nid = node.target.id
                if nid in pool or nid in top_funcs or nid in _BUILTIN_NAMES:
                    continue
                free_nodes.setdefault(nid, []).append(node.target)

        for bad_name, nodes in free_nodes.items():
            if len(bad_name) < 3:
                continue
            best, best_d = None, 999
            for cand in pool:
                if len(cand) < 2:
                    continue
                d = _edit_distance(bad_name, cand)
                if d < best_d:
                    best_d, best = d, cand
            if best is None or best_d == 0 or best_d > 2:
                continue
            key = (func.name, bad_name, best)
            if key in seen:
                continue
            seen.add(key)
            spans = sorted((_span(source, n) for n in nodes), key=lambda x: -x[0])
            new_source = source
            for s, e in spans:
                new_source = new_source[:s] + best + new_source[e:]
            out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 2: self-referential dead accumulator (`day = day + 1` when the real
# counter is `days`) -> rename to the real zero-initialized accumulator.
# ---------------------------------------------------------------------------

def _fix_self_referential_counter(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        zero_inits = []
        assign_count = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                tgt = node.targets[0].id
                assign_count[tgt] = assign_count.get(tgt, 0) + 1
                if isinstance(node.value, ast.Constant) and node.value.value == 0:
                    zero_inits.append(tgt)
        for node in ast.walk(func):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                continue
            tgt = node.targets[0].id
            if tgt in zero_inits:
                continue
            if assign_count.get(tgt, 0) != 1:
                continue
            names_in_value = [n for n in ast.walk(node.value)
                               if isinstance(n, ast.Name) and n.id == tgt]
            if not names_in_value:
                continue
            best, best_d = None, 999
            for z in zero_inits:
                d = _edit_distance(tgt, z)
                if d < best_d:
                    best_d, best = d, z
            if best is None or best_d == 0 or best_d > 2:
                continue
            nodes_to_fix = [node.targets[0]] + names_in_value
            spans = sorted((_span(source, n) for n in nodes_to_fix), key=lambda x: -x[0])
            new_source = source
            for s, e in spans:
                new_source = new_source[:s] + best + new_source[e:]
            out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 3: wrong tuple-field index in equality comparisons
# (month compared against index 1 instead of 0, day/date against 0 instead
# of 1).
# ---------------------------------------------------------------------------

def _fix_tuple_index_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        for node in ast.walk(func):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.Eq)):
                continue
            left, right = node.left, node.comparators[0]
            for a, b in ((left, right), (right, left)):
                if not (isinstance(a, ast.Name) and a.id in params):
                    continue
                pname = a.id.lower()
                if "month" in pname:
                    expected = 0
                elif "day" in pname or "date" in pname:
                    expected = 1
                else:
                    continue
                if not isinstance(b, ast.Subscript):
                    continue
                idx_node = _index_value(b.slice)
                if idx_node is None:
                    continue
                if idx_node.value != expected:
                    s, e = _span(source, idx_node)
                    out.append(source[:s] + str(expected) + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 4: wrong tuple-field index passed as argument to unique_day/unique_month
# ---------------------------------------------------------------------------

def _fix_call_arg_index_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        fname = node.func.id
        if fname not in ("unique_day", "unique_month"):
            continue
        if not node.args:
            continue
        arg0 = node.args[0]
        if not isinstance(arg0, ast.Subscript):
            continue
        idx_node = _index_value(arg0.slice)
        if idx_node is None:
            continue
        expected = 1 if fname == "unique_day" else 0
        if idx_node.value != expected:
            s, e = _span(source, idx_node)
            out.append(source[:s] + str(expected) + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 5: accumulating a tuple without wrapping the element
# (`count = count + i` should be `count = count + (i,)`)
# ---------------------------------------------------------------------------

def _fix_tuple_concat_wrap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        zero_tuple_inits = set()
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Tuple) and len(node.value.elts) == 0):
                zero_tuple_inits.add(node.targets[0].id)

        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                tgt = node.targets[0].id
                if tgt not in zero_tuple_inits:
                    continue
                val = node.value
                if (isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add)
                        and isinstance(val.left, ast.Name) and val.left.id == tgt
                        and isinstance(val.right, ast.Name)):
                    right = val.right
                    s, e = _span(source, right)
                    new_text = "(" + source[s:e] + ",)"
                    out.append(_splice(source, right, new_text))
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                tgt = node.target.id
                if tgt not in zero_tuple_inits:
                    continue
                if isinstance(node.op, ast.Add) and isinstance(node.value, ast.Name):
                    right = node.value
                    s, e = _span(source, right)
                    new_text = "(" + source[s:e] + ",)"
                    out.append(_splice(source, right, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 6: loose relational threshold instead of exact-one check inside
# unique_day / unique_month (e.g. `counter <= 1`, `count >= 2`).
# ---------------------------------------------------------------------------

def _fix_threshold_comparison(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("unique_day", "unique_month"):
            continue
        for node in ast.walk(func):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
                continue
            op = node.ops[0]
            if not isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                continue
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and isinstance(right.value, int):
                s, e = _span(source, left)
                new_text = source[s:e] + " == 1"
                out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 7: contains_unique_day returns False on the very first non-matching
# iteration of its loop instead of continuing to the next candidate.
# ---------------------------------------------------------------------------

def _fix_premature_false_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != "contains_unique_day":
            continue
        body = func.body
        for idx, stmt in enumerate(body):
            if not isinstance(stmt, ast.For):
                continue
            if len(stmt.body) != 1 or not isinstance(stmt.body[0], ast.If):
                continue
            ifnode = stmt.body[0]
            if len(ifnode.body) != 1 or not isinstance(ifnode.body[0], ast.Return):
                continue
            if not _is_const(ifnode.body[0].value, True):
                continue
            if len(ifnode.orelse) != 1 or not isinstance(ifnode.orelse[0], ast.Return):
                continue
            if not _is_const(ifnode.orelse[0].value, False):
                continue

            test_s, test_e = _span(source, ifnode.test)
            test_text = source[test_s:test_e]
            indent = " " * ifnode.col_offset
            new_if_text = "if " + test_text + ":\n" + indent + "    return True"

            if_s, if_e = _span(source, ifnode)
            for_s, for_e = _span(source, stmt)

            need_return_false = True
            if idx + 1 < len(body):
                nxt = body[idx + 1]
                if isinstance(nxt, ast.Return) and _is_const(nxt.value, False):
                    need_return_false = False

            tail = ""
            if need_return_false:
                for_indent = " " * stmt.col_offset
                tail = "\n" + for_indent + "return False"

            new_source = source[:if_s] + new_if_text + source[if_e:for_e] + tail + source[for_e:]
            out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 8: boolean accumulator used via `tf = tf or ...` without ever being
# initialized before the loop -> insert `tf = False` before the loop.
# ---------------------------------------------------------------------------

def _fix_uninitialized_bool_accumulator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node

    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = {a.arg for a in func.args.args}
        assign_count = {}
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                tgt = node.targets[0].id
                assign_count[tgt] = assign_count.get(tgt, 0) + 1

        for node in ast.walk(func):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                continue
            tgt = node.targets[0].id
            if tgt in params:
                continue
            val = node.value
            if not (isinstance(val, ast.BoolOp) and isinstance(val.op, ast.Or) and val.values):
                continue
            first = val.values[0]
            if not (isinstance(first, ast.Name) and first.id == tgt):
                continue
            if assign_count.get(tgt, 0) != 1:
                continue

            anc = node
            for_node = None
            while anc in parent:
                anc = parent[anc]
                if isinstance(anc, ast.For):
                    for_node = anc
                if isinstance(anc, ast.FunctionDef):
                    break
            if for_node is None:
                continue

            indent = " " * for_node.col_offset
            insertion = indent + tgt + " = False\n"
            s, _e = _span(source, for_node)
            out.append(source[:s] + insertion + source[s:])
    return out


# ---------------------------------------------------------------------------
# Fixer
# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="free_variable_typo",
                apply=_safe(_fix_free_variable_typo),
                symptoms=("err:NameError", "err:UnboundLocalError", "wrong"),
            ),
            Rule(
                name="self_referential_counter_typo",
                apply=_safe(_fix_self_referential_counter),
                symptoms=("err:UnboundLocalError", "err:NameError", "wrong"),
            ),
            Rule(
                name="tuple_index_mismatch",
                apply=_safe(_fix_tuple_index_mismatch),
                symptoms=("wrong",),
            ),
            Rule(
                name="call_arg_index_mismatch",
                apply=_safe(_fix_call_arg_index_mismatch),
                symptoms=("wrong",),
            ),
            Rule(
                name="tuple_concat_wrap",
                apply=_safe(_fix_tuple_concat_wrap),
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="threshold_comparison_to_eq1",
                apply=_safe(_fix_threshold_comparison),
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_premature_false",
                apply=_safe(_fix_premature_false_return),
                symptoms=("wrong",),
            ),
            Rule(
                name="uninitialized_bool_accumulator",
                apply=_safe(_fix_uninitialized_bool_accumulator),
                symptoms=("err:NameError", "err:UnboundLocalError", "wrong"),
            ),
        ]