import ast
import re
import builtins

from src.core.repair import Rule


BUILTIN_NAMES = set(dir(builtins)) | {"True", "False", "None"}


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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# 1-4: threshold comparisons for "unique" counting (count vs 1) are wrong.
# ---------------------------------------------------------------------------

def _lte1_to_eq1(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.LtE):
            comp = node.comparators[0]
            if isinstance(comp, ast.Constant) and comp.value == 1:
                left = node.left
                ls, le = _span(source, left)
                rs, re_ = _span(source, comp)
                new_cmp = source[ls:le] + " == " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


def _lt2_to_eq1(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Lt):
            comp = node.comparators[0]
            if isinstance(comp, ast.Constant) and comp.value == 2:
                left = node.left
                ls, le = _span(source, left)
                new_cmp = source[ls:le] + " == 1"
                out.append(_splice(source, node, new_cmp))
    return out


def _gt1_to_ne1(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Gt):
            comp = node.comparators[0]
            if isinstance(comp, ast.Constant) and comp.value == 1:
                left = node.left
                ls, le = _span(source, left)
                rs, re_ = _span(source, comp)
                new_cmp = source[ls:le] + " != " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


def _gte2_to_ne1(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.GtE):
            comp = node.comparators[0]
            if isinstance(comp, ast.Constant) and comp.value == 2:
                left = node.left
                ls, le = _span(source, left)
                new_cmp = source[ls:le] + " != 1"
                out.append(_splice(source, node, new_cmp))
    return out


# ---------------------------------------------------------------------------
# 5: contains_unique_day needs "at least one" unique day, not exactly one.
# ---------------------------------------------------------------------------

