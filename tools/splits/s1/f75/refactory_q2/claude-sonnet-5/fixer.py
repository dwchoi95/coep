"""
Repair module for the "Unique dates and months" assignment.

Each rule below targets one recurring misconception observed in the class's
buggy submissions and proposes small, local, AST-span based edits.  The
harness is expected to search over (possibly repeated/combined) application
of these candidate generators, so each rule intentionally produces minimal,
surgical edits rather than trying to fix an entire submission in one shot.
"""

import ast
import builtins

from src.core.repair import Rule


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------

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


def _apply_edits(source, edits):
    """edits: list of (start, end, replacement). Applied right-to-left."""
    edits = sorted(edits, key=lambda x: x[0], reverse=True)
    result = source
    for s, e, rep in edits:
        result = result[:s] + rep + result[e:]
    return result


def _get_index_value(subscript):
    sl = subscript.slice
    if isinstance(sl, ast.Constant):
        return sl.value
    idx_cls = getattr(ast, "Index", None)
    if idx_cls is not None and isinstance(sl, idx_cls):
        val = sl.value
        if isinstance(val, ast.Constant):
            return val.value
    return None


def _top_level_funcs(tree, names=None):
    out = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            if names is None or n.name in names:
                out.append(n)
    return out


# --------------------------------------------------------------------------
# Rule 1: undefined "free" identifier used instead of the real parameter
#   e.g. def unique_day(date, possible_birthdays): ... if i[1] == day: ...
#   -> rename every occurrence of the undefined name to the first parameter.
# --------------------------------------------------------------------------

def _free_var_to_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    module_func_names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    builtin_names = set(dir(builtins))

    for func in _top_level_funcs(tree, ("unique_day", "unique_month")):
        if not func.args.args:
            continue
        first_param = func.args.args[0].arg
        bound = {a.arg for a in func.args.args}

        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    for nm in ast.walk(t):
                        if isinstance(nm, ast.Name):
                            bound.add(nm.id)
            elif isinstance(n, ast.AugAssign):
                if isinstance(n.target, ast.Name):
                    bound.add(n.target.id)
            elif isinstance(n, ast.For):
                for nm in ast.walk(n.target):
                    if isinstance(nm, ast.Name):
                        bound.add(nm.id)
            elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for gen in n.generators:
                    for nm in ast.walk(gen.target):
                        if isinstance(nm, ast.Name):
                            bound.add(nm.id)

        free_by_name = {}
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if (n.id in bound or n.id in builtin_names or
                        n.id in module_func_names or n.id == first_param):
                    continue
                free_by_name.setdefault(n.id, []).append(n)

        for _name, nodes in free_by_name.items():
            edits = []
            for n in nodes:
                s, e = _span(source, n)
                edits.append((s, e, first_param))
            candidate = _apply_edits(source, edits)
            if candidate != source:
                out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Rule 2: counter/parameter name swap in the classic "range(len(...))"
#   template:
#       days = 0
#       for i in range(len(possible_birthdays)):
#           if possible_birthdays[i][1] == days:   # should compare to param
#               day = day + 1                      # should increment counter
# --------------------------------------------------------------------------

def _fix_counter_param_swap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for func in _top_level_funcs(tree, ("unique_day", "unique_month")):
        if not func.args.args:
            continue
        first_param = func.args.args[0].arg

        counter_name = None
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1 and
                    isinstance(node.targets[0], ast.Name) and
                    isinstance(node.value, ast.Constant) and node.value.value == 0):
                counter_name = node.targets[0].id
                break
        if counter_name is None or counter_name == first_param:
            continue

        edits = []
        for node in ast.walk(func):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and
                    isinstance(test.ops[0], ast.Eq)):
                continue
            comp = test.comparators[0]
            if not (isinstance(comp, ast.Name) and comp.id == counter_name):
                continue

            s, e = _span(source, comp)
            edits.append((s, e, first_param))

            for stmt in node.body:
                bad_name = None
                target_node = None
                if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                    if stmt.target.id != counter_name:
                        bad_name = stmt.target.id
                        target_node = stmt.target
                elif (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and
                        isinstance(stmt.targets[0], ast.Name)):
                    if stmt.targets[0].id != counter_name:
                        bad_name = stmt.targets[0].id
                        target_node = stmt.targets[0]

                if bad_name is None:
                    continue
                ts, te = _span(source, target_node)
                edits.append((ts, te, counter_name))
                for nm in ast.walk(stmt.value):
                    if isinstance(nm, ast.Name) and nm.id == bad_name:
                        nvs, nve = _span(source, nm)
                        edits.append((nvs, nve, counter_name))

        if edits:
            candidate = _apply_edits(source, edits)
            if candidate != source:
                out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Rule 3: call to a never-defined helper name (typo for unique_day).
