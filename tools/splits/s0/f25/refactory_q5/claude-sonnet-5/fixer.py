"""
Repair rules for the Top-K assignment.

Each rule targets a specific, recognizable misconception seen in student
submissions. Rules operate by locating an AST node and splicing a small,
local text edit into the original source - never by rewriting whole
functions.
"""

import ast
import re
import builtins

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

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


def _iter_bodies(tree):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            body = getattr(node, field, None)
            if isinstance(body, list):
                yield body


def _find_parent_body(tree, target):
    for body in _iter_bodies(tree):
        if target in body:
            return body
    return None


def _second_param_name(tree, fname):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fname:
            args = node.args.args
            if len(args) >= 2:
                return args[1].arg
    return None


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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Rule 1: wrong variable updated inside a max/min-tracking if-body
#   for i in lst: if i > biggest: oldest = i   ->   biggest = i
# ---------------------------------------------------------------------------

def fix_wrong_assign_target_in_if(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for body in _iter_bodies(tree):
        for idx, stmt in enumerate(body):
            if not isinstance(stmt, ast.For) or not isinstance(stmt.target, ast.Name):
                continue
            if idx == 0:
                continue
            prev = body[idx - 1]
            if not (isinstance(prev, ast.Assign) and len(prev.targets) == 1
                    and isinstance(prev.targets[0], ast.Name)):
                continue
            tracker = prev.targets[0].id
            for sub in stmt.body:
                if isinstance(sub, ast.If) and len(sub.body) == 1:
                    inner = sub.body[0]
                    if isinstance(inner, ast.Assign) and len(inner.targets) == 1 \
                       and isinstance(inner.targets[0], ast.Name) \
                       and isinstance(inner.value, ast.Name):
                        target_name = inner.targets[0].id
                        if target_name == tracker:
                            continue
                        names_in_cond = {n.id for n in ast.walk(sub.test)
                                          if isinstance(n, ast.Name)}
                        if tracker in names_in_cond:
                            s, e = _span(source, inner.targets[0])
                            out.append(source[:s] + tracker + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 2: an undefined (typo'd) name inside a function, where exactly one
# defined name in scope is a near-match (edit distance <= 2).
# ---------------------------------------------------------------------------

def fix_undefined_name_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    global_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        defined = set(a.arg for a in fn.args.args)
        for sub in ast.walk(fn):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                defined.add(sub.id)
            if isinstance(sub, ast.FunctionDef):
                defined.add(sub.name)

        groups = {}
        for sub in ast.walk(fn):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                if sub.id in defined or sub.id in global_funcs:
                    continue
                if hasattr(builtins, sub.id):
                    continue
                groups.setdefault(sub.id, []).append(sub)

        for bad_id, nodes in groups.items():
            candidates = [d for d in defined
                          if d != bad_id and _levenshtein(d, bad_id) <= 2]
            if len(candidates) != 1:
                continue
            repl = candidates[0]
            new_source = source
            for n in sorted(nodes, key=lambda nd: _span(source, nd)[0], reverse=True):
                s, e = _span(source, n)
                new_source = new_source[:s] + repl + new_source[e:]
            if new_source != source:
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 3: local variable shadows a function of the same name, called as
#   sort = sort(lst)
# causing UnboundLocalError. Rename just the local variable.
# ---------------------------------------------------------------------------

def fix_self_shadowing_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for stmt in fn.body:
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            varname = stmt.targets[0].id
            if varname not in func_names:
                continue
            if not (isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Name)
                    and stmt.value.func.id == varname):
                continue
            new_name = varname + "_result"
            call_func_node = stmt.value.func
            targets = [n for n in ast.walk(fn)
                       if isinstance(n, ast.Name) and n.id == varname and n is not call_func_node]
            if not targets:
                continue
            new_source = source
            for n in sorted(targets, key=lambda nd: _span(source, nd)[0], reverse=True):
                s, e = _span(source, n)
                new_source = new_source[:s] + new_name + new_source[e:]
            out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 4: `obj.pop[x]` used instead of `obj.pop(x)`
# ---------------------------------------------------------------------------

def fix_subscript_as_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr not in ("pop",):
                continue
            sl = node.slice
            if isinstance(sl, ast.Slice):
                continue
            if isinstance(sl, ast.Index):
                sl = sl.value
            vs, ve = _span(source, node.value)
            ss, se = _span(source, sl)
            new_text = source[vs:ve] + "(" + source[ss:se] + ")"
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 5: a counting `while n <= k:` loop that never increments `n`.
# ---------------------------------------------------------------------------

def fix_missing_increment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        left = test.left
        if not isinstance(left, ast.Name):
            continue
        var_name = left.id
        incremented = False
        for sub in node.body:
            if isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name) \
               and sub.target.id == var_name:
                incremented = True
            if isinstance(sub, ast.Assign):
                for t in sub.targets:
                    if isinstance(t, ast.Name) and t.id == var_name:
                        incremented = True
        if incremented or not node.body:
            continue
        last_stmt = node.body[-1]
        indent = " " * last_stmt.col_offset
        insertion = "\n" + indent + var_name + " += 1"
        s, e = _span(source, last_stmt)
        out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 6: `while len(acc) <= k:` (off-by-one) -> `while len(acc) < k:`
# ---------------------------------------------------------------------------

def fix_len_based_while_bound(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    k_param = _second_param_name(tree, "top_k")
    if k_param is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.LtE)):
            continue
        left = test.left
        right = test.comparators[0]
        if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) \
           and left.func.id == "len" and isinstance(right, ast.Name) and right.id == k_param:
            s, e = _span(source, test.ops[0])
            out.append(source[:s] + "<" + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 7: `while len(lst) > len(lst) - k:` should track the accumulator
# length against k instead.
# ---------------------------------------------------------------------------

def fix_len_diff_while_condition(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)):
            continue
        left, right = test.left, test.comparators[0]
        if not (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                and left.func.id == "len" and len(left.args) == 1
                and isinstance(left.args[0], ast.Name)):
            continue
        lst_name = left.args[0].id
        if not (isinstance(right, ast.BinOp) and isinstance(right.op, ast.Sub)):
            continue
        rl, rr = right.left, right.right
        if not (isinstance(rl, ast.Call) and isinstance(rl.func, ast.Name)
                and rl.func.id == "len" and len(rl.args) == 1
                and isinstance(rl.args[0], ast.Name) and rl.args[0].id == lst_name
                and isinstance(rr, ast.Name)):
            continue
        k_name = rr.id
        acc_name = None
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
               and sub.func.attr == "append" and isinstance(sub.func.value, ast.Name):
                acc_name = sub.func.value.id
        if not acc_name:
            continue
        new_test = "len(" + acc_name + ") != " + k_name
        out.append(_splice(source, test, new_test))
    return out


