"""
Repair module for the "Duplicate elimination" (remove_extras) assignment.

Each Rule below targets one recurring misconception observed in the class's
buggy submissions. Rules operate purely on the AST structure (never on the
literal example programs) and splice a minimal, local text edit into the
original source, leaving everything else byte-for-byte identical.
"""

import ast
from src.core.repair import Rule


# --------------------------------------------------------------------------
# Generic AST / text-splicing helpers
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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _splice_many(source, replacements):
    """replacements: list of (start, end, text); applied right-to-left."""
    out = source
    for s, e, text in sorted(replacements, key=lambda t: -t[0]):
        out = out[:s] + text + out[e:]
    return out


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _funcdefs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _find_empty_list_accumulator(func):
    """Name of the variable assigned an empty list literal (preferred),
    falling back to an empty tuple literal if no list is found."""
    tuple_fallback = None
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            v = node.value
            if isinstance(v, ast.List) and not v.elts:
                return node.targets[0].id
            if isinstance(v, ast.Tuple) and not v.elts and tuple_fallback is None:
                tuple_fallback = node.targets[0].id
    return tuple_fallback


def _mutation_targets(scope_node):
    """Names mutated via .append/.extend calls or += within scope_node."""
    names = {}
    for n in ast.walk(scope_node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
           and n.func.attr in ('append', 'extend') and isinstance(n.func.value, ast.Name):
            names[n.func.value.id] = names.get(n.func.value.id, 0) + 1
        elif isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) \
             and isinstance(n.target, ast.Name):
            names[n.target.id] = names.get(n.target.id, 0) + 1
    return names


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
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (0 if a[i - 1] == b[j - 1] else 1))
            prev = cur
    return dp[lb]


# --------------------------------------------------------------------------
# Rule 1: `for x in list:` / `in list` -- builtin `list` used instead of the
# actual parameter name.
# --------------------------------------------------------------------------

