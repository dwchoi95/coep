"""
Repair rules for the Top-K assignment.

Each rule inspects the AST for a specific, narrow structural misconception
seen across buggy submissions and proposes a small, local text splice that
addresses it. Rules never rewrite whole functions; they only touch the
offending span(s).
"""

import ast
import builtins

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


def _levenshtein(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    dp = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        dp[i][0] = i
    for j in range(lb + 1):
        dp[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1,
                            dp[i][j - 1] + 1,
                            dp[i - 1][j - 1] + cost)
    return dp[la][lb]


# ---------------------------------------------------------------------------
# Rule 1: typo'd variable name (e.g. `new_lst` used where `new_list` was defined)
# ---------------------------------------------------------------------------
def fix_name_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    seen = set()
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        assigned = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                assigned.add(n.id)
            if isinstance(n, ast.arg):
                assigned.add(n.arg)
        for n in ast.walk(func):
            if not (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)):
                continue
            bad = n.id
            if bad in assigned or bad == func.name:
                continue
            if hasattr(builtins, bad):
                continue
            candidates = [a for a in assigned if _levenshtein(a, bad) == 1]
            if len(candidates) != 1:
                continue
            good = candidates[0]
            key = (func.name, bad, good)
            if key in seen:
                continue
            seen.add(key)
            targets = [t for t in ast.walk(func)
                       if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Load)
                       and t.id == bad]
            targets.sort(key=lambda t: (t.lineno, t.col_offset), reverse=True)
            new_source = source
            for t in targets:
                new_source = _splice(new_source, t, good)
            if new_source != source:
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 2: selection loop that tracks the MINIMUM when it should track the MAXIMUM
# ---------------------------------------------------------------------------
def flip_min_to_max_selection(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            if not (isinstance(s1, ast.Assign) and len(s1.targets) == 1
                    and isinstance(s1.targets[0], ast.Name)
                    and isinstance(s1.value, ast.Subscript)):
                continue
            extreme_name = s1.targets[0].id
            if not (isinstance(s2, ast.For) and isinstance(s2.target, ast.Name)):
                continue
            loop_var = s2.target.id
            for inner in s2.body:
                if not (isinstance(inner, ast.If) and isinstance(inner.test, ast.Compare)
                        and len(inner.test.ops) == 1):
                    continue
                test = inner.test
                left, right = test.left, test.comparators[0]
                op = test.ops[0]
                if not (isinstance(left, ast.Name) and isinstance(right, ast.Name)):
                    continue
                reassigns = (inner.body and isinstance(inner.body[0], ast.Assign)
                             and len(inner.body[0].targets) == 1
                             and isinstance(inner.body[0].targets[0], ast.Name)
                             and inner.body[0].targets[0].id == extreme_name)
                if not reassigns:
                    continue
                new_op = None
                if left.id == loop_var and right.id == extreme_name and isinstance(op, ast.Lt):
                    new_op = ">"
                elif left.id == extreme_name and right.id == loop_var and isinstance(op, ast.Gt):
                    new_op = "<"
                if new_op is None:
                    continue
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " " + new_op + " " + source[rs:re_]
                out.append(_splice(source, test, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule 3: list mutation + append buried inside the search `if`, executed every
# time a new local extremum is found instead of once after the search loop.
# ---------------------------------------------------------------------------
def hoist_side_effects_after_for(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.If):
            continue
        if_node = node.body[0]
        test = if_node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Gt, ast.Lt))):
            continue
        body = if_node.body
        if len(body) < 2:
            continue
        first = body[0]
        if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if not (isinstance(first.value, ast.Name) and first.value.id == node.target.id):
            continue
        extra_stmts = body[1:]
        try:
            removal_start, _ = _span(source, extra_stmts[0])
            _, removal_end = _span(source, extra_stmts[-1])
            node_start, node_end = _span(source, node)
        except (IndexError, ValueError):
            continue
        if not (node_start <= removal_start and removal_end <= node_end):
            continue
        indent = " " * node.col_offset
        extra_lines = []
        for st in extra_stmts:
            s, e = _span(source, st)
            extra_lines.append(indent + source[s:e])
        inserted = "\n" + "\n".join(extra_lines)
        new_source = (source[:removal_start]
                      + source[removal_end:node_end]
                      + inserted
                      + source[node_end:])
        out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 4: recursive call's result is discarded (called as a bare statement)
# instead of being combined into the return value.
# ---------------------------------------------------------------------------
def merge_discarded_recursive_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        fname = func.name
        for node in ast.walk(func):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for i in range(len(body) - 1):
                s1, s2 = body[i], body[i + 1]
                if not (isinstance(s1, ast.Expr) and isinstance(s1.value, ast.Call)
                        and isinstance(s1.value.func, ast.Name)
                        and s1.value.func.id == fname):
                    continue
                if not (isinstance(s2, ast.Return) and s2.value is not None):
                    continue
                call_s, call_e = _span(source, s1.value)
                ret_s, ret_e = _span(source, s2.value)
                call_src = source[call_s:call_e]
                ret_src = source[ret_s:ret_e]
                new_stmt = "return " + ret_src + " + " + call_src
                s_start, _ = _span(source, s1)
                _, s_end = _span(source, s2)
                out.append(source[:s_start] + new_stmt + source[s_end:])
    return out


# ---------------------------------------------------------------------------
# Rule 5: base case `k == 1` returns the whole (remaining) list parameter
# instead of the single greatest element.
# ---------------------------------------------------------------------------
def fix_base_case_single_max(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.args.args:
            continue
        list_param = func.args.args[0].arg
        for node in ast.walk(func):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Eq)):
                continue
            vals = [test.left] + test.comparators
            if not any(isinstance(v, ast.Constant) and v.value == 1 for v in vals):
                continue
            if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
                continue
            ret = node.body[0]
            if not (isinstance(ret.value, ast.Name) and ret.value.id == list_param):
                continue
            new_text = "[max(" + list_param + ")]"
            out.append(_splice(source, ret.value, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 6: `return False` used in a function that otherwise returns lists.
# ---------------------------------------------------------------------------
def fix_return_false(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        has_list_return = any(
            isinstance(n, ast.Return) and isinstance(n.value, ast.List)
            for n in ast.walk(func)
        )
        if not has_list_return:
            continue
        for node in ast.walk(func):
            if (isinstance(node, ast.Return) and isinstance(node.value, ast.Constant)
                    and node.value.value is False):
                out.append(_splice(source, node.value, "[]"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_name_typo",
                apply=fix_name_typo,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="flip_min_to_max_selection",
                apply=flip_min_to_max_selection,
                symptoms=("wrong",),
            ),
            Rule(
                name="hoist_side_effects_after_for",
                apply=hoist_side_effects_after_for,
                symptoms=("wrong",),
            ),
            Rule(
                name="merge_discarded_recursive_call",
                apply=merge_discarded_recursive_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_base_case_single_max",
                apply=fix_base_case_single_max,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_return_false",
                apply=fix_return_false,
                symptoms=("wrong", "err:TypeError"),
            ),
        ]