# ---------------------------------------------------------------------------
# Rule 8: `for i in range(k): res.append(max(lst))` forgets to remove the
# element, so the same max is appended k times.
# ---------------------------------------------------------------------------

def fix_missing_removal_after_max_append(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or len(node.body) != 1:
            continue
        stmt = node.body[0]
        if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and stmt.value.func.attr == "append"):
            continue
        args = stmt.value.args
        if not (len(args) == 1 and isinstance(args[0], ast.Call)
                and isinstance(args[0].func, ast.Name) and args[0].func.id == "max"
                and len(args[0].args) == 1 and isinstance(args[0].args[0], ast.Name)):
            continue
        lst_name = args[0].args[0].id
        indent = " " * stmt.col_offset
        insertion = "\n" + indent + lst_name + ".remove(max(" + lst_name + "))"
        s, e = _span(source, stmt)
        out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 9: statements that belong after the max-finding for-loop (remove the
# found element, append it) are misplaced inside the for-loop body, using
# the loop variable instead of the tracker variable.
# ---------------------------------------------------------------------------

def fix_misplaced_update_in_for(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        if len(node.body) < 2:
            continue
        first = node.body[0]
        if not isinstance(first, ast.If):
            continue
        extra = node.body[1:]
        loopvar = node.target.id
        ok = True
        for st in extra:
            if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)):
                ok = False
                break
            call = st.value
            arg_names = [a.id for a in call.args if isinstance(a, ast.Name)]
            if loopvar not in arg_names:
                ok = False
                break
        if not ok:
            continue
        tracker = None
        if len(first.body) == 1 and isinstance(first.body[0], ast.Assign) \
           and len(first.body[0].targets) == 1 \
           and isinstance(first.body[0].targets[0], ast.Name):
            tracker = first.body[0].targets[0].id
        if tracker is None or tracker == loopvar:
            continue
        first_end = _span(source, first)[1]
        for_end = _span(source, node)[1]
        for_indent = " " * node.col_offset
        new_block = ""
        for st in extra:
            s, e = _span(source, st)
            text = source[s:e]
            text = re.sub(r"\b" + re.escape(loopvar) + r"\b", tracker, text)
            new_block += "\n" + for_indent + text
        new_source = source[:first_end] + new_block + source[for_end:]
        out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 10: `return list.reverse(x)[...]` - reverse() mutates in place and
