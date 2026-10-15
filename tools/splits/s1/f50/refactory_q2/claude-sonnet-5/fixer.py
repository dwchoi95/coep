import ast
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


def _collect_bound(func):
    bound = set(a.arg for a in func.args.args)
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        if isinstance(node, ast.FunctionDef) and node is not func:
            bound.add(node.name)
        if isinstance(node, ast.Lambda):
            bound.update(a.arg for a in node.args.args)
    return bound


def rename_undefined_name(source):
    """A stray identifier (e.g. 'day'/'date' mismatch, or a pluralization
    typo like possible_birthday/possible_birthdays) is renamed to the
    binding that actually exists in scope."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    defined_funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if func.name not in ("unique_day", "unique_month", "contains_unique_day"):
            continue
        if any(isinstance(n, ast.FunctionDef) and n is not func for n in ast.walk(func)):
            continue
        bound = _collect_bound(func)
        undefined = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in bound or node.id in defined_funcs or node.id in BUILTIN_NAMES:
                    continue
                undefined.setdefault(node.id, []).append(node)
        if len(undefined) != 1:
            continue
        bad_name, nodes = next(iter(undefined.items()))
        candidate = None
        for b in bound:
            if b != bad_name and b.rstrip("s") == bad_name.rstrip("s"):
                candidate = b
                break
        if candidate is None:
            params = [a.arg for a in func.args.args if a.arg != "possible_birthdays"]
            if len(params) == 1:
                candidate = params[0]
        if candidate is None or candidate == bad_name:
            continue
        positions = sorted((_span(source, n) for n in nodes), key=lambda p: -p[0])
        new_source = source
        for s, e in positions:
            new_source = new_source[:s] + candidate + new_source[e:]
        out.append(new_source)
    return out


def _const_int(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool)


def _find_parent_body(tree, target):
    for n in ast.walk(tree):
        body = getattr(n, "body", None)
        if isinstance(body, list) and target in body:
            return body
    return None


def threshold_to_equality(source):
    """count > 1 (or >= 2) -> False / else True, and count <= 1 -> True /
    else False both miscount the zero case; relax the comparison to
    an equality check against the single-match threshold."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        op = test.ops[0]
        right = test.comparators[0]
        if not _const_int(right):
            continue
        if not (len(node.body) == 1 and isinstance(node.body[0], ast.Return)):
            continue
        then_ret = node.body[0].value
        if not (isinstance(then_ret, ast.Constant) and isinstance(then_ret.value, bool)):
            continue
        else_val = None
        if node.orelse and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return):
            v = node.orelse[0].value
            if isinstance(v, ast.Constant) and isinstance(v.value, bool):
                else_val = v.value
        else:
            parent_body = _find_parent_body(tree, node)
            if parent_body is not None:
                idx = parent_body.index(node)
                if idx + 1 < len(parent_body) and isinstance(parent_body[idx + 1], ast.Return):
                    v = parent_body[idx + 1].value
                    if isinstance(v, ast.Constant) and isinstance(v.value, bool):
                        else_val = v.value
        if else_val is None:
            continue
        then_val = then_ret.value
        ls, le = _span(source, test.left)
        left_src = source[ls:le]
        if isinstance(op, (ast.Gt, ast.GtE)) and then_val is False and else_val is True:
            n = right.value if isinstance(op, ast.Gt) else right.value - 1
            out.append(_splice(source, test, f"{left_src} != {n}"))
        elif isinstance(op, ast.LtE) and then_val is True and else_val is False:
            out.append(_splice(source, test, f"{left_src} == {right.value}"))
    return out


def dead_code_early_return(source):
    """A bare `return count` placed before the real if/else check makes
    the real logic unreachable; drop the premature return."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        body = func.body
        for i, stmt in enumerate(body[:-1]):
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
                nxt = body[i + 1]
                if isinstance(nxt, ast.If) and isinstance(nxt.test, ast.Compare):
                    left = nxt.test.left
                    if isinstance(left, ast.Name) and left.id == stmt.value.id:
                        s, e = _span(source, stmt)
                        out.append(source[:s] + source[e:])
    return out


def _editdist(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev = cur
    return dp[lb]


def fix_typo_call(source):
    """A call to a never-defined, near-miss name (e.g. unique_date) is
    redirected to the closest actually-defined helper."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name in defined:
                continue
            best = None
            for cand in defined:
                if cand.startswith("unique_") or cand.startswith("contains_"):
                    if _editdist(name, cand) <= 2 and abs(len(name) - len(cand)) <= 3:
                        best = cand
                        break
            if best:
                out.append(_splice(source, node.func, best))
    return out


