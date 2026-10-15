"""
Repair module for the "Unique dates and months" assignment.

Targets a set of common, recurring misconceptions found across student
submissions for unique_day / unique_month / contains_unique_day:

  - undefined domain variable (parameter renamed but body still refers
    to the old name, e.g. `day` used when the parameter is `date`)
  - month/day index confusion (birthday[0] vs birthday[1])
  - loose count comparisons (`<= 1`, `>= 2`, `> 1`) that should be `== 1`
  - lowercase `true`/`false` typos
  - `unique_date` call typo for `unique_day`
  - contains_unique_day missing a trailing `return False`
  - contains_unique_day search loop returning False on the first miss
    instead of continuing
  - tuple accumulation using `x = x + i` instead of `x = x + (i,)`
  - counter used via `+=`/`= x + 1` inside a loop without being
    initialized beforehand
"""

import ast

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# small AST/source helpers
# ---------------------------------------------------------------------------

def _line_starts(source):
    starts = [0]
    for ln in source.splitlines(keepends=True):
        starts.append(starts[-1] + len(ln))
    return starts


def _span(source, node, starts=None):
    if starts is None:
        starts = _line_starts(source)
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _multi_splice(source, edits):
    # edits: list of (start, end, text) - non-overlapping
    edits = sorted(edits, key=lambda x: x[0], reverse=True)
    for s, e, t in edits:
        source = source[:s] + t + source[e:]
    return source


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _enclosing_function(node):
    cur = getattr(node, 'parent', None)
    while cur is not None and not isinstance(cur, ast.FunctionDef):
        cur = getattr(cur, 'parent', None)
    return cur


def _indent_of(source, node):
    starts = _line_starts(source)
    line_start = starts[node.lineno - 1]
    s, _ = _span(source, node)
    return source[line_start:s]


_DOMAIN_WORDS = {'day', 'date', 'month'}


# ---------------------------------------------------------------------------
# Rule A: undefined domain variable (name mismatch with parameter)
# ---------------------------------------------------------------------------