# returns None.
# ---------------------------------------------------------------------------

def fix_list_reverse_misuse(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript)):
            continue
        sub = node.value
        call = sub.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "reverse"
                and isinstance(call.func.value, ast.Name) and call.func.value.id == "list"
                and len(call.args) == 1 and isinstance(call.args[0], ast.Name)):
            continue
        varname = call.args[0].id
        sl = sub.slice
        if isinstance(sl, ast.Index):
            sl = sl.value
        ss, se = _span(source, sl)
        indent = " " * node.col_offset
        new_text = varname + ".reverse()\n" + indent + "return " + varname + "[" + source[ss:se] + "]"
        out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 11: off-by-one slice bound `[:k-1]` or `[:k+1]` -> `[:k]`
# ---------------------------------------------------------------------------

def fix_slice_bound_off_by_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    k_param = _second_param_name(tree, "top_k")
    if k_param is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Slice) and node.upper is not None):
            continue
        up = node.upper
        if isinstance(up, ast.BinOp) and isinstance(up.op, (ast.Add, ast.Sub)) \
           and isinstance(up.left, ast.Name) and up.left.id == k_param \
           and isinstance(up.right, ast.Constant) and up.right.value == 1:
            out.append(_splice(source, up, k_param))
    return out


# ---------------------------------------------------------------------------
# Rule 12: a single-level pivot partition (quicksort style) that never
# recurses into the `lower`/`higher` partitions.
# ---------------------------------------------------------------------------

def fix_partition_without_recursion(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        e = node.target.id
        ifs = [s for s in node.body if isinstance(s, ast.If)]
        if len(ifs) != 3:
            continue
        lower_name = mid_name = higher_name = None
        ops_seen = set()
        ok = True
        for ifstmt in ifs:
            test = ifstmt.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
                ok = False
                break
            left, op, right = test.left, test.ops[0], test.comparators[0]
            if not (isinstance(left, ast.Name) and left.id == e and isinstance(right, ast.Name)):
                ok = False
                break
            if len(ifstmt.body) != 1:
                ok = False
                break
            call_stmt = ifstmt.body[0]
            if not (isinstance(call_stmt, ast.Expr) and isinstance(call_stmt.value, ast.Call)):
                ok = False
                break
            call = call_stmt.value
            if not (isinstance(call.func, ast.Attribute) and call.func.attr == "append"
                    and isinstance(call.func.value, ast.Name)):
                ok = False
                break
            target_list = call.func.value.id
            if isinstance(op, ast.Lt):
                lower_name = target_list
                ops_seen.add("lt")
            elif isinstance(op, ast.Eq):
                mid_name = target_list
                ops_seen.add("eq")
            elif isinstance(op, ast.Gt):
                higher_name = target_list
                ops_seen.add("gt")
            else:
                ok = False
                break
        if not ok or ops_seen != {"lt", "eq", "gt"}:
            continue
        if not (lower_name and mid_name and higher_name):
            continue
        parent_body = _find_parent_body(tree, node)
        if parent_body is None:
            continue
        idx = parent_body.index(node)
        if idx + 1 >= len(parent_body):
            continue
        next_stmt = parent_body[idx + 1]
        if not isinstance(next_stmt, ast.Assign):
            continue
        names_in_val = {n.id for n in ast.walk(next_stmt.value) if isinstance(n, ast.Name)}
        if not (lower_name in names_in_val and mid_name in names_in_val
                and higher_name in names_in_val):
            continue
        indent = " " * node.col_offset
        helper_name = "_quicksort_helper"
        insertion = (
            indent + "if len(" + lower_name + ") > 1:\n"
            + indent + "    " + lower_name + " = " + helper_name + "(" + lower_name + ")\n"
            + indent + "if len(" + higher_name + ") > 1:\n"
            + indent + "    " + higher_name + " = " + helper_name + "(" + higher_name + ")\n"
        )
        s_next, _e_next = _span(source, next_stmt)
        new_source = source[:s_next] + insertion + source[s_next:]
        helper_def = (
            "def " + helper_name + "(_lst):\n"
            "    if len(_lst) <= 1:\n"
            "        return _lst\n"
            "    _p = _lst[0]\n"
            "    _low = [_x for _x in _lst if _x < _p]\n"
            "    _mid = [_x for _x in _lst if _x == _p]\n"
            "    _high = [_x for _x in _lst if _x > _p]\n"
            "    return " + helper_name + "(_low) + _mid + " + helper_name + "(_high)\n\n"
        )
        out.append(helper_def + new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 13: a min-tracking comparison (`<`) used where a max-tracking
# comparison (`>`) is needed to directly build a descending result.
# ---------------------------------------------------------------------------

def fix_min_tracking_should_be_max(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        loopvar = node.target.id
        for sub in ast.walk(node):
            if not isinstance(sub, ast.If):
                continue
            test = sub.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Lt)):
                continue
            left, right = test.left, test.comparators[0]
            if not (isinstance(left, ast.Name) and left.id == loopvar and isinstance(right, ast.Name)):
                continue
            tracker = right.id
            if len(sub.body) == 1 and isinstance(sub.body[0], ast.Assign) \
               and len(sub.body[0].targets) == 1:
                tnode = sub.body[0].targets[0]
                if isinstance(tnode, ast.Name) and tnode.id == tracker:
                    new_cmp = source[_span(source, left)[0]:_span(source, left)[1]] \
                              + " > " + source[_span(source, right)[0]:_span(source, right)[1]]
                    out.append(_splice(source, test, new_cmp))
    return out


# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="wrong_var_updated_in_max_tracking_if",
                apply=fix_wrong_assign_target_in_if,
                symptoms=("wrong",),
            ),
            Rule(
                name="undefined_name_typo",
                apply=fix_undefined_name_typo,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="local_var_shadows_function_name",
                apply=fix_self_shadowing_call,
                symptoms=("err:UnboundLocalError",),
            ),
            Rule(
                name="subscript_used_instead_of_call",
                apply=fix_subscript_as_call,
                symptoms=("err:TypeError",),
            ),
            Rule(
                name="missing_loop_counter_increment",
                apply=fix_missing_increment,
                symptoms=("timeout",),
            ),
            Rule(
                name="len_based_while_off_by_one",
                apply=fix_len_based_while_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="len_diff_while_condition",
                apply=fix_len_diff_while_condition,
                symptoms=("wrong", "timeout", "err:IndexError"),
            ),
            Rule(
                name="missing_removal_after_max_append",
                apply=fix_missing_removal_after_max_append,
                symptoms=("wrong",),
            ),
            Rule(
                name="misplaced_update_statements_in_for",
                apply=fix_misplaced_update_in_for,
                symptoms=("wrong", "err:ValueError"),
            ),
            Rule(
                name="list_reverse_misuse",
                apply=fix_list_reverse_misuse,
                symptoms=("err:TypeError",),
            ),
            Rule(
                name="slice_bound_off_by_one",
                apply=fix_slice_bound_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="partition_without_recursion",
                apply=fix_partition_without_recursion,
                symptoms=("wrong",),
            ),
            Rule(
                name="min_tracking_should_be_max",
                apply=fix_min_tracking_should_be_max,
                symptoms=("wrong",),
            ),
        ]