import ast
import builtins as _builtins_mod

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


def _safe(fn):
    def wrapper(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapper


def _dedupe(items):
    seen = set()
    out = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _names_in_target(t):
    names = []
    if isinstance(t, ast.Name):
        names.append(t.id)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for elt in t.elts:
            names.extend(_names_in_target(elt))
    return names


def _edit_distance(a, b):
    if abs(len(a) - len(b)) > 1:
        return 2
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[len(a)][len(b)]


def _find_accumulator(for_node, src_name, loop_var):
    candidates = []
    for stmt in ast.walk(for_node):
        if isinstance(stmt, ast.Call):
            f = stmt.func
            if isinstance(f, ast.Attribute) and f.attr in ('append', 'extend', 'insert') \
               and isinstance(f.value, ast.Name):
                name = f.value.id
                if name not in (src_name, loop_var):
                    candidates.append(name)
        elif isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.target, ast.Name) and isinstance(stmt.op, ast.Add):
                name = stmt.target.id
                if name not in (src_name, loop_var):
                    candidates.append(name)
        elif isinstance(stmt, ast.Assign):
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                name = stmt.targets[0].id
                if name not in (src_name, loop_var) and isinstance(stmt.value, ast.BinOp) \
                   and isinstance(stmt.value.op, ast.Add):
                    left = stmt.value.left
                    if isinstance(left, ast.Name) and left.id == name:
                        candidates.append(name)
    if not candidates:
        return None
    counts = {}
    for c in candidates:
        counts[c] = counts.get(c, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _find_function_accumulator(fn):
    for stmt in fn.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
           and isinstance(stmt.targets[0], ast.Name):
            if isinstance(stmt.value, ast.List) and len(stmt.value.elts) == 0:
                name = stmt.targets[0].id
                for node in ast.walk(fn):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                       and node.func.attr in ('append', 'extend', 'insert') \
                       and isinstance(node.func.value, ast.Name) and node.func.value.id == name:
                        return name
    return None


def _contains_return(node):
    if isinstance(node, ast.Return):
        return True
    if isinstance(node, ast.FunctionDef):
        return False
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef):
            continue
        if _contains_return(child):
            return True
    return False


def _has_any_return(fn):
    for stmt in fn.body:
        if _contains_return(stmt):
            return True
    return False


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

@_safe
def list_builtin_to_param(source):
    """`list` (builtin) used where the parameter name was meant."""
    tree = ast.parse(source)
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if not fn.args.args:
            continue
        param = fn.args.args[0].arg
        if param == 'list':
            continue
        call_func_ids = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'list':
                call_func_ids.add(id(node.func))
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and node.id == 'list' and isinstance(node.ctx, ast.Load):
                if id(node) in call_func_ids:
                    continue
                out.append(_splice(source, node, param))
    return _dedupe(out)


@_safe
def membership_container_swap(source):
    """Membership / count() checked against the source list instead of the
    accumulator list that is actually being built."""
    tree = ast.parse(source)
    out = []
    for for_node in [n for n in ast.walk(tree) if isinstance(n, ast.For)]:
        if not isinstance(for_node.iter, ast.Name) or not isinstance(for_node.target, ast.Name):
            continue
        src_name = for_node.iter.id
        loop_var = for_node.target.id
        acc = _find_accumulator(for_node, src_name, loop_var)
        if not acc:
            continue
        for node in ast.walk(for_node):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
                continue
            op = node.ops[0]
            left = node.left
            right = node.comparators[0]
            if isinstance(op, (ast.In, ast.NotIn)):
                if isinstance(right, ast.Name) and right.id == src_name:
                    out.append(_splice(source, right, acc))
                elif isinstance(right, ast.Call) and isinstance(right.func, ast.Attribute) \
                        and right.func.attr == 'count' and isinstance(right.func.value, ast.Name) \
                        and right.func.value.id == src_name:
                    out.append(_splice(source, right.func.value, acc))
                if isinstance(left, ast.Name) and left.id == src_name and left.id != loop_var:
                    out.append(_splice(source, left, loop_var))
            elif isinstance(op, (ast.Eq, ast.Lt)):
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) \
                        and left.func.attr == 'count' and isinstance(left.func.value, ast.Name) \
                        and left.func.value.id == src_name:
                    if isinstance(op, ast.Eq) and isinstance(right, ast.Constant) and right.value == 1:
                        item_src = ''
                        if left.args:
                            i_s, i_e = _span(source, left.args[0])
                            item_src = source[i_s:i_e]
                        new_text = "%s.count(%s) == 0" % (acc, item_src)
                        out.append(_splice(source, node, new_text))
                    else:
                        out.append(_splice(source, left.func.value, acc))
    return _dedupe(out)


