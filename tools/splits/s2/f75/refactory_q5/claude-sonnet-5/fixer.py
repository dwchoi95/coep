"""
Repair module for the Top-K assignment.

Each rule performs a small, local, AST-located, text-spliced edit that
targets one recurring misconception observed in buggy submissions. Rules
are pure candidate generators: they never mutate behaviour by rewriting
whole functions, and they return [] when their pattern does not match.
"""

import ast
from src.core.repair import Rule


# ---------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------

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


def _slice_index(sl):
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapped


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


def _names_close(a, b):
    if a == b:
        return False
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= 3 and short in long_:
        return True
    if a + "s" == b or b + "s" == a:
        return True
    if a.rstrip("s") == b.rstrip("s") and a.rstrip("s") != "":
        return True
    return _edit_distance(a, b) <= 2


# ---------------------------------------------------------------------
# Rule 1: undefined / mistyped identifiers (NameError-prone)
# ---------------------------------------------------------------------

@_safe
def fix_undefined_name_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    import builtins
    builtin_names = set(dir(builtins))
    module_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    seen = set()
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = {a.arg for a in func.args.args}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                name = node.id
                if name in defined or name in builtin_names or name in module_funcs:
                    continue
                candidates = sorted(d for d in defined if _names_close(name, d))
                for cand in candidates[:1]:
                    key = (node.lineno, node.col_offset, cand)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(_splice(source, node, cand))
    return out


# ---------------------------------------------------------------------
# Rule 2: .remove(X) executed before .append(X) (removes the max before
# it is recorded)
# ---------------------------------------------------------------------

def _as_method_call(stmt):
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and len(call.args) == 1:
            return call.func.attr, call.args[0]
    return None


@_safe
def swap_remove_append_order(source):
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
            c1 = _as_method_call(s1)
            c2 = _as_method_call(s2)
            if not c1 or not c2:
                continue
            if c1[0] != "remove" or c2[0] != "append":
                continue
            if ast.dump(c1[1], annotate_fields=False) != ast.dump(c2[1], annotate_fields=False):
                continue
            s1s, s1e = _span(source, s1)
            s2s, s2e = _span(source, s2)
            between = source[s1e:s2s]
            text1 = source[s1s:s1e]
            text2 = source[s2s:s2e]
            out.append(source[:s1s] + text2 + between + text1 + source[s2e:])
    return out


# ---------------------------------------------------------------------
# Rule 3: final slice bound normalised to plain `k`
# ---------------------------------------------------------------------

@_safe
def fix_slice_bound_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if "k" not in {a.arg for a in func.args.args}:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
                upper = node.slice.upper
                if upper is None:
                    continue
                replace = False
                if isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                    replace = True
                elif isinstance(upper, ast.BinOp) and isinstance(upper.op, (ast.Add, ast.Sub)):
                    left, right = upper.left, upper.right
                    if isinstance(left, ast.Name) and left.id == "k" \
                       and isinstance(right, ast.Constant) and right.value == 1:
                        replace = True
                if replace:
                    out.append(_splice(source, upper, "k"))
    return out


# ---------------------------------------------------------------------
# Rule 4: range(k-1) / range(k+1) -> range(k)
# ---------------------------------------------------------------------

@_safe
def fix_range_k_offset(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Sub)):
                left, right = arg.left, arg.right
                if isinstance(left, ast.Name) and left.id == "k" \
                   and isinstance(right, ast.Constant) and right.value == 1:
                    out.append(_splice(source, arg, "k"))
    return out


# ---------------------------------------------------------------------
# Rule 5: off-by-one While loop comparator (<=/>= vs </>)
# ---------------------------------------------------------------------

@_safe
def flip_while_comparator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    pairs = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt}
    symbols = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1:
            op = node.test.ops[0]
            if type(op) in pairs:
                cmp = node.test
                left, right = cmp.left, cmp.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_sym = symbols[pairs[type(op)]]
                new_text = source[ls:le] + " " + new_sym + " " + source[rs:re_]
                out.append(_splice(source, cmp, new_text))
    return out


# ---------------------------------------------------------------------
# Rule 6: counter initialised to 0 but loop uses <= (off-by-one start)
# ---------------------------------------------------------------------

@_safe
def counter_init_zero_to_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        body = func.body
        for i, stmt in enumerate(body):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
               and isinstance(stmt.targets[0], ast.Name) \
               and isinstance(stmt.value, ast.Constant) and stmt.value.value == 0:
                name = stmt.targets[0].id
                for later in body[i + 1:]:
                    if isinstance(later, ast.While) and isinstance(later.test, ast.Compare) \
                       and len(later.test.ops) == 1 and isinstance(later.test.ops[0], ast.LtE):
                        names_in_test = [n.id for n in ast.walk(later.test) if isinstance(n, ast.Name)]
                        if name in names_in_test:
                            out.append(_splice(source, stmt.value, "1"))
    return out


# ---------------------------------------------------------------------
# Rule 7: append/remove using the wrong variable instead of the max tracker
# ---------------------------------------------------------------------