def fix_lowercase_bool(source):
    """A stray lowercase true/false (not bound to anything) should be the
    actual Python keyword."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in ("true", "false"):
            if node.id in bound:
                continue
            repl = "True" if node.id == "true" else "False"
            out.append(_splice(source, node, repl))
    return out


def _contains_name_load(node, name):
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load):
            return True
    return False


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def insert_missing_accumulator_init(source):
    """A counter/flag is accumulated (x += 1, x = x or ...) without ever
    being initialized first; insert the missing init before the loop."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        prior_assigned = set(a.arg for a in func.args.args)
        for stmt in func.body:
            if isinstance(stmt, ast.For):
                for sub in ast.walk(stmt):
                    target_name = None
                    init_val = None
                    if isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name):
                        if isinstance(sub.op, ast.Add):
                            target_name = sub.target.id
                            init_val = "0"
                    elif isinstance(sub, ast.Assign) and len(sub.targets) == 1 and isinstance(sub.targets[0], ast.Name):
                        tname = sub.targets[0].id
                        if _contains_name_load(sub.value, tname):
                            if isinstance(sub.value, ast.BoolOp) and isinstance(sub.value.op, ast.Or):
                                target_name, init_val = tname, "False"
                            elif isinstance(sub.value, ast.BinOp) and isinstance(sub.value.op, ast.Add):
                                other = sub.value.right if _is_name(sub.value.left, tname) else sub.value.left
                                target_name = tname
                                init_val = "()" if isinstance(other, ast.Tuple) else "0"
                    if target_name and init_val is not None and target_name not in prior_assigned:
                        indent = " " * stmt.col_offset
                        s, _ = _span(source, stmt)
                        new_stmt = f"{target_name} = {init_val}\n{indent}"
                        out.append(source[:s] + new_stmt + source[s:])
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    prior_assigned.add(sub.id)
    return out


def fix_premature_false_in_loop(source):
    """for x in items: if cond: return True else: return False stops after
    the first non-matching element; make the else just continue and
    ensure the loop falls through to a trailing return False."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        body = func.body
        for i, stmt in enumerate(body):
            if not isinstance(stmt, ast.For):
                continue
            forbody = stmt.body
            if len(forbody) != 1 or not isinstance(forbody[0], ast.If):
                continue
            ifnode = forbody[0]
            if not (len(ifnode.body) == 1 and isinstance(ifnode.body[0], ast.Return)
                    and ifnode.orelse and len(ifnode.orelse) == 1
                    and isinstance(ifnode.orelse[0], ast.Return)):
                continue
            bodyval = ifnode.body[0].value
            elseval = ifnode.orelse[0].value
            if not (isinstance(bodyval, ast.Constant) and bodyval.value is True
                    and isinstance(elseval, ast.Constant) and elseval.value is False):
                continue
            os_, oe = _span(source, ifnode.orelse[0])
            has_trailing_return = any(isinstance(s, ast.Return) for s in body[i + 1:])
            new_source = source
            if not has_trailing_return:
                _, e_for = _span(source, stmt)
                indent = " " * stmt.col_offset
                new_source = new_source[:e_for] + "\n" + indent + "return False" + new_source[e_for:]
            new_source = new_source[:os_] + "continue" + new_source[oe:]
            out.append(new_source)
    return out


def insert_missing_filter_helper(source):
    """contains_unique_day calls an undefined helper (e.g. keep_month) that
    is supposed to filter possible_birthdays by month; define it."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
                if name not in defined and len(node.args) == 2:
                    s, _ = _span(source, func)
                    indent = " " * func.col_offset
                    helper = (
                        f"def {name}(a, b):\n"
                        f"{indent}    result = ()\n"
                        f"{indent}    for item in b:\n"
                        f"{indent}        if a == item[0]:\n"
                        f"{indent}            result = result + (item,)\n"
                        f"{indent}    return result\n\n"
                    )
                    out.append(source[:s] + helper + source[s:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="rename_undefined_name",
                apply=rename_undefined_name,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="threshold_to_equality",
                apply=threshold_to_equality,
                symptoms=("wrong",),
            ),
            Rule(
                name="dead_code_early_return",
                apply=dead_code_early_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_typo_call",
                apply=fix_typo_call,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="fix_lowercase_bool",
                apply=fix_lowercase_bool,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="insert_missing_accumulator_init",
                apply=insert_missing_accumulator_init,
                symptoms=("err:UnboundLocalError", "err:NameError"),
            ),
            Rule(
                name="fix_premature_false_in_loop",
                apply=fix_premature_false_in_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="insert_missing_filter_helper",
                apply=insert_missing_filter_helper,
                symptoms=("err:NameError",),
            ),
        ]