@_safe
def in_flip_direct_append(source):
    """`if x in acc: acc.append(x)` should be `not in` (backwards uniqueness check)."""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and not node.orelse:
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.In):
                left, right = test.left, test.comparators[0]
                if isinstance(right, ast.Name) and isinstance(left, ast.Name):
                    for stmt in node.body:
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            call = stmt.value
                            if isinstance(call.func, ast.Attribute) and call.func.attr == 'append' \
                               and isinstance(call.func.value, ast.Name) and call.func.value.id == right.id \
                               and len(call.args) == 1 and isinstance(call.args[0], ast.Name) \
                               and call.args[0].id == left.id:
                                ls, le = _span(source, left)
                                rs, re_ = _span(source, right)
                                new_cmp = source[ls:le] + " not in " + source[rs:re_]
                                out.append(_splice(source, test, new_cmp))
    return _dedupe(out)


@_safe
def unwrap_mutator_assign(source):
    """`x = x.append(y)` (or augassign) assigns None; keep just the call."""
    tree = ast.parse(source)
    out = []
    mutators = {'append', 'remove', 'extend', 'insert', 'pop', 'sort', 'reverse'}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) \
               and value.func.attr in mutators:
                vs, ve = _span(source, value)
                call_src = source[vs:ve]
                out.append(_splice(source, node, call_src))
    return _dedupe(out)


@_safe
def add_missing_call_parens(source):
    """`x.pop` / `x.reverse` used as a statement or return value without `()`."""
    tree = ast.parse(source)
    out = []
    mutators = {'append', 'pop', 'extend', 'remove', 'reverse', 'insert', 'sort'}
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute):
            target = node.value
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute):
            target = node.value
        if target is not None and target.attr in mutators:
            s, e = _span(source, target)
            out.append(_splice(source, target, source[s:e] + "()"))
    return _dedupe(out)


@_safe
def subscript_to_call(source):
    """`x.append[y]` / `x.count[y]` should be a call, not a subscript."""
    tree = ast.parse(source)
    out = []
    mutators = {'append', 'count', 'extend', 'remove'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
           and node.value.attr in mutators:
            sl = node.slice
            expr = sl.value if isinstance(sl, ast.Index) else sl
            fs, fe = _span(source, node.value)
            es, ee = _span(source, expr)
            new_text = source[fs:fe] + "(" + source[es:ee] + ")"
            out.append(_splice(source, node, new_text))
    return _dedupe(out)


@_safe
def fix_return_variable(source):
    """`return` of the wrong variable instead of the accumulator list."""
    tree = ast.parse(source)
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        acc = _find_function_accumulator(fn)
        if not acc:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id != acc:
                    out.append(_splice(source, node.value, acc))
    return _dedupe(out)


@_safe
def add_missing_return(source):
    """Function builds an accumulator list but never returns it."""
    tree = ast.parse(source)
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        acc = _find_function_accumulator(fn)
        if not acc:
            continue
        if not fn.body:
            continue
        if _has_any_return(fn):
            continue
        last_stmt = fn.body[-1]
        _, e = _span(source, last_stmt)
        indent = ' ' * last_stmt.col_offset
        insertion = "\n" + indent + "return %s" % acc
        out.append(source[:e] + insertion + source[e:])
    return _dedupe(out)


@_safe
def fix_loop_target_clash(source):
    """for-loop target reuses the accumulator's name, shadowing it."""
    tree = ast.parse(source)
    out = []
    for for_node in [n for n in ast.walk(tree) if isinstance(n, ast.For)]:
        if not isinstance(for_node.target, ast.Name):
            continue
        tname = for_node.target.id
        used_as_container = False
        item_name = None
        for node in ast.walk(for_node):
            if node is for_node.target:
                continue
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
               and node.func.attr in ('append', 'extend', 'insert') \
               and isinstance(node.func.value, ast.Name) and node.func.value.id == tname:
                used_as_container = True
                if node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Name):
                        item_name = arg.id
                    elif isinstance(arg, ast.List) and len(arg.elts) == 1 \
                            and isinstance(arg.elts[0], ast.Name):
                        item_name = arg.elts[0].id
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) \
               and node.target.id == tname and isinstance(node.op, ast.Add):
                used_as_container = True
                val = node.value
                if isinstance(val, (ast.List, ast.Tuple)) and len(val.elts) == 1 \
                        and isinstance(val.elts[0], ast.Name):
                    item_name = val.elts[0].id
        if used_as_container and item_name and item_name != tname:
            out.append(_splice(source, for_node.target, item_name))
    return _dedupe(out)