@_safe
def fix_tracker_misuse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        tracker = None
        for stmt in body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
               and isinstance(stmt.targets[0], ast.Name):
                val = stmt.value
                is_init = False
                if isinstance(val, ast.Subscript):
                    idx = _slice_index(val.slice)
                    if isinstance(idx, ast.Constant) and idx.value == 0:
                        is_init = True
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "max":
                    is_init = True
                if is_init:
                    tracker = stmt.targets[0].id
                    continue
            if tracker is None:
                continue
            for call_node in ast.walk(stmt):
                if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Attribute) \
                   and call_node.func.attr in ("append", "remove") and len(call_node.args) == 1:
                    arg = call_node.args[0]
                    if isinstance(arg, ast.Name) and arg.id != tracker:
                        out.append(_splice(source, arg, tracker))
    return out


# ---------------------------------------------------------------------
# Rule 8: inside the comparison-update `if`, the wrong variable gets updated
# ---------------------------------------------------------------------

@_safe
def fix_if_update_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        loopvar = node.target.id
        for sub in ast.walk(node):
            if isinstance(sub, ast.If) and isinstance(sub.test, ast.Compare) and len(sub.test.ops) == 1:
                left, right = sub.test.left, sub.test.comparators[0]
                names = []
                if isinstance(left, ast.Name):
                    names.append(left.id)
                if isinstance(right, ast.Name):
                    names.append(right.id)
                others = [n for n in names if n != loopvar]
                if len(others) != 1:
                    continue
                tracker = others[0]
                if len(sub.body) == 1 and isinstance(sub.body[0], ast.Assign) \
                   and len(sub.body[0].targets) == 1 and isinstance(sub.body[0].targets[0], ast.Name):
                    assign = sub.body[0]
                    val = assign.value
                    target_name = assign.targets[0].id
                    if isinstance(val, ast.Name) and val.id == loopvar and target_name != tracker:
                        out.append(_splice(source, assign.targets[0], tracker))
    return out


# ---------------------------------------------------------------------
# Rule 9: `.append[x]` / `.remove[x]` (subscript used instead of call)
# ---------------------------------------------------------------------

@_safe
def fix_subscript_call_syntax(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
           and node.value.attr in ("append", "remove", "pop", "insert"):
            idx = _slice_index(node.slice)
            vs, ve = _span(source, node.value)
            idxs, idxe = _span(source, idx)
            new_text = source[vs:ve] + "(" + source[idxs:idxe] + ")"
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------
# Rule 10: While loop bounded by a counter that is never incremented
# ---------------------------------------------------------------------

@_safe
def insert_missing_counter_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        counter_name = None
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.left, ast.Name) \
           and isinstance(test.ops[0], (ast.Lt, ast.LtE)):
            counter_name = test.left.id
        if counter_name is None or not node.body:
            continue
        incremented = False
        for stmt in node.body:
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) \
               and stmt.target.id == counter_name:
                incremented = True
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
               and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == counter_name:
                incremented = True
        if incremented:
            continue
        last_stmt = node.body[-1]
        _, le = _span(source, last_stmt)
        indent = " " * last_stmt.col_offset
        insertion = "\n" + indent + f"{counter_name} += 1"
        out.append(source[:le] + insertion + source[le:])
    return out


# ---------------------------------------------------------------------
# Rule 11: accumulator list built but function never returns it
# ---------------------------------------------------------------------

@_safe
def insert_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if any(isinstance(s, ast.Return) for s in func.body):
            continue
        if not func.body:
            continue
        accumulator = None
        for stmt in func.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
               and isinstance(stmt.targets[0], ast.Name) \
               and isinstance(stmt.value, ast.List) and not stmt.value.elts:
                accumulator = stmt.targets[0].id
        if accumulator is None:
            continue
        appended = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "append" and isinstance(n.func.value, ast.Name)
            and n.func.value.id == accumulator
            for n in ast.walk(func)
        )
        if not appended:
            continue
        _, end_offset = _span(source, func)
        indent = " " * func.body[0].col_offset
        insertion = "\n" + indent + f"return {accumulator}"
        out.append(source[:end_offset] + insertion + source[end_offset:])
    return out


# ---------------------------------------------------------------------
# Rule 12: failed in-place swap `a = b; b = a` -> tuple swap
# ---------------------------------------------------------------------

@_safe
def fix_sequential_swap(source):
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
            if not (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)):
                continue
            if len(s1.targets) != 1 or len(s2.targets) != 1:
                continue
            t1, t2 = s1.targets[0], s2.targets[0]
            v1, v2 = s1.value, s2.value
            if ast.dump(t1, annotate_fields=False) == ast.dump(v2, annotate_fields=False) \
               and ast.dump(v1, annotate_fields=False) == ast.dump(t2, annotate_fields=False) \
               and ast.dump(t1, annotate_fields=False) != ast.dump(t2, annotate_fields=False):
                t1s, t1e = _span(source, t1)
                v1s, v1e = _span(source, v1)
                a_text = source[t1s:t1e]
                b_text = source[v1s:v1e]
                new_text = f"{a_text}, {b_text} = {b_text}, {a_text}"
                full_s, _ = _span(source, s1)
                _, s2e = _span(source, s2)
                out.append(source[:full_s] + new_text + source[s2e:])
    return out