# --------------------------------------------------------------------------

def _rename_unique_date_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "unique_date" in defined:
        return []

    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "unique_date":
            s, e = _span(source, node)
            edits.append((s, e, "unique_day"))

    if not edits:
        return []
    candidate = _apply_edits(source, edits)
    return [candidate] if candidate != source else []


# --------------------------------------------------------------------------
# Rule 4: boolean literal typos (true/false/Flase/...) used as bare names.
# --------------------------------------------------------------------------

def _fix_bool_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    mapping = {"true": "True", "false": "False", "Flase": "False",
               "flase": "False", "Fasle": "False"}
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in mapping:
            s, e = _span(source, node)
            edits.append((s, e, mapping[node.id]))

    if not edits:
        return []
    candidate = _apply_edits(source, edits)
    return [candidate] if candidate != source else []


# --------------------------------------------------------------------------
# Rule 5: accumulator variable used (via += or "x = x op ...") without ever
#   being initialized -> UnboundLocalError.  Insert an initializer right
#   before the first statement that contains its first use.
# --------------------------------------------------------------------------

def _init_accumulator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out_edits = []
    for func in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        plain_assigns = {}
        self_refs = {}

        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1 and
                    isinstance(node.targets[0], ast.Name)):
                name = node.targets[0].id
                refs_self = any(isinstance(x, ast.Name) and x.id == name
                                 for x in ast.walk(node.value))
                s, _e = _span(source, node)
                if refs_self:
                    kind = "bool" if isinstance(node.value, ast.BoolOp) else "num"
                    self_refs.setdefault(name, []).append((s, kind))
                else:
                    plain_assigns.setdefault(name, []).append(s)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                s, _e = _span(source, node)
                self_refs.setdefault(name, []).append((s, "num"))

        for name, refs in self_refs.items():
            refs.sort(key=lambda t: t[0])
            first_s, kind = refs[0]
            earlier = [p for p in plain_assigns.get(name, []) if p < first_s]
            if earlier:
                continue

            target_stmt = None
            for stmt in func.body:
                ss, se = _span(source, stmt)
                if ss <= first_s < se:
                    target_stmt = stmt
                    break
            if target_stmt is None:
                continue

            ts, _te = _span(source, target_stmt)
            indent = " " * target_stmt.col_offset
            init_val = "False" if kind == "bool" else "0"
            out_edits.append((ts, ts, f"{name} = {init_val}\n{indent}"))

    if not out_edits:
        return []
    candidate = _apply_edits(source, out_edits)
    return [candidate] if candidate != source else []


# --------------------------------------------------------------------------
# Rule 6: wrong threshold comparison for "exactly one occurrence".
#   count <= 1 / count < 2 / count >= 2   ->   count == 1
# --------------------------------------------------------------------------

def _fix_threshold_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for func in _top_level_funcs(tree, ("unique_day", "unique_month")):
        for node in ast.walk(func):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and
                    len(node.comparators) == 1):
                continue
            op = node.ops[0]
            comp = node.comparators[0]
            if not isinstance(comp, ast.Constant):
                continue

            matches = ((isinstance(op, ast.LtE) and comp.value == 1) or
                       (isinstance(op, ast.Lt) and comp.value == 2) or
                       (isinstance(op, ast.GtE) and comp.value == 2))
            if not matches:
                continue

            left_s, left_e = _span(source, node.left)
            new_text = source[left_s:left_e] + " == 1"
            candidate = _splice(source, node, new_text)
            if candidate != source:
                out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Rule 7: function ends with a bare "return True" even though a preceding
#   "if counter > 1: return False" (or >= 2) means the zero-matches case is
#   never rejected.  Replace the trailing return with "return counter == 1".
# --------------------------------------------------------------------------

def _fix_final_return_true(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for func in _top_level_funcs(tree, ("unique_day", "unique_month")):
        if not func.body:
            continue
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue

        varname = None
        for n in ast.walk(func):
            if not isinstance(n, ast.If):
                continue
            test = n.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and
                    len(test.comparators) == 1 and isinstance(test.left, ast.Name)):
                continue
            op = test.ops[0]
            comp = test.comparators[0]
            if not isinstance(comp, ast.Constant):
                continue
            if ((isinstance(op, ast.Gt) and comp.value == 1) or
                    (isinstance(op, ast.GtE) and comp.value == 2)):
                has_return_false = any(
                    isinstance(s, ast.Return) and isinstance(s.value, ast.Constant)
                    and s.value.value is False for s in n.body)
                if has_return_false:
                    varname = test.left.id
                    break

        if varname:
            candidate = _splice(source, last, f"return {varname} == 1")
            if candidate != source:
                out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Rule 8: contains_unique_day calls unique_day with the wrong tuple index