def _rename_undefined_domain_vars(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        first = params[0]
        if first not in _DOMAIN_WORDS:
            continue
        bound = set(params)
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                bound.add(n.id)
            if isinstance(n, ast.arg):
                bound.add(n.arg)
        undefined_ids = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id in _DOMAIN_WORDS and n.id not in bound:
                    undefined_ids.add(n.id)
        for uid in undefined_ids:
            if uid == first:
                continue
            edits = []
            for n in ast.walk(func):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == uid:
                    s, e = _span(source, n)
                    edits.append((s, e, first))
            if edits:
                out.append(_multi_splice(source, edits))
    return out


# ---------------------------------------------------------------------------
# Rule B: month/day tuple index confusion
# ---------------------------------------------------------------------------

def _get_index_constant(sub):
    sl = sub.slice
    if isinstance(sl, ast.Constant):
        return sl
    val = getattr(sl, 'value', None)
    if isinstance(val, ast.Constant):
        return val
    return None


def _month_day_index_fix(source):
    tree = _parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for cmp_node in [n for n in ast.walk(tree)
                      if isinstance(n, ast.Compare) and len(n.ops) == 1
                      and isinstance(n.ops[0], ast.Eq)]:
        func = _enclosing_function(cmp_node)
        if func is None or not func.args.args:
            continue
        param0 = func.args.args[0].arg
        sides = [cmp_node.left] + list(cmp_node.comparators)
        name_side = None
        sub_side = None
        for s in sides:
            if isinstance(s, ast.Name) and s.id == param0:
                name_side = s
            elif isinstance(s, ast.Subscript):
                sub_side = s
        if name_side is None or sub_side is None:
            continue
        const_node = _get_index_constant(sub_side)
        if const_node is None or not isinstance(const_node.value, int):
            continue
        lowp = param0.lower()
        if 'month' in lowp and const_node.value == 1:
            out.append(_splice(source, const_node, '0'))
        elif ('day' in lowp or 'date' in lowp) and const_node.value == 0:
            out.append(_splice(source, const_node, '1'))
    return out


# ---------------------------------------------------------------------------
# Rule C: loose count comparisons should be == 1
# ---------------------------------------------------------------------------

def _count_compare_relax(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []

    for ret in [n for n in ast.walk(tree) if isinstance(n, ast.Return) and n.value is not None]:
        v = ret.value
        if isinstance(v, ast.Compare) and len(v.ops) == 1 and isinstance(v.left, ast.Name):
            op = v.ops[0]
            comp = v.comparators[0]
            if isinstance(comp, ast.Constant) and isinstance(comp.value, int) and comp.value in (0, 1, 2):
                if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    new_text = v.left.id + ' == 1'
                    out.append(_splice(source, v, new_text))

    for ifnode in [n for n in ast.walk(tree) if isinstance(n, ast.If)]:
        test = ifnode.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.left, ast.Name)):
            continue
        op = test.ops[0]
        comp = test.comparators[0]
        if not (isinstance(comp, ast.Constant) and isinstance(comp.value, int) and comp.value in (1, 2)):
            continue
        if not isinstance(op, (ast.Gt, ast.GtE)):
            continue
        body = ifnode.body
        if len(body) == 1 and isinstance(body[0], ast.Return) \
           and isinstance(body[0].value, ast.Constant) and body[0].value.value is False:
            new_text = test.left.id + ' != 1'
            out.append(_splice(source, test, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule D: lowercase true/false typo
# ---------------------------------------------------------------------------

def _lowercase_bool_fix(source):
    tree = _parse(source)
    if tree is None:
        return []
    edits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in ('true', 'false'):
            s, e = _span(source, n)
            edits.append((s, e, 'True' if n.id == 'true' else 'False'))
    if not edits:
        return []
    return [_multi_splice(source, edits)]


# ---------------------------------------------------------------------------
# Rule E: unique_date typo call -> unique_day
# ---------------------------------------------------------------------------

def _typo_call_fix(source):
    tree = _parse(source)
    if tree is None:
        return []
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    if 'unique_day' not in defined:
        return []
    edits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id == 'unique_date' and 'unique_date' not in defined:
                s, e = _span(source, n.func)
                edits.append((s, e, 'unique_day'))
    if not edits:
        return []
    return [_multi_splice(source, edits)]


# ---------------------------------------------------------------------------
# Rule F: contains_unique_day missing trailing return False
# ---------------------------------------------------------------------------

def _missing_return_false_append(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if func.name != 'contains_unique_day' or not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, (ast.For, ast.While)):
            indent = _indent_of(source, func.body[0])
            s, e = _span(source, last)
            insertion = '\n' + indent + 'return False'
            out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule G: search-loop else-return-False should be continue
# ---------------------------------------------------------------------------

def _break_return_false_to_continue(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if func.name != 'contains_unique_day':
            continue
        for forn in [n for n in ast.walk(func) if isinstance(n, ast.For)]:
            for stmt in forn.body:
                if isinstance(stmt, ast.If) and stmt.orelse:
                    orelse = stmt.orelse
                    if len(orelse) == 1 and isinstance(orelse[0], ast.Return) \
                       and isinstance(orelse[0].value, ast.Constant) \
                       and orelse[0].value.value is False:
                        has_true_return = any(
                            isinstance(x, ast.Return) and isinstance(x.value, ast.Constant)
                            and x.value.value is True
                            for x in ast.walk(stmt) if x is not orelse[0]
                        )
                        if has_true_return:
                            out.append(_splice(source, orelse[0], 'continue'))
    return out


# ---------------------------------------------------------------------------
# Rule H: tuple accumulation missing the trailing comma / parens
# ---------------------------------------------------------------------------

def _tuple_concat_fix(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        tuple_vars = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                if isinstance(n.value, ast.Tuple) and not n.value.elts:
                    tuple_vars.add(n.targets[0].id)
        if not tuple_vars:
            continue
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                tgt = n.targets[0].id
                if tgt not in tuple_vars:
                    continue
                val = n.value
                if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add) \
                   and isinstance(val.left, ast.Name) and val.left.id == tgt \
                   and not isinstance(val.right, ast.Tuple):
                    ls, le = _span(source, val.left)
                    rs, re_ = _span(source, val.right)
                    right_src = source[rs:re_]
                    new_val_text = source[ls:le] + ' + (' + right_src + ',)'
                    out.append(_splice(source, val, new_val_text))
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) \
                    and n.target.id in tuple_vars and isinstance(n.op, ast.Add) \
                    and not isinstance(n.value, ast.Tuple):
                vs, ve = _span(source, n.value)
                val_src = source[vs:ve]
                new_text = '(' + val_src + ',)'
                out.append(_splice(source, n.value, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule I: counter used inside a loop without a prior initialization
# ---------------------------------------------------------------------------

def _missing_counter_init(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        assigned_const = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
               and isinstance(n.value, ast.Constant) and isinstance(n.value.value, int):
                assigned_const.add(n.targets[0].id)
        for stmt in func.body:
            if not isinstance(stmt, ast.For):
                continue
            for n in ast.walk(stmt):
                target_name = None
                if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and isinstance(n.op, ast.Add):
                    target_name = n.target.id
                elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                        and isinstance(n.value, ast.BinOp) and isinstance(n.value.op, ast.Add) \
                        and isinstance(n.value.left, ast.Name) and n.value.left.id == n.targets[0].id:
                    target_name = n.targets[0].id
                if target_name and target_name not in assigned_const:
                    indent = _indent_of(source, stmt)
                    s, _e = _span(source, stmt)
                    insertion = target_name + ' = 0\n' + indent
                    out.append(source[:s] + insertion + source[s:])
    return out


# ---------------------------------------------------------------------------
# Fixer
# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="undefined_domain_var_rename",
                apply=_rename_undefined_domain_vars,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="month_day_index_fix",
                apply=_month_day_index_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="count_compare_relax",
                apply=_count_compare_relax,
                symptoms=("wrong",),
            ),
            Rule(
                name="lowercase_bool_fix",
                apply=_lowercase_bool_fix,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="typo_call_fix",
                apply=_typo_call_fix,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="missing_return_false_append",
                apply=_missing_return_false_append,
                symptoms=("wrong",),
            ),
            Rule(
                name="break_return_false_to_continue",
                apply=_break_return_false_to_continue,
                symptoms=("wrong",),
            ),
            Rule(
                name="tuple_concat_fix",
                apply=_tuple_concat_fix,
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="missing_counter_init",
                apply=_missing_counter_init,
                symptoms=("err:UnboundLocalError", "err:NameError"),
            ),
        ]