def fix_list_builtin(source):
    """Replace stray uses of the `list` builtin name with the real param."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        args = [a.arg for a in func.args.args]
        if not args or args[0] == 'list':
            continue
        param = args[0]
        assigned = set(args)
        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                assigned.add(n.target.id)
            elif isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                assigned.add(n.target.id)
        if 'list' in assigned:
            continue
        targets = [n for n in ast.walk(func)
                   if isinstance(n, ast.Name) and n.id == 'list' and isinstance(n.ctx, ast.Load)]
        if not targets:
            continue
        reps = [(*_span(source, n), param) for n in targets]
        new_src = _splice_many(source, reps)
        if new_src != source:
            out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 2: a typo'd / undefined name is used as the target of .append/.extend
# instead of the real accumulator list.
# --------------------------------------------------------------------------

def fix_undefined_accumulator_target(source):
    """Rename an undefined .append()/.extend() target to the real accumulator."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        acc = _find_empty_list_accumulator(func)
        if not acc:
            continue
        defined = {a.arg for a in func.args.args}
        defined.add(func.name)
        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        defined.add(t.id)
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                defined.add(n.target.id)
            elif isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                defined.add(n.target.id)
        bad_names = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
               and n.func.attr in ('append', 'extend') and isinstance(n.func.value, ast.Name):
                name = n.func.value.id
                if name != acc and name not in defined:
                    bad_names.add(name)
        for bad in bad_names:
            reps = [(*_span(source, n), acc) for n in ast.walk(func)
                    if isinstance(n, ast.Name) and n.id == bad]
            if reps:
                new_src = _splice_many(source, reps)
                if new_src != source:
                    out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 3: function returns the wrong name (input list, loop var, or an
# undefined name) instead of the real accumulator.
# --------------------------------------------------------------------------

def fix_return_wrong_name(source):
    """Replace `return X` with `return ACC` when ACC is the real accumulator."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        acc = _find_empty_list_accumulator(func)
        if not acc:
            continue
        mutated = _mutation_targets(func)
        if acc not in mutated:
            continue
        for n in ast.walk(func):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id != acc:
                new_src = _splice(source, n.value, acc)
                if new_src != source:
                    out.append(new_src)
    return out


def fix_missing_return(source):
    """Insert `return ACC` when the function builds ACC but never returns it."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        acc = _find_empty_list_accumulator(func)
        if not acc:
            continue
        mutated = _mutation_targets(func)
        if acc not in mutated:
            continue
        if not func.body:
            continue
        last = func.body[-1]
        _, e = _span(source, last)
        indent = ' ' * last.col_offset
        new_src = source[:e] + "\n" + indent + "return " + acc + source[e:]
        out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 4/5: the dedup check compares against the wrong container, or tests
# the wrong item.
# --------------------------------------------------------------------------

def fix_membership_checks(source):
    """Fix `if X not in Y` inside the accumulate loop when X or Y is wrong."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        for forn in ast.walk(func):
            if not isinstance(forn, ast.For) or not isinstance(forn.target, ast.Name):
                continue
            loopvar = forn.target.id
            itername = forn.iter.id if isinstance(forn.iter, ast.Name) else None
            for ifn in ast.walk(forn):
                if ifn is forn or not isinstance(ifn, ast.If):
                    continue
                test = ifn.test
                if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                        and isinstance(test.ops[0], (ast.In, ast.NotIn))):
                    continue
                left = test.left
                right = test.comparators[0]
                muts = _mutation_targets(ifn)
                acc = max(muts, key=muts.get) if muts else None

                if acc and isinstance(right, ast.Name) and right.id != acc:
                    new_src = _splice(source, right, acc)
                    if new_src != source:
                        out.append(new_src)

                if itername and isinstance(left, ast.Name) and left.id != loopvar \
                   and left.id == itername:
                    new_src = _splice(source, left, loopvar)
                    if new_src != source:
                        out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 6: `x != acc` used instead of `x not in acc`.
# --------------------------------------------------------------------------

def fix_noteq_to_notin(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        acc = _find_empty_list_accumulator(func)
        if not acc:
            continue
        for n in ast.walk(func):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.NotEq):
                right = n.comparators[0]
                if isinstance(right, ast.Name) and right.id == acc:
                    left_text = _text(source, n.left)
                    new_src = _splice(source, n, f"{left_text} not in {acc}")
                    if new_src != source:
                        out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 7: `obj.append[x]` used instead of `obj.append(x)` (subscript typo).
# --------------------------------------------------------------------------

def fix_subscript_method_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Attribute) \
           and n.value.attr in ('append', 'extend', 'count', 'remove', 'pop'):
            obj_text = _text(source, n.value.value)
            sl = n.slice
            if isinstance(sl, ast.Index):  # py<3.9 compatibility
                sl = sl.value
            arg_text = _text(source, sl)
            new_text = f"{obj_text}.{n.value.attr}({arg_text})"
            new_src = _splice(source, n, new_text)
            if new_src != source:
                out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 8: `x = x.append(y)` / `x += x.append(y)` -- capturing None.
# --------------------------------------------------------------------------

def fix_append_assign_none(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        value = None
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            value = n.value
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            value = n.value
        if value is not None and isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) \
           and value.func.attr in ('append', 'extend'):
            call_text = _text(source, value)
            new_src = _splice(source, n, call_text)
            if new_src != source:
                out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 9: stray `X == Y` statement meant to be assignment `X = Y`.
# --------------------------------------------------------------------------

def fix_eq_should_be_assign(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Compare) \
           and len(n.value.ops) == 1 and isinstance(n.value.ops[0], ast.Eq):
            left_text = _text(source, n.value.left)
            right_text = _text(source, n.value.comparators[0])
            new_src = _splice(source, n, f"{left_text} = {right_text}")
            if new_src != source:
                out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 10: `.extend(single_item)` should be `.append(single_item)`.
# --------------------------------------------------------------------------

def fix_extend_to_append(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'extend' \
           and len(n.args) == 1 and not isinstance(n.args[0], (ast.List, ast.Tuple, ast.Set)):
            obj_text = _text(source, n.func.value)
            arg_text = _text(source, n.args[0])
            new_src = _splice(source, n, f"{obj_text}.append({arg_text})")
            if new_src != source:
                out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 11: `acc += item` (should be `acc += [item]`) inside the dedup idiom.
# --------------------------------------------------------------------------

def fix_augassign_wrap_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for ifn in ast.walk(tree):
        if not isinstance(ifn, ast.If):
            continue
        test = ifn.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.In, ast.NotIn))):
            continue
        names_in_test = set()
        if isinstance(test.left, ast.Name):
            names_in_test.add(test.left.id)
        if isinstance(test.comparators[0], ast.Name):
            names_in_test.add(test.comparators[0].id)
        for n in ast.walk(ifn):
            if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) \
               and isinstance(n.target, ast.Name) and n.target.id in names_in_test \
               and not isinstance(n.value, (ast.List, ast.Tuple)):
                value_text = _text(source, n.value)
                s, e = _span(source, n.value)
                new_src = source[:s] + f"[{value_text}]" + source[e:]
                if new_src != source:
                    out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 12: `obj.pop` used as a statement instead of `obj.pop()`.
# --------------------------------------------------------------------------

def fix_pop_missing_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Attribute) and n.value.attr == 'pop':
            text = _text(source, n.value)
            new_src = _splice(source, n.value, text + "()")
            if new_src != source:
                out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 13: nested `while` index-removal loop increments the index
# unconditionally after a removal, causing skipped elements / infinite loop.
# --------------------------------------------------------------------------

def fix_while_missing_else(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.While):
            continue
        body = n.body
        for i in range(len(body) - 1):
            stmt, nxt = body[i], body[i + 1]
            if isinstance(stmt, ast.If) and not stmt.orelse \
               and isinstance(nxt, ast.AugAssign) and isinstance(nxt.op, ast.Add):
                s_if, e_if = _span(source, stmt)
                s_next, e_next = _span(source, nxt)
                indent = ' ' * stmt.col_offset
                next_text = source[s_next:e_next]
                new_segment = (source[s_if:e_if] + "\n" + indent + "else:\n"
                               + indent + "    " + next_text)
                new_src = source[:s_if] + new_segment + source[e_next:]
                if new_src != source:
                    out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 14: a helper function is called under a mis-typed name.
# --------------------------------------------------------------------------

def fix_function_name_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    funcnames = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    seen = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            if name in funcnames:
                continue
            best, bestd = None, None
            for fname in funcnames:
                d = _levenshtein(name, fname)
                if d <= 2 and (bestd is None or d < bestd):
                    best, bestd = fname, d
            if best and (name, best) not in seen:
                seen.add((name, best))
                new_src = _splice(source, n.func, best)
                if new_src != source:
                    out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rules 15-17: OrderedDict one-liner misconceptions.
# --------------------------------------------------------------------------

def fix_lists_typo(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'lists':
            new_src = _splice(source, n.func, "list")
            if new_src != source:
                out.append(new_src)
    return out


def fix_missing_list_wrap(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Call) \
           and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'fromkeys':
            text = _text(source, n.value)
            new_src = _splice(source, n.value, f"list({text})")
            if new_src != source:
                out.append(new_src)
    return out


def fix_missing_ordereddict_import(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    uses = any(isinstance(n, ast.Name) and n.id == 'OrderedDict' for n in ast.walk(tree))
    if not uses:
        return []
    has_import = any(
        isinstance(n, ast.ImportFrom) and n.module == 'collections'
        and any(a.name == 'OrderedDict' for a in n.names)
        for n in ast.walk(tree)
    )
    if has_import:
        return []
    return ["from collections import OrderedDict\n" + source]


# --------------------------------------------------------------------------
# Rule 18: `return None` should be `return []` on the empty-list guard.
# --------------------------------------------------------------------------

def fix_none_to_empty_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.If):
            continue
        test = n.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
            continue
        right = test.comparators[0]
        if not (isinstance(right, ast.List) and not right.elts):
            continue
        for stmt in ast.walk(n):
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) \
               and stmt.value.value is None:
                new_src = _splice(source, stmt.value, "[]")
                if new_src != source:
                    out.append(new_src)
    return out


# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="list_builtin_shadowing", apply=fix_list_builtin,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="undefined_accumulator_target", apply=fix_undefined_accumulator_target,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="return_wrong_name", apply=fix_return_wrong_name,
                 symptoms=("wrong",)),
            Rule(name="missing_return", apply=fix_missing_return,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="membership_check_wrong_name", apply=fix_membership_checks,
                 symptoms=("wrong",)),
            Rule(name="noteq_should_be_notin", apply=fix_noteq_to_notin,
                 symptoms=("wrong",)),
            Rule(name="subscript_instead_of_call", apply=fix_subscript_method_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="append_assign_captures_none", apply=fix_append_assign_none,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="eq_should_be_assign", apply=fix_eq_should_be_assign,
                 symptoms=("wrong",)),
            Rule(name="extend_should_be_append", apply=fix_extend_to_append,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="augassign_should_wrap_list", apply=fix_augassign_wrap_list,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="pop_missing_call", apply=fix_pop_missing_call,
                 symptoms=("wrong",)),
            Rule(name="while_loop_missing_else_increment", apply=fix_while_missing_else,
                 symptoms=("timeout", "wrong")),
            Rule(name="function_name_typo", apply=fix_function_name_typo,
                 symptoms=("err:NameError",)),
            Rule(name="ordereddict_lists_typo", apply=fix_lists_typo,
                 symptoms=("err:NameError",)),
            Rule(name="ordereddict_missing_list_wrap", apply=fix_missing_list_wrap,
                 symptoms=("wrong",)),
            Rule(name="ordereddict_missing_import", apply=fix_missing_ordereddict_import,
                 symptoms=("err:NameError",)),
            Rule(name="none_should_be_empty_list", apply=fix_none_to_empty_list,
                 symptoms=("wrong", "err:TypeError")),
        ]