@_safe
def fix_return_none_empty(source):
    """`if lst == []: return None` should return `[]`."""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            is_empty_check = False
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                right = test.comparators[0]
                if isinstance(right, ast.List) and len(right.elts) == 0:
                    is_empty_check = True
            if is_empty_check:
                for stmt in node.body:
                    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) \
                       and stmt.value.value is None:
                        out.append(_splice(source, stmt.value, "[]"))
    return _dedupe(out)


@_safe
def split_reverse_return(source):
    """`return x.reverse()` returns None; reverse then return the name."""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == 'reverse' \
               and isinstance(call.func.value, ast.Name):
                name = call.func.value.id
                indent = ' ' * node.col_offset
                new_text = "%s.reverse()\n%sreturn %s" % (name, indent, name)
                out.append(_splice(source, node, new_text))
    return _dedupe(out)


@_safe
def fix_eq_list_should_be_in(source):
    """`item != acc_list` used instead of `item not in acc_list`."""
    tree = ast.parse(source)
    out = []
    for for_node in [n for n in ast.walk(tree) if isinstance(n, ast.For)]:
        acc = None
        for node in ast.walk(for_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
               and node.func.attr in ('append', 'extend') and isinstance(node.func.value, ast.Name):
                acc = node.func.value.id
                break
        if not acc:
            continue
        for node in ast.walk(for_node):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 \
               and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                right = node.comparators[0]
                if isinstance(right, ast.Name) and right.id == acc:
                    left = node.left
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    op_text = "not in" if isinstance(node.ops[0], ast.NotEq) else "in"
                    new_cmp = source[ls:le] + (" %s " % op_text) + source[rs:re_]
                    out.append(_splice(source, node, new_cmp))
    return _dedupe(out)


@_safe
def typo_fix(source):
    """An undefined name that is a one-edit typo of a defined name/function."""
    tree = ast.parse(source)
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            bound.add(node.name)
            for a in node.args.args:
                bound.add(a.arg)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                for nm in _names_in_target(t):
                    bound.add(nm)
        elif isinstance(node, ast.AugAssign):
            for nm in _names_in_target(node.target):
                bound.add(nm)
        elif isinstance(node, ast.For):
            for nm in _names_in_target(node.target):
                bound.add(nm)
    builtin_names = set(dir(_builtins_mod))
    out = []
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            nid = node.id
            if nid in bound or nid in builtin_names:
                continue
            best = None
            for b in bound:
                if b == nid:
                    continue
                if _edit_distance(nid, b) == 1:
                    best = b
                    break
            if best is not None:
                key = (node.lineno, node.col_offset, best)
                if key in seen:
                    continue
                seen.add(key)
                out.append(_splice(source, node, best))
    return _dedupe(out)


class Fixer:
    def rules(self):
        return [
            Rule(name="list_builtin_to_param", apply=list_builtin_to_param,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="membership_container_swap", apply=membership_container_swap,
                 symptoms=("wrong",)),
            Rule(name="in_flip_direct_append", apply=in_flip_direct_append,
                 symptoms=("wrong",)),
            Rule(name="unwrap_mutator_assign", apply=unwrap_mutator_assign,
                 symptoms=("wrong", "err:AttributeError", "err:TypeError")),
            Rule(name="add_missing_call_parens", apply=add_missing_call_parens,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="subscript_to_call", apply=subscript_to_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_return_variable", apply=fix_return_variable,
                 symptoms=("wrong",)),
            Rule(name="add_missing_return", apply=add_missing_return,
                 symptoms=("wrong",)),
            Rule(name="fix_loop_target_clash", apply=fix_loop_target_clash,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_return_none_empty", apply=fix_return_none_empty,
                 symptoms=("wrong",)),
            Rule(name="split_reverse_return", apply=split_reverse_return,
                 symptoms=("wrong",)),
            Rule(name="fix_eq_list_should_be_in", apply=fix_eq_list_should_be_in,
                 symptoms=("wrong",)),
            Rule(name="typo_fix", apply=typo_fix,
                 symptoms=("err:NameError", "wrong")),
        ]