#   (month index 0 instead of the day index 1).
# --------------------------------------------------------------------------

def _fix_unique_day_call_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for func in _top_level_funcs(tree, ("contains_unique_day",)):
        for node in ast.walk(func):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "unique_day" and node.args):
                continue
            first = node.args[0]
            if not isinstance(first, ast.Subscript):
                continue
            idx = _get_index_value(first)
            if idx != 0:
                continue
            s, e = _span(source, first.slice)
            candidate = source[:s] + "1" + source[e:]
            if candidate != source:
                out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Rule 9: contains_unique_day compares the day-index (1) against the month
#   parameter instead of the month-index (0).
# --------------------------------------------------------------------------

def _fix_month_index_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for func in _top_level_funcs(tree, ("contains_unique_day",)):
        if not func.args.args:
            continue
        month_param = func.args.args[0].arg
        for node in ast.walk(func):
            if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and
                    isinstance(node.ops[0], ast.Eq)):
                continue
            left, right = node.left, node.comparators[0]
            for a, b in ((left, right), (right, left)):
                if (isinstance(a, ast.Subscript) and isinstance(b, ast.Name)
                        and b.id == month_param):
                    idx = _get_index_value(a)
                    if idx == 1:
                        s, e = _span(source, a.slice)
                        candidate = source[:s] + "0" + source[e:]
                        if candidate != source:
                            out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Rule 10: the final for-loop of contains_unique_day returns False in its
#   else-branch, aborting the search after the first mismatch, instead of
#   continuing and returning False only once the loop is exhausted.
# --------------------------------------------------------------------------

def _fix_loop_return_false_to_continue(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for func in _top_level_funcs(tree, ("contains_unique_day",)):
        if not func.body:
            continue
        last = func.body[-1]
        if not isinstance(last, ast.For):
            continue
        if len(last.body) != 1 or not isinstance(last.body[0], ast.If):
            continue
        ifnode = last.body[0]
        if len(ifnode.orelse) != 1:
            continue
        orelse_stmt = ifnode.orelse[0]
        if not (isinstance(orelse_stmt, ast.Return) and
                isinstance(orelse_stmt.value, ast.Constant) and
                orelse_stmt.value.value is False):
            continue

        s1, e1 = _span(source, orelse_stmt)
        _for_s, for_e = _span(source, last)
        indent = " " * last.col_offset
        edits = [
            (s1, e1, "continue"),
            (for_e, for_e, "\n" + indent + "return False"),
        ]
        candidate = _apply_edits(source, edits)
        if candidate != source:
            out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Rule 11: generic strict/non-strict comparison flip (cheap, broad slip).
# --------------------------------------------------------------------------

def _generic_comparison_flip(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    flip_map = {
        ast.Lt: "<=",
        ast.LtE: "<",
        ast.Gt: ">=",
        ast.GtE: ">",
    }
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and
                len(node.comparators) == 1):
            continue
        op = node.ops[0]
        sym = flip_map.get(type(op))
        if sym is None:
            continue
        left, right = node.left, node.comparators[0]
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        new_cmp = source[ls:le] + f" {sym} " + source[rs:re_]
        candidate = _splice(source, node, new_cmp)
        if candidate != source:
            out.append(candidate)

    return out


# --------------------------------------------------------------------------
# Fixer
# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="free_var_to_param",
                apply=_free_var_to_param,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="counter_param_name_swap",
                apply=_fix_counter_param_swap,
                symptoms=("wrong", "err:NameError", "err:UnboundLocalError"),
            ),
            Rule(
                name="rename_unique_date_call",
                apply=_rename_unique_date_call,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="bool_literal_typo",
                apply=_fix_bool_typo,
                symptoms=("err:NameError", "err:SyntaxError"),
            ),
            Rule(
                name="init_uninitialized_accumulator",
                apply=_init_accumulator,
                symptoms=("err:UnboundLocalError",),
            ),
            Rule(
                name="threshold_compare_to_eq1",
                apply=_fix_threshold_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="final_return_true_to_count_eq1",
                apply=_fix_final_return_true,
                symptoms=("wrong",),
            ),
            Rule(
                name="unique_day_call_wrong_index",
                apply=_fix_unique_day_call_index,
                symptoms=("wrong",),
            ),
            Rule(
                name="month_index_compare_fix",
                apply=_fix_month_index_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="loop_return_false_to_continue",
                apply=_fix_loop_return_false_to_continue,
                symptoms=("wrong",),
            ),
            Rule(
                name="comparison_flip_generic",
                apply=_generic_comparison_flip,
                symptoms=("wrong",),
            ),
        ]