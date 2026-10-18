import ast
import difflib
import builtins

from src.core.repair import Rule

BUILTIN_NAMES = set(dir(builtins))


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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _func_defs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _defined_names(func):
    names = set(a.arg for a in func.args.args)
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for e in t.elts:
                        if isinstance(e, ast.Name):
                            names.add(e.id)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            names.add(n.target.id)
        elif isinstance(n, ast.For):
            if isinstance(n.target, ast.Name):
                names.add(n.target.id)
            elif isinstance(n.target, (ast.Tuple, ast.List)):
                for e in n.target.elts:
                    if isinstance(e, ast.Name):
                        names.add(e.id)
    return names


def _real_slice(slice_node):
    if isinstance(slice_node, ast.Index):
        return slice_node.value
    return slice_node


def _empty_list_vars(func):
    out = set()
    for n in ast.walk(func):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
           and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.List) \
           and not n.value.elts:
            out.add(n.targets[0].id)
    return out


# ---------------------------------------------------------------------------
# Rule 1: `.append[x]` / `.remove[x]` typo'd as subscript instead of call.
# ---------------------------------------------------------------------------
def fix_bracket_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
           and node.value.attr in ("append", "remove", "pop", "extend", "add"):
            idx = _real_slice(node.slice)
            new_text = _text(source, node.value) + "(" + _text(source, idx) + ")"
            cand = _splice(source, node, new_text)
            if cand != source:
                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 2: generic undefined-name fuzzy rename (typo'd variable names).
# ---------------------------------------------------------------------------
def fix_undefined_name_fuzzy(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    module_funcs = {n.name for n in _func_defs(tree)}
    out = []
    for func in _func_defs(tree):
        defined = _defined_names(func) | module_funcs
        undefined_nodes = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in defined and n.id not in BUILTIN_NAMES:
                    undefined_nodes.append(n)
        if not undefined_nodes:
            continue
        reps = {}
        for n in undefined_nodes:
            matches = difflib.get_close_matches(n.id, list(defined), n=1, cutoff=0.6)
            if matches and matches[0] != n.id:
                reps[id(n)] = matches[0]
        edits = [(n, reps[id(n)]) for n in undefined_nodes if id(n) in reps]
        if not edits:
            continue
        edits.sort(key=lambda x: _span(source, x[0])[0], reverse=True)
        new_source = source
        for n, rep in edits:
            s, e = _span(source, n)
            new_source = new_source[:s] + rep + new_source[e:]
        if new_source != source:
            out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 3: `for x in UNDEFINED:` / `while UNDEFINED:` should iterate the list param.
# ---------------------------------------------------------------------------
def fix_undefined_iterable_to_param(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _func_defs(tree):
        params = [a.arg for a in func.args.args]
        list_params = [p for p in params if p != "k"]
        if len(list_params) != 1:
            continue
        candidate = list_params[0]
        defined = _defined_names(func)
        for node in ast.walk(func):
            target = None
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                target = node.iter
            elif isinstance(node, ast.While) and isinstance(node.test, ast.Name):
                target = node.test
            if target is not None and target.id not in defined \
               and target.id not in BUILTIN_NAMES and target.id != candidate:
                cand = _splice(source, target, candidate)
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 4: `undefined_name.append(...)` where accumulator is a sole `X = []` var.
# ---------------------------------------------------------------------------
def fix_undefined_accumulator_object(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _func_defs(tree):
        defined = _defined_names(func)
        acc_vars = _empty_list_vars(func)
        if len(acc_vars) != 1:
            continue
        acc = next(iter(acc_vars))
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
               and node.func.attr in ("append", "remove", "pop", "extend") \
               and isinstance(node.func.value, ast.Name):
                name_node = node.func.value
                if name_node.id not in defined and name_node.id not in BUILTIN_NAMES \
                   and name_node.id != acc:
                    cand = _splice(source, name_node, acc)
                    if cand != source:
                        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 5: append/remove argument should match the just-computed max var.
# ---------------------------------------------------------------------------
def fix_append_remove_arg_mismatch(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i, stmt in enumerate(body):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
               and isinstance(stmt.targets[0], ast.Name) \
               and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) \
               and stmt.value.func.id == "max":
                v = stmt.targets[0].id
                for later in body[i + 1:]:
                    for n2 in ast.walk(later):
                        if isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute) \
                           and n2.func.attr in ("append", "remove") \
                           and len(n2.args) == 1 and isinstance(n2.args[0], ast.Name) \
                           and n2.args[0].id != v:
                            cand = _splice(source, n2.args[0], v)
                            if cand != source:
                                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 6: `lst.remove(max(lst)); acc.append(max(lst))` executes in wrong order.
# ---------------------------------------------------------------------------
def fix_swap_remove_before_append(source):
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
            if not (isinstance(s1, ast.Expr) and isinstance(s1.value, ast.Call)
                    and isinstance(s1.value.func, ast.Attribute) and s1.value.func.attr == "remove"
                    and isinstance(s1.value.func.value, ast.Name)):
                continue
            if len(s1.value.args) != 1 or not isinstance(s1.value.args[0], ast.Call):
                continue
            inner1 = s1.value.args[0]
            if not (isinstance(inner1.func, ast.Name) and inner1.func.id == "max"
                    and len(inner1.args) == 1 and isinstance(inner1.args[0], ast.Name)):
                continue
            l1 = s1.value.func.value.id
            if inner1.args[0].id != l1:
                continue
            if not (isinstance(s2, ast.Expr) and isinstance(s2.value, ast.Call)
                    and isinstance(s2.value.func, ast.Attribute) and s2.value.func.attr == "append"):
                continue
            if len(s2.value.args) != 1 or not isinstance(s2.value.args[0], ast.Call):
                continue
            inner2 = s2.value.args[0]
            if not (isinstance(inner2.func, ast.Name) and inner2.func.id == "max"
                    and len(inner2.args) == 1 and isinstance(inner2.args[0], ast.Name)):
                continue
            if inner2.args[0].id != l1:
                continue
            s1s, s1e = _span(source, s1)
            s2s, s2e = _span(source, s2)
            seg1 = source[s1s:s1e]
            seg2 = source[s2s:s2e]
            new_source = source[:s1s] + seg2 + source[s1e:s2s] + seg1 + source[s2e:]
            if new_source != source:
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 7: `while ... <= k` off-by-one -> `< k`.
# ---------------------------------------------------------------------------
def fix_le_k_to_lt(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.LtE) \
           and isinstance(node.test.comparators[0], ast.Name) and node.test.comparators[0].id == "k":
            left = node.test.left
            right = node.test.comparators[0]
            new_cmp = _text(source, left) + " < " + _text(source, right)
            cand = _splice(source, node.test, new_cmp)
            if cand != source:
                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 8: `while k >= 0` off-by-one -> `while k > 0`.
# ---------------------------------------------------------------------------
def fix_gte_zero_to_gt(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.GtE) \
           and isinstance(node.test.comparators[0], ast.Constant) \
           and node.test.comparators[0].value == 0:
            left = node.test.left
            new_cmp = _text(source, left) + " > 0"
            cand = _splice(source, node.test, new_cmp)
            if cand != source:
                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 9: slice/range bound is `k+1`/`k-1`/literal instead of plain `k`.
# ---------------------------------------------------------------------------
def fix_slice_range_bound(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _func_defs(tree):
        params = [a.arg for a in func.args.args]
        if "k" not in params:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Slice) and node.upper is not None:
                upper = node.upper
                if isinstance(upper, ast.BinOp) and isinstance(upper.left, ast.Name) \
                   and upper.left.id == "k" and isinstance(upper.op, (ast.Add, ast.Sub)) \
                   and isinstance(upper.right, ast.Constant):
                    cand = _splice(source, upper, "k")
                    if cand != source:
                        out.append(cand)
                elif isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                    cand = _splice(source, upper, "k")
                    if cand != source:
                        out.append(cand)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "range" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.left, ast.Name) \
                   and arg.left.id == "k" and isinstance(arg.op, (ast.Add, ast.Sub)) \
                   and isinstance(arg.right, ast.Constant):
                    cand = _splice(source, arg, "k")
                    if cand != source:
                        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 10: function body never returns -> add `return <accumulator>` at the end.
# ---------------------------------------------------------------------------
def fix_missing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _func_defs(tree):
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        acc_vars = _empty_list_vars(func)
        if len(acc_vars) != 1:
            continue
        acc = next(iter(acc_vars))
        if not func.body:
            continue
        last = func.body[-1]
        indent = " " * func.body[0].col_offset
        _, e = _span(source, last)
        insertion = "\n" + indent + "return " + acc
        cand = source[:e] + insertion + source[e:]
        if cand != source:
            out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 11: manual swap without temp overwrites itself -> tuple swap.
# ---------------------------------------------------------------------------
def fix_bubble_swap(source):
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
            if not (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)):
                continue
            if len(s1.targets) != 1 or len(s2.targets) != 1:
                continue
            t1, t2 = s1.targets[0], s2.targets[0]
            v1, v2 = s1.value, s2.value
            if not all(isinstance(x, ast.Subscript) for x in (t1, t2, v1, v2)):
                continue
            if not (isinstance(t1.value, ast.Name) and isinstance(t2.value, ast.Name)
                    and isinstance(v1.value, ast.Name) and isinstance(v2.value, ast.Name)):
                continue
            names = {t1.value.id, t2.value.id, v1.value.id, v2.value.id}
            if len(names) != 1:
                continue
            L = next(iter(names))
            idx_t1 = _text(source, _real_slice(t1.slice))
            idx_v1 = _text(source, _real_slice(v1.slice))
            idx_t2 = _text(source, _real_slice(t2.slice))
            idx_v2 = _text(source, _real_slice(v2.slice))
            if idx_t1 == idx_v2 and idx_v1 == idx_t2 and idx_t1 != idx_v1:
                s1s, _ = _span(source, s1)
                _, s2e = _span(source, s2)
                new_text = "%s[%s], %s[%s] = %s[%s], %s[%s]" % (
                    L, idx_t1, L, idx_v1, L, idx_v1, L, idx_t1
                )
                cand = source[:s1s] + new_text + source[s2e:]
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 12: `return lst[:k]` / `return lst` instead of the actual accumulator.
# ---------------------------------------------------------------------------
def fix_return_wrong_accumulator(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _func_defs(tree):
        params = {a.arg for a in func.args.args}
        acc_vars = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
               and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.List) \
               and not n.value.elts:
                name = n.targets[0].id
                for n2 in ast.walk(func):
                    if isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute) \
                       and n2.func.attr == "append" and isinstance(n2.func.value, ast.Name) \
                       and n2.func.value.id == name:
                        acc_vars.add(name)
        if len(acc_vars) != 1:
            continue
        acc = next(iter(acc_vars))
        for node in ast.walk(func):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            target_name_node = None
            if isinstance(node.value, ast.Name):
                target_name_node = node.value
            elif isinstance(node.value, ast.Subscript) and isinstance(node.value.value, ast.Name):
                target_name_node = node.value.value
            if target_name_node is None:
                continue
            r = target_name_node.id
            if r != acc and r in params:
                cand = _splice(source, target_name_node, acc)
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 13: `lst.pop(max(lst))` should pop by index, not by value.
# ---------------------------------------------------------------------------
def fix_pop_value_to_index(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "pop" and isinstance(node.func.value, ast.Name):
            L = node.func.value.id
            if len(node.args) == 1 and isinstance(node.args[0], ast.Call) \
               and isinstance(node.args[0].func, ast.Name) and node.args[0].func.id == "max" \
               and len(node.args[0].args) == 1 and isinstance(node.args[0].args[0], ast.Name) \
               and node.args[0].args[0].id == L:
                new_text = "%s.index(max(%s))" % (L, L)
                cand = _splice(source, node.args[0], new_text)
                if cand != source:
                    out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 14: inside the max-finding `if`, the update assigns to the wrong name.
# ---------------------------------------------------------------------------
def fix_wrong_if_assign_target(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        op = test.ops[0]
        if isinstance(op, ast.Gt):
            a_node, b_node = test.left, test.comparators[0]
        elif isinstance(op, ast.Lt):
            a_node, b_node = test.comparators[0], test.left
        else:
            continue
        if not (isinstance(a_node, ast.Name) and isinstance(b_node, ast.Name)):
            continue
        a_id, b_id = a_node.id, b_node.id
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Assign):
            continue
        assign = node.body[0]
        if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
            continue
        if not isinstance(assign.value, ast.Name) or assign.value.id != a_id:
            continue
        c_id = assign.targets[0].id
        if c_id != b_id:
            cand = _splice(source, assign.targets[0], b_id)
            if cand != source:
                out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Rule 15: nested `for k in ...` shadows the outer `k` parameter.
# ---------------------------------------------------------------------------
def fix_k_shadow_rename(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _func_defs(tree):
        params = [a.arg for a in func.args.args]
        if "k" not in params:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == "k":
                names = [n for n in ast.walk(node) if isinstance(n, ast.Name) and n.id == "k"]
                if not names:
                    continue
                new_name = "k_item"
                names_sorted = sorted(names, key=lambda n: _span(source, n)[0], reverse=True)
                new_source = source
                for n in names_sorted:
                    s, e = _span(source, n)
                    new_source = new_source[:s] + new_name + new_source[e:]
                if new_source != source:
                    out.append(new_source)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="bracket_call_to_parens",
                apply=fix_bracket_call,
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="undefined_name_fuzzy_rename",
                apply=fix_undefined_name_fuzzy,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="undefined_iterable_to_param",
                apply=fix_undefined_iterable_to_param,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="undefined_accumulator_object_rename",
                apply=fix_undefined_accumulator_object,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="append_remove_arg_should_match_max",
                apply=fix_append_remove_arg_mismatch,
                symptoms=("wrong",),
            ),
            Rule(
                name="swap_remove_before_append",
                apply=fix_swap_remove_before_append,
                symptoms=("wrong",),
            ),
            Rule(
                name="le_k_offbyone_to_lt",
                apply=fix_le_k_to_lt,
                symptoms=("wrong",),
            ),
            Rule(
                name="gte_zero_offbyone_to_gt",
                apply=fix_gte_zero_to_gt,
                symptoms=("wrong",),
            ),
            Rule(
                name="slice_range_bound_offset_fix",
                apply=fix_slice_range_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_return_accumulator",
                apply=fix_missing_return,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="bubble_swap_needs_tuple",
                apply=fix_bubble_swap,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_wrong_accumulator",
                apply=fix_return_wrong_accumulator,
                symptoms=("wrong",),
            ),
            Rule(
                name="pop_value_should_be_index",
                apply=fix_pop_value_to_index,
                symptoms=("err:ValueError", "wrong"),
            ),
            Rule(
                name="wrong_if_assign_target",
                apply=fix_wrong_if_assign_target,
                symptoms=("wrong", "err:NameError", "timeout"),
            ),
            Rule(
                name="k_param_shadowed_by_loop_var",
                apply=fix_k_shadow_rename,
                symptoms=("wrong", "timeout"),
            ),
        ]