"""
Repair rules for the "unique dates and months" assignment.

Targets recurring misconceptions seen in buggy submissions for
unique_day / unique_month / contains_unique_day:

  * typo / undefined-name references that are a near-miss of a real
    parameter or variable name,
  * confusing the running counter with the function's own parameter
    (comparing against the counter instead of the argument, or
    incrementing an unrelated/undefined name instead of the counter),
  * mixing up the month-index (0) and day-index (1) inside the wrong
    function,
  * the "count > 1 => False else True" idiom that silently returns
    True when the count is zero instead of checking count == 1,
  * contains_unique_day requiring an exact count of 1 instead of
    "at least one" (existence) ,
  * contains_unique_day calling unique_day with the filtered
    month-subset instead of the full birthdays list.
"""

import ast
import re
import builtins as _builtins

from src.core.repair import Rule


BUILTIN_NAMES = set(dir(_builtins)) | {"True", "False", "None"}


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


def _is_int_const(node, val):
    return isinstance(node, ast.Constant) and type(node.value) is int and node.value == val


def _functions(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


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
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (0 if a[i - 1] == b[j - 1] else 1))
            prev = cur
    return dp[lb]


def _collect_bound_names(module_tree, func_node):
    names = set()
    for n in ast.walk(func_node):
        if isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.add(n.id)
        elif isinstance(n, ast.FunctionDef):
            names.add(n.name)
    for n in ast.walk(module_tree):
        if isinstance(n, ast.FunctionDef):
            names.add(n.name)
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    names |= BUILTIN_NAMES
    return names


# ---------------------------------------------------------------------------
# Rule 1: undefined name that is a near-miss typo of a real bound name.
# ---------------------------------------------------------------------------

def fix_typo_undefined_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    seen = set()
    try:
        for func in _functions(tree):
            bound = _collect_bound_names(tree, func)
            for node in ast.walk(func):
                if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)):
                    continue
                if node.id in bound or len(node.id) < 3:
                    continue
                candidates = [
                    b for b in bound
                    if b not in BUILTIN_NAMES and b != node.id
                    and abs(len(node.id) - len(b)) <= 2
                    and _levenshtein(node.id, b) <= 2
                ]
                if len(candidates) == 1:
                    key = (node.lineno, node.col_offset, candidates[0])
                    if key in seen:
                        continue
                    seen.add(key)
                    cand = _splice(source, node, candidates[0])
                    if cand != source:
                        out.append(cand)
    except Exception:
        return out
    return out


# ---------------------------------------------------------------------------
# Rule 2: counter variable confused with the parameter being counted,
# and/or the increment step touches the wrong (often undefined) name.
# ---------------------------------------------------------------------------

def fix_counter_variable_confusion(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    try:
        for func in _functions(tree):
            if func.name not in ("unique_day", "unique_month") or not func.args.args:
                continue
            param_name = func.args.args[0].arg

            acc_name = None
            for stmt in func.body:
                if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and _is_int_const(stmt.value, 0)):
                    acc_name = stmt.targets[0].id
                    break
            if acc_name is None:
                continue

            confirmed = False
            for node in ast.walk(func):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                    sides = [node.left] + node.comparators
                    names = [s for s in sides if isinstance(s, ast.Name)]
                    if any(nm.id == acc_name for nm in names) and \
                       any(_is_int_const(s, 1) for s in sides):
                        confirmed = True
                        break
            if not confirmed:
                continue

            for_node = None
            for stmt in func.body:
                if isinstance(stmt, ast.For):
                    for_node = stmt
                    break
            if for_node is None:
                continue

            for node in ast.walk(for_node):
                if not isinstance(node, ast.If):
                    continue
                cmp_fix = None
                test = node.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                    sides = [test.left] + test.comparators
                    name_sides = [s for s in sides if isinstance(s, ast.Name)]
                    sub_sides = [s for s in sides if isinstance(s, ast.Subscript)]
                    if len(name_sides) == 1 and len(sub_sides) == 1 and name_sides[0].id == acc_name:
                        cmp_fix = name_sides[0]

                incr_fix = None
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name)
                            and isinstance(sub.op, ast.Add) and _is_int_const(sub.value, 1)):
                        if sub.target.id != acc_name:
                            incr_fix = (sub, sub.target.id)
                    elif (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                          and isinstance(sub.targets[0], ast.Name)
                          and isinstance(sub.value, ast.BinOp) and isinstance(sub.value.op, ast.Add)):
                        tgt = sub.targets[0].id
                        l, r = sub.value.left, sub.value.right
                        is_plus_one = (_is_int_const(r, 1) and isinstance(l, ast.Name) and l.id == tgt) or \
                                      (_is_int_const(l, 1) and isinstance(r, ast.Name) and r.id == tgt)
                        if is_plus_one and tgt != acc_name:
                            incr_fix = (sub, tgt)

                if cmp_fix is None and incr_fix is None:
                    continue

                edits = []
                if cmp_fix is not None:
                    s, e = _span(source, cmp_fix)
                    edits.append((s, e, param_name))
                if incr_fix is not None:
                    stmt_node, wrong = incr_fix
                    s, e = _span(source, stmt_node)
                    seg = source[s:e]
                    new_seg = re.sub(r'\b' + re.escape(wrong) + r'\b', acc_name, seg)
                    if new_seg != seg:
                        edits.append((s, e, new_seg))

                if not edits:
                    continue

                if len(edits) == 2:
                    combined = source
                    for s, e, txt in sorted(edits, key=lambda x: -x[0]):
                        combined = combined[:s] + txt + combined[e:]
                    if combined != source:
                        out.append(combined)

                for s, e, txt in edits:
                    cand = source[:s] + txt + source[e:]
                    if cand != source:
                        out.append(cand)
    except Exception:
        return out
    return out