# ---------------------------------------------------------------------
# Rule 13: single-pass bubble sort never repeated -> wrap in outer loop
# ---------------------------------------------------------------------

@_safe
def wrap_single_pass_bubble_sort(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for stmt in func.body:
            if not isinstance(stmt, ast.For):
                continue
            has_tuple_swap = False
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Assign) and len(sub.targets) == 1 \
                   and isinstance(sub.targets[0], ast.Tuple):
                    has_tuple_swap = True
            if not has_tuple_swap:
                continue
            seq_name = None
            if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name) \
               and stmt.iter.func.id == "range" and stmt.iter.args:
                arg0 = stmt.iter.args[0]
                if isinstance(arg0, ast.BinOp) and isinstance(arg0.left, ast.Call) \
                   and isinstance(arg0.left.func, ast.Name) and arg0.left.func.id == "len" \
                   and arg0.left.args and isinstance(arg0.left.args[0], ast.Name):
                    seq_name = arg0.left.args[0].id
            if seq_name is None:
                if func.args.args:
                    seq_name = func.args.args[0].arg
                else:
                    continue
            s, e = _span(source, stmt)
            indent = " " * stmt.col_offset
            original = source[s:e]
            lines = original.split("\n")
            new_lines = [indent + "    " + lines[0]]
            for l in lines[1:]:
                new_lines.append(l if l.strip() == "" else "    " + l)
            wrapped = indent + f"for _pass_ in range(len({seq_name})):\n" + "\n".join(new_lines)
            out.append(source[:s] + wrapped + source[e:])
    return out


# ---------------------------------------------------------------------
# Rule 14: k == 0 edge case never guarded
# ---------------------------------------------------------------------

def _has_k_zero_compare(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], ast.Eq):
            names = []
            vals = []
            for side in [sub.left] + sub.comparators:
                if isinstance(side, ast.Name):
                    names.append(side.id)
                if isinstance(side, ast.Constant):
                    vals.append(side.value)
            if "k" in names and 0 in vals:
                return True
    return False


@_safe
def insert_k_zero_guard(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if "k" not in {a.arg for a in func.args.args}:
            continue
        if not func.body or _has_k_zero_compare(func):
            continue
        first_stmt = func.body[0]
        s, _ = _span(source, first_stmt)
        indent = " " * first_stmt.col_offset
        insertion = f"if k == 0:\n{indent}    return []\n{indent}"
        out.append(source[:s] + insertion + source[s:])
    return out


# ---------------------------------------------------------------------
# Rule 15: k == 0 branch exists but returns the wrong thing
# ---------------------------------------------------------------------

@_safe
def fix_k_zero_return_value(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq):
            names = []
            vals = []
            for side in [node.test.left] + node.test.comparators:
                if isinstance(side, ast.Name):
                    names.append(side.id)
                if isinstance(side, ast.Constant):
                    vals.append(side.value)
            if "k" in names and 0 in vals:
                for stmt in node.body:
                    if isinstance(stmt, ast.Return) and stmt.value is not None:
                        is_empty = isinstance(stmt.value, ast.List) and not stmt.value.elts
                        if not is_empty:
                            out.append(_splice(source, stmt.value, "[]"))
    return out


# ---------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="fix_undefined_name_typo",
                 apply=fix_undefined_name_typo,
                 symptoms=("err:NameError",)),
            Rule(name="swap_remove_append_order",
                 apply=swap_remove_append_order,
                 symptoms=("wrong",)),
            Rule(name="fix_slice_bound_k",
                 apply=fix_slice_bound_k,
                 symptoms=("wrong",)),
            Rule(name="fix_range_k_offset",
                 apply=fix_range_k_offset,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="flip_while_comparator",
                 apply=flip_while_comparator,
                 symptoms=("wrong", "timeout", "err:IndexError", "err:ValueError")),
            Rule(name="counter_init_zero_to_one",
                 apply=counter_init_zero_to_one,
                 symptoms=("wrong",)),
            Rule(name="fix_tracker_misuse",
                 apply=fix_tracker_misuse,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_if_update_target",
                 apply=fix_if_update_target,
                 symptoms=("wrong", "timeout")),
            Rule(name="fix_subscript_call_syntax",
                 apply=fix_subscript_call_syntax,
                 symptoms=("err:TypeError",)),
            Rule(name="insert_missing_counter_increment",
                 apply=insert_missing_counter_increment,
                 symptoms=("timeout", "wrong")),
            Rule(name="insert_missing_return",
                 apply=insert_missing_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_sequential_swap",
                 apply=fix_sequential_swap,
                 symptoms=("wrong",)),
            Rule(name="wrap_single_pass_bubble_sort",
                 apply=wrap_single_pass_bubble_sort,
                 symptoms=("wrong",)),
            Rule(name="insert_k_zero_guard",
                 apply=insert_k_zero_guard,
                 symptoms=("wrong", "err:IndexError", "err:ValueError")),
            Rule(name="fix_k_zero_return_value",
                 apply=fix_k_zero_return_value,
                 symptoms=("wrong",)),
        ]