def _contains_unique_day_eq_to_any(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == "contains_unique_day":
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                   and isinstance(node.ops[0], ast.Eq):
                    comp = node.comparators[0]
                    if isinstance(comp, ast.Constant) and comp.value == 1:
                        left = node.left
                        ls, le = _span(source, left)
                        rs, re_ = _span(source, comp)
                        new_cmp = source[ls:le] + " >= " + source[rs:re_]
                        out.append(_splice(source, node, new_cmp))
    return out


# ---------------------------------------------------------------------------
# 6: an undefined identifier is used where the function parameter was meant.
# ---------------------------------------------------------------------------

def _rename_undefined_to_param(source):
    tree = _parse(source)
    if tree is None:
        return []
    module_funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name in ("unique_day", "unique_month"):
            params = [a.arg for a in fn.args.args]
            if not params:
                continue
            target_param = params[0]
            assigned = set(params)
            for n in ast.walk(fn):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    assigned.add(n.id)

            undefined_spans = {}
            for n in ast.walk(fn):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    if n.id == target_param:
                        continue
                    if n.id in assigned or n.id in module_funcs or n.id in BUILTIN_NAMES:
                        continue
                    undefined_spans.setdefault(n.id, []).append(_span(source, n))

            for name_id, spans in undefined_spans.items():
                new_source = source
                for s, e in sorted(spans, key=lambda t: -t[0]):
                    new_source = new_source[:s] + target_param + new_source[e:]
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# 7: the comparison re-checks the counter variable instead of the parameter.
# ---------------------------------------------------------------------------

def _counter_used_instead_of_param(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name in ("unique_day", "unique_month"):
            params = [a.arg for a in fn.args.args]
            if not params:
                continue
            param = params[0]
            counter_name = None
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                   and isinstance(n.targets[0], ast.Name):
                    if isinstance(n.value, ast.Constant) and n.value.value == 0:
                        counter_name = n.targets[0].id
            if not counter_name or counter_name == param:
                continue
            for n in ast.walk(fn):
                if isinstance(n, ast.Compare):
                    ids = [x.id for x in ast.walk(n) if isinstance(x, ast.Name)]
                    if counter_name in ids and param not in ids:
                        s, e = _span(source, n)
                        text = source[s:e]
                        new_text = re.sub(r'\b' + re.escape(counter_name) + r'\b',
                                           param, text)
                        if new_text != text:
                            out.append(_splice(source, n, new_text))
    return out


# ---------------------------------------------------------------------------
# 8: an accumulator (counter / flag / tuple) is used but never initialized.
# ---------------------------------------------------------------------------

def _insert_missing_accumulator_init(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = {a.arg for a in fn.args.args}
        plain_assigned = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
               and isinstance(n.targets[0], ast.Name):
                xid = n.targets[0].id
                refs = [x.id for x in ast.walk(n.value) if isinstance(x, ast.Name)]
                if xid not in refs:
                    plain_assigned.add(xid)

        candidates = []
        for stmt in ast.walk(fn):
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                xid = stmt.target.id
                if xid in params or xid in plain_assigned:
                    continue
                init_val = "()" if isinstance(stmt.value, ast.Tuple) else "0"
                candidates.append((stmt, xid, init_val))
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                    and isinstance(stmt.targets[0], ast.Name):
                xid = stmt.targets[0].id
                refs = [x.id for x in ast.walk(stmt.value) if isinstance(x, ast.Name)]
                if xid in refs and xid not in params and xid not in plain_assigned:
                    if isinstance(stmt.value, ast.BoolOp) and isinstance(stmt.value.op, ast.Or):
                        init_val = "False"
                    elif isinstance(stmt.value, ast.BinOp) and (
                            isinstance(stmt.value.right, ast.Tuple)
                            or isinstance(stmt.value.left, ast.Tuple)):
                        init_val = "()"
                    else:
                        init_val = "0"
                    candidates.append((stmt, xid, init_val))

        for stmt, xid, init_val in candidates:
            top_stmt = None
            ss, se = _span(source, stmt)
            for b in fn.body:
                bs, be = _span(source, b)
                if bs <= ss and se <= be:
                    top_stmt = b
                    break
            if top_stmt is None:
                continue
            s, _e = _span(source, top_stmt)
            line_start = source.rfind("\n", 0, s) + 1
            indent = source[line_start:s]
            insertion = f"{indent}{xid} = {init_val}\n"
            out.append(source[:line_start] + insertion + source[line_start:])
    return out


# ---------------------------------------------------------------------------
# 9: a helper function is called under a misspelled/undefined name.
# ---------------------------------------------------------------------------

def _common_prefix_len(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _typo_call_rename(source):
    tree = _parse(source)
    if tree is None:
        return []
    module_funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not module_funcs:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fid = node.func.id
            if fid in module_funcs or fid in BUILTIN_NAMES:
                continue
            best = None
            for mf in module_funcs:
                if _common_prefix_len(mf, fid) >= 6 and abs(len(mf) - len(fid)) <= 3:
                    best = mf
                    break
            if best:
                s, e = _span(source, node.func)
                out.append(source[:s] + best + source[e:])
    return out


# ---------------------------------------------------------------------------
# 10: lowercase true/false literal typos.
# ---------------------------------------------------------------------------

def _lowercase_bool_fix(source):
    tree = _parse(source)
    if tree is None:
        return []
    assigned_all = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            assigned_all.add(n.id)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in ("false", "true"):
            if n.id in assigned_all:
                continue
            s, e = _span(source, n)
            repl = "False" if n.id == "false" else "True"
            out.append(source[:s] + repl + source[e:])
    return out


# ---------------------------------------------------------------------------
# 11: contains_unique_day calls unique_day without first filtering by month.
# ---------------------------------------------------------------------------

def _contains_unique_day_missing_month_filter(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not (isinstance(fn, ast.FunctionDef) and fn.name == "contains_unique_day"):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.For):
                continue
            if len(node.body) != 1 or not isinstance(node.body[0], ast.If):
                continue
            if not isinstance(node.target, ast.Name):
                continue
            ifnode = node.body[0]
            test = ifnode.test
            calls_unique_day = any(
                isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                and sub.func.id == "unique_day"
                for sub in ast.walk(test)
            )
            mentions_month = any(
                isinstance(sub, ast.Name) and sub.id == "month"
                for sub in ast.walk(test)
            )
            if not calls_unique_day or mentions_month:
                continue

            loopvar = node.target.id
            ifs, ife = _span(source, ifnode)
            if_text = source[ifs:ife]
            line_start = source.rfind("\n", 0, ifs) + 1
            indent = source[line_start:ifs]
            lines = if_text.split("\n")
            new_lines = [lines[0]] + ["    " + ln for ln in lines[1:]]
            reindented = "\n".join(new_lines)
            new_block = f"if month == {loopvar}[0]:\n{indent}    {reindented}"
            out.append(_splice(source, ifnode, new_block))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="lte1_to_eq1",
                apply=_lte1_to_eq1,
                symptoms=("wrong",),
            ),
            Rule(
                name="lt2_to_eq1",
                apply=_lt2_to_eq1,
                symptoms=("wrong",),
            ),
            Rule(
                name="gt1_to_ne1",
                apply=_gt1_to_ne1,
                symptoms=("wrong",),
            ),
            Rule(
                name="gte2_to_ne1",
                apply=_gte2_to_ne1,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_eq_to_any",
                apply=_contains_unique_day_eq_to_any,
                symptoms=("wrong",),
            ),
            Rule(
                name="rename_undefined_to_param",
                apply=_rename_undefined_to_param,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="counter_used_instead_of_param",
                apply=_counter_used_instead_of_param,
                symptoms=("wrong",),
            ),
            Rule(
                name="insert_missing_accumulator_init",
                apply=_insert_missing_accumulator_init,
                symptoms=("err:NameError", "err:UnboundLocalError"),
            ),
            Rule(
                name="typo_call_rename",
                apply=_typo_call_rename,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="lowercase_bool_fix",
                apply=_lowercase_bool_fix,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="contains_unique_day_missing_month_filter",
                apply=_contains_unique_day_missing_month_filter,
                symptoms=("wrong",),
            ),
        ]