# ---------------------------------------------------------------------------
# Rule 3: `if counter == 1: return True/False` style check where the
# running counter ended up indexed with the wrong tuple position
# (month-check using index 1, day-check using index 0).
# ---------------------------------------------------------------------------

def _const_index(node):
    if isinstance(node, ast.Index):
        node = node.value
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    return None


def _slice_node_and_span_target(node):
    if isinstance(node, ast.Index):
        return node.value
    return node


def _name_of_slice(node):
    inner = node
    if isinstance(inner, ast.Index):
        inner = inner.value
    return inner.id if isinstance(inner, ast.Name) else None


def fix_month_day_index_swap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    try:
        for func in _functions(tree):
            if func.name not in ("unique_day", "unique_month"):
                continue
            args = func.args.args
            if len(args) < 2:
                continue
            list_param = args[1].arg
            wrong_index = 1 if func.name == "unique_month" else 0
            correct_index = 0 if func.name == "unique_month" else 1

            item_vars = set()
            idx_vars = set()
            for n in ast.walk(func):
                if isinstance(n, ast.For):
                    if isinstance(n.iter, ast.Name) and n.iter.id == list_param and isinstance(n.target, ast.Name):
                        item_vars.add(n.target.id)
                    if (isinstance(n.iter, ast.Call) and isinstance(n.iter.func, ast.Name)
                            and n.iter.func.id == "range" and n.iter.args):
                        a0 = n.iter.args[0]
                        if (isinstance(a0, ast.Call) and isinstance(a0.func, ast.Name)
                                and a0.func.id == "len" and a0.args
                                and isinstance(a0.args[0], ast.Name) and a0.args[0].id == list_param
                                and isinstance(n.target, ast.Name)):
                            idx_vars.add(n.target.id)

            for n in ast.walk(func):
                if not isinstance(n, ast.Subscript):
                    continue
                idxval = _const_index(n.slice)
                if idxval != wrong_index:
                    continue
                base = n.value
                is_item = isinstance(base, ast.Name) and base.id in item_vars
                is_idx_sub = (isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name)
                              and base.value.id == list_param and _name_of_slice(base.slice) in idx_vars)
                if not (is_item or is_idx_sub):
                    continue
                sl = _slice_node_and_span_target(n.slice)
                s, e = _span(source, sl)
                cand = source[:s] + str(correct_index) + source[e:]
                if cand != source:
                    out.append(cand)
    except Exception:
        return out
    return out


# ---------------------------------------------------------------------------
# Rule 4: `if acc > 1: return False else: return True` never returns
# False when acc == 0. Rewrite as `return acc == 1`.
# ---------------------------------------------------------------------------

def fix_threshold_if_else(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    try:
        for func in _functions(tree):
            init_zero = set()
            for n in ast.walk(func):
                if (isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name) and _is_int_const(n.value, 0)):
                    init_zero.add(n.targets[0].id)

            for node in ast.walk(func):
                if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                        and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Gt)):
                    continue
                left, right = node.test.left, node.test.comparators[0]
                if not (isinstance(left, ast.Name) and _is_int_const(right, 1)):
                    continue
                acc = left.id
                if acc not in init_zero:
                    continue
                if not (len(node.body) == 1 and isinstance(node.body[0], ast.Return)
                        and isinstance(node.body[0].value, ast.Constant)
                        and node.body[0].value.value is False):
                    continue
                if not (len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return)
                        and isinstance(node.orelse[0].value, ast.Constant)
                        and node.orelse[0].value.value is True):
                    continue
                cand = _splice(source, node, "return {} == 1".format(acc))
                if cand != source:
                    out.append(cand)
    except Exception:
        return out
    return out


# ---------------------------------------------------------------------------
# Rule 5: a loop counts matches but the function unconditionally
# `return True`s afterwards, so zero matches is wrongly "unique".
# ---------------------------------------------------------------------------

def fix_zero_match_return_true(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    try:
        for func in _functions(tree):
            body = func.body
            if not body:
                continue
            last = body[-1]
            if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                    and last.value.value is True):
                continue

            acc = None
            for stmt in body:
                if not isinstance(stmt, ast.For):
                    continue
                for sub in ast.walk(stmt):
                    if (isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name)
                            and isinstance(sub.op, ast.Add) and _is_int_const(sub.value, 1)):
                        acc = sub.target.id
                        break
                    if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                            and isinstance(sub.targets[0], ast.Name)
                            and isinstance(sub.value, ast.BinOp) and isinstance(sub.value.op, ast.Add)):
                        tgt = sub.targets[0].id
                        l, r = sub.value.left, sub.value.right
                        if (_is_int_const(r, 1) and isinstance(l, ast.Name) and l.id == tgt) or \
                           (_is_int_const(l, 1) and isinstance(r, ast.Name) and r.id == tgt):
                            acc = tgt
                            break
                if acc:
                    break
            if acc is None:
                continue
            cand = _splice(source, last, "return {} == 1".format(acc))
            if cand != source:
                out.append(cand)
    except Exception:
        return out
    return out


# ---------------------------------------------------------------------------
# Rule 6: contains_unique_day requires the count of qualifying days to
# equal exactly 1 instead of checking existence (count > 0).
# ---------------------------------------------------------------------------

def fix_contains_exact_one_to_exists(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    try:
        for func in _functions(tree):
            if func.name != "contains_unique_day":
                continue
            for node in ast.walk(func):
                if not (isinstance(node, ast.Compare) and len(node.ops) == 1
                        and isinstance(node.ops[0], ast.Eq)):
                    continue
                sides = [node.left] + node.comparators
                names = [s for s in sides if isinstance(s, ast.Name)]
                consts = [s for s in sides if _is_int_const(s, 1)]
                if len(names) == 1 and len(consts) == 1:
                    cand = _splice(source, node, "{} > 0".format(names[0].id))
                    if cand != source:
                        out.append(cand)
    except Exception:
        return out
    return out


# ---------------------------------------------------------------------------
# Rule 7: contains_unique_day calls unique_day with the filtered
# month-subset instead of the full possible_birthdays list.
# ---------------------------------------------------------------------------

def fix_wrong_list_arg_to_unique_day(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    try:
        for func in _functions(tree):
            if func.name != "contains_unique_day" or len(func.args.args) < 2:
                continue
            param2 = func.args.args[1].arg
            for node in ast.walk(func):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "unique_day" and len(node.args) >= 2):
                    continue
                arg2 = node.args[1]
                if isinstance(arg2, ast.Name) and arg2.id != param2:
                    cand = _splice(source, arg2, param2)
                    if cand != source:
                        out.append(cand)
    except Exception:
        return out
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="typo_undefined_name_near_match",
                apply=fix_typo_undefined_name,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="counter_variable_confusion",
                apply=fix_counter_variable_confusion,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="month_day_index_swap",
                apply=fix_month_day_index_swap,
                symptoms=("wrong",),
            ),
            Rule(
                name="threshold_if_else_zero_match",
                apply=fix_threshold_if_else,
                symptoms=("wrong",),
            ),
            Rule(
                name="loop_then_unconditional_return_true",
                apply=fix_zero_match_return_true,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_exact_one_vs_exists",
                apply=fix_contains_exact_one_to_exists,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_wrong_list_arg",
                apply=fix_wrong_list_arg_to_unique_day,
                symptoms=("wrong",),
            ),
        ]