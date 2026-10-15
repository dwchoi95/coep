"""
Repair module for the Top-K assignment.

Each rule inspects the AST of a submission, looks for a narrow, well
defined structural misconception, and if found returns one or more
*minimally* edited source strings (character-span splices on the
original text, never a full rewrite).
"""

import ast
import re
import builtins

from src.core.repair import Rule

BUILTIN_NAMES = set(dir(builtins)) | {"True", "False", "None", "self"}


# ----------------------------------------------------------------- helpers

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


def _get_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _indent_of(source, node):
    s, _ = _span(source, node)
    line_start = source.rfind("\n", 0, s) + 1
    return source[line_start:s]


def _build_parent_map(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _edit_distance(a, b):
    if a == b:
        return 0
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, cb in enumerate(b, 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
            prev = cur
    return dp[-1]


def _is_similar(a, b):
    if a == b:
        return False
    if _edit_distance(a, b) <= 2:
        return True
    if len(a) >= 2 and len(b) >= 2:
        if (a in b or b in a) and abs(len(a) - len(b)) <= 4:
            return True
    return False


def _collect_bound_names(func):
    names = {func.name}
    for n in ast.walk(func):
        if isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.add(n.id)
        elif isinstance(n, ast.FunctionDef):
            names.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            names.update(n.names)
    return names


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


# ----------------------------------------------------------------- rules

def fuzzy_typo_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    module_funcs = {n.name for n in _funcs(tree)}
    for func in _funcs(tree):
        bound = _collect_bound_names(func) | module_funcs | BUILTIN_NAMES
        undefined = {}
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in bound:
                    undefined.setdefault(n.id, []).append(n)
        for uid in undefined:
            candidates = {b for b in bound if _is_similar(uid, b)}
            if len(candidates) == 1:
                cand = next(iter(candidates))
                fs, fe = _span(source, func)
                func_src = source[fs:fe]
                new_func_src = re.sub(r"\b" + re.escape(uid) + r"\b", cand, func_src)
                if new_func_src != func_src:
                    out.append(source[:fs] + new_func_src + source[fe:])
    return out


def undefined_append_receiver(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    module_funcs = {n.name for n in _funcs(tree)}
    for func in _funcs(tree):
        bound = _collect_bound_names(func) | module_funcs | BUILTIN_NAMES
        accumulators = []
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.List) and not n.value.elts:
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        accumulators.append(t.id)
        accumulators = list(dict.fromkeys(accumulators))
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append":
                recv = n.func.value
                if isinstance(recv, ast.Name) and recv.id not in bound:
                    cands = [a for a in accumulators if a != recv.id]
                    if len(cands) == 1:
                        out.append(_splice(source, recv, cands[0]))
    return out


def shadow_function_rename(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    module_funcs = {n.name for n in _funcs(tree)}
    for func in _funcs(tree):
        for stmt in ast.walk(func):
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                name = stmt.targets[0].id
                if (name in module_funcs and name != func.name
                        and isinstance(stmt.value, ast.Call)
                        and isinstance(stmt.value.func, ast.Name)
                        and stmt.value.func.id == name):
                    new_name = name + "_result"
                    fs, fe = _span(source, func)
                    func_src = source[fs:fe]
                    new_func_src = re.sub(
                        r"\b" + re.escape(name) + r"\b(?!\s*\()", new_name, func_src)
                    if new_func_src != func_src:
                        out.append(source[:fs] + new_func_src + source[fe:])
    return out


def wrong_extremum_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and len(node.body) == 1:
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Gt):
                left, right = test.left, test.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                    stmt = node.body[0]
                    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                            and isinstance(stmt.targets[0], ast.Name)
                            and isinstance(stmt.value, ast.Name)):
                        if (stmt.value.id == left.id
                                and stmt.targets[0].id != right.id
                                and stmt.targets[0].id != left.id):
                            out.append(_splice(source, stmt.targets[0], right.id))
    return out


def stray_loop_var_after_search(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parents = _build_parent_map(tree)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                and len(node.body) == 1 and isinstance(node.body[0], ast.If)):
            target_id = node.target.id
            ifstmt = node.body[0]
            test = ifstmt.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Gt)):
                continue
            left, right = test.left, test.comparators[0]
            if not (isinstance(left, ast.Name) and left.id == target_id
                    and isinstance(right, ast.Name)):
                continue
            extremum_id = right.id
            if len(ifstmt.body) != 1 or not isinstance(ifstmt.body[0], ast.Assign):
                continue
            astmt = ifstmt.body[0]
            if not (len(astmt.targets) == 1 and isinstance(astmt.targets[0], ast.Name)
                    and astmt.targets[0].id == extremum_id
                    and isinstance(astmt.value, ast.Name) and astmt.value.id == target_id):
                continue
            parent = parents.get(node)
            if parent is None or not hasattr(parent, "body"):
                continue
            body = parent.body
            if node not in body:
                continue
            idx = body.index(node)
            for j in range(idx + 1, min(idx + 4, len(body))):
                nxt = body[j]
                for n in ast.walk(nxt):
                    if isinstance(n, ast.Name) and n.id == target_id and isinstance(n.ctx, ast.Load):
                        out.append(_splice(source, n, extremum_id))
    return out


def append_wraps_mutator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if (isinstance(call.func, ast.Attribute) and call.func.attr == "append"
                    and len(call.args) == 1):
                inner = call.args[0]
                if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
                        and inner.func.attr in ("remove", "pop") and len(inner.args) == 1):
                    value_src = _get_text(source, inner.args[0])
                    list_src = _get_text(source, inner.func.value)
                    recv_src = _get_text(source, call.func.value)
                    indent = _indent_of(source, node)
                    new_stmt = f"{recv_src}.append({value_src})\n{indent}{list_src}.remove({value_src})"
                    out.append(_splice(source, node, new_stmt))
    return out


def off_by_one_range_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "range" and len(node.args) == 1):
            arg = node.args[0]
            if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
                    and isinstance(arg.left, ast.Name) and arg.left.id == "k"
                    and isinstance(arg.right, ast.Constant) and arg.right.value == 1):
                out.append(_splice(source, arg, "k"))
    return out


def off_by_one_slice_bound(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            sl = node.slice
            if isinstance(sl, ast.Slice) and sl.lower is None and sl.step is None:
                upper = sl.upper
                if (isinstance(upper, ast.BinOp) and isinstance(upper.left, ast.Name)
                        and upper.left.id == "k" and isinstance(upper.op, (ast.Add, ast.Sub))
                        and isinstance(upper.right, ast.Constant) and upper.right.value == 1):
                    out.append(_splice(source, upper, "k"))
    return out


def loop_bound_lte_to_lt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.LtE):
                right = test.comparators[0]
                if isinstance(right, ast.Name) and right.id == "k":
                    left_s, left_e = _span(source, test.left)
                    right_s, right_e = _span(source, right)
                    between = source[left_e:right_s]
                    new_between = between.replace("<=", "<", 1)
                    if new_between != between:
                        out.append(source[:left_e] + new_between + source[right_s:])
    return out


def missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _funcs(tree):
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        accumulators = []
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.List) and not n.value.elts:
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        accumulators.append(t.id)
        if len(accumulators) != 1 or not func.body:
            continue
        var = accumulators[0]
        last_stmt = func.body[-1]
        _, le = _span(source, last_stmt)
        indent = _indent_of(source, last_stmt)
        insertion = f"\n{indent}return {var}"
        out.append(source[:le] + insertion + source[le:])
    return out


def hardcoded_literal_to_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _funcs(tree):
        params = [a.arg for a in func.args.args]
        if "k" not in params:
            continue
        for n in ast.walk(func):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Subscript):
                sl = n.value.slice
                if (isinstance(sl, ast.Slice) and sl.lower is None and sl.step is None
                        and isinstance(sl.upper, ast.Constant) and isinstance(sl.upper.value, int)
                        and not isinstance(sl.upper.value, bool)):
                    out.append(_splice(source, sl.upper, "k"))
    return out


def bracket_call_to_paren(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr in ("append", "remove", "pop", "extend")):
            arg_src = _get_text(source, node.slice)
            recv_src = _get_text(source, node.value)
            new_text = f"{recv_src}({arg_src})"
            out.append(_splice(source, node, new_text))
    return out


def min_should_be_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and len(node.body) == 1:
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Lt):
                left, right = test.left, test.comparators[0]
                stmt = node.body[0]
                if (isinstance(left, ast.Name) and isinstance(right, ast.Name)
                        and isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name) and isinstance(stmt.value, ast.Name)
                        and stmt.targets[0].id == right.id and stmt.value.id == left.id):
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    new_cmp = source[ls:le] + " > " + source[rs:re_]
                    out.append(_splice(source, test, new_cmp))
    return out


def unsafe_swap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            if (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)
                    and len(s1.targets) == 1 and len(s2.targets) == 1):
                t1_src = _get_text(source, s1.targets[0])
                v1_src = _get_text(source, s1.value)
                t2_src = _get_text(source, s2.targets[0])
                v2_src = _get_text(source, s2.value)
                if t1_src == v2_src and t2_src == v1_src and t1_src != t2_src:
                    s1s, _ = _span(source, s1)
                    _, s2e = _span(source, s2)
                    new_stmt = f"{t1_src}, {t2_src} = {v1_src}, {v2_src}"
                    out.append(source[:s1s] + new_stmt + source[s2e:])
    return out


def missing_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            test = node.test
            if (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], (ast.Lt, ast.LtE, ast.NotEq))
                    and isinstance(test.left, ast.Name)):
                var = test.left.id
                updated = False
                for n in ast.walk(node):
                    if n is node:
                        continue
                    if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == var:
                        updated = True
                    if isinstance(n, ast.Assign):
                        for t in n.targets:
                            if isinstance(t, ast.Name) and t.id == var:
                                updated = True
                if not updated and node.body:
                    last_stmt = node.body[-1]
                    _, le = _span(source, last_stmt)
                    indent = _indent_of(source, last_stmt)
                    insertion = f"\n{indent}{var} += 1"
                    out.append(source[:le] + insertion + source[le:])
    return out


def return_wrong_list_variable(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _funcs(tree):
        if not func.args.args:
            continue
        param0 = func.args.args[0].arg
        accumulators = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.List) and not n.value.elts:
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id != param0:
                        accumulators.add(t.id)
        appended = set()
        for n in ast.walk(func):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "append" and isinstance(n.func.value, ast.Name)):
                appended.add(n.func.value.id)
        candidates = accumulators & appended
        if len(candidates) != 1:
            continue
        acc = next(iter(candidates))
        for n in ast.walk(func):
            if isinstance(n, ast.Return):
                val = n.value
                target_node = None
                if isinstance(val, ast.Name) and val.id == param0:
                    target_node = val
                elif (isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name)
                        and val.value.id == param0):
                    target_node = val.value
                if target_node is not None:
                    out.append(_splice(source, target_node, acc))
    return out


def insert_missing_remove(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for loopnode in ast.walk(tree):
        if isinstance(loopnode, (ast.While, ast.For)):
            body = loopnode.body
            for stmt in body:
                list_name = None
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    if (isinstance(call.func, ast.Attribute) and call.func.attr == "append"
                            and len(call.args) == 1):
                        arg = call.args[0]
                        if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                                and arg.func.id == "max" and len(arg.args) == 1
                                and isinstance(arg.args[0], ast.Name)):
                            list_name = arg.args[0].id
                if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
                    val = stmt.value
                    if isinstance(val, ast.List) and len(val.elts) == 1:
                        el = val.elts[0]
                        if (isinstance(el, ast.Call) and isinstance(el.func, ast.Name)
                                and el.func.id == "max" and len(el.args) == 1
                                and isinstance(el.args[0], ast.Name)):
                            list_name = el.args[0].id
                if list_name:
                    body_src = "".join(_get_text(source, b) for b in body)
                    if f"{list_name}.remove(" in body_src or f"{list_name}.pop(" in body_src:
                        continue
                    s, e = _span(source, stmt)
                    indent = _indent_of(source, stmt)
                    insertion = f"\n{indent}{list_name}.remove(max({list_name}))"
                    out.append(source[:e] + insertion + source[e:])
    return out


# ----------------------------------------------------------------- Fixer

class Fixer:
    def rules(self):
        return [
            Rule(name="fuzzy_typo_fix", apply=fuzzy_typo_fix,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_append_receiver", apply=undefined_append_receiver,
                 symptoms=("err:NameError",)),
            Rule(name="shadow_function_rename", apply=shadow_function_rename,
                 symptoms=("err:UnboundLocalError",)),
            Rule(name="wrong_extremum_target", apply=wrong_extremum_target,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="stray_loop_var_after_search", apply=stray_loop_var_after_search,
                 symptoms=("wrong",)),
            Rule(name="append_wraps_mutator", apply=append_wraps_mutator,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="off_by_one_range_k", apply=off_by_one_range_k,
                 symptoms=("wrong",)),
            Rule(name="off_by_one_slice_bound", apply=off_by_one_slice_bound,
                 symptoms=("wrong",)),
            Rule(name="loop_bound_lte_to_lt", apply=loop_bound_lte_to_lt,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="missing_return", apply=missing_return,
                 symptoms=("wrong",)),
            Rule(name="hardcoded_literal_to_k", apply=hardcoded_literal_to_k,
                 symptoms=("wrong",)),
            Rule(name="bracket_call_to_paren", apply=bracket_call_to_paren,
                 symptoms=("err:TypeError",)),
            Rule(name="min_should_be_max", apply=min_should_be_max,
                 symptoms=("wrong",)),
            Rule(name="unsafe_swap", apply=unsafe_swap,
                 symptoms=("wrong",)),
            Rule(name="missing_increment", apply=missing_increment,
                 symptoms=("timeout", "wrong")),
            Rule(name="return_wrong_list_variable", apply=return_wrong_list_variable,
                 symptoms=("wrong",)),
            Rule(name="insert_missing_remove", apply=insert_missing_remove,
                 symptoms=("wrong", "timeout")),
        ]