"""
Repair module for the "Sort Tuples by Age" assignment.

Each Rule below targets one recurring misconception observed across the
class's buggy submissions. Every `apply` function parses the submission
with `ast`, locates a structural pattern, and splices a minimal textual
replacement into the ORIGINAL source (never rebuilding the whole program).
"""

import ast
import builtins
import re

from src.core.repair import Rule


# ----------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------

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


def _multi_splice(source, spans, texts_or_text):
    """Apply several (start, end) replacements in one pass, right-to-left."""
    if isinstance(texts_or_text, str):
        items = [(s, e, texts_or_text) for (s, e) in spans]
    else:
        items = [(s, e, t) for (s, e), t in zip(spans, texts_or_text)]
    for s, e, t in sorted(items, key=lambda x: -x[0]):
        source = source[:s] + t + source[e:]
    return source


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _enclosing_function(node):
    cur = getattr(node, 'parent', None)
    while cur is not None and not isinstance(cur, ast.FunctionDef):
        cur = getattr(cur, 'parent', None)
    return cur


def _top_level_ancestor(func, node):
    cur = node
    guard = 0
    while getattr(cur, 'parent', None) is not None and cur.parent is not func and guard < 10000:
        cur = cur.parent
        guard += 1
    return cur


def _defined_names(tree, func):
    names = set(dir(builtins))
    names.update(['True', 'False', 'None', 'self'])
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    args = func.args
    for a in list(args.args) + list(getattr(args, 'posonlyargs', [])) + list(args.kwonlyargs):
        names.add(a.arg)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        if isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source) or []
        except Exception:
            return []
    return wrapped


# ----------------------------------------------------------------------
# Rule: bare identifier `list` used instead of the list parameter
# ----------------------------------------------------------------------

def _list_to_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef) or not func.args.args:
            continue
        param = func.args.args[0].arg
        if param == 'list':
            continue
        spans = []
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and node.id == 'list' and isinstance(node.ctx, ast.Load):
                parent = getattr(node, 'parent', None)
                spans.append(_span(source, node))
        if spans:
            out.append(_multi_splice(source, spans, param))
    return out


# ----------------------------------------------------------------------
# Rule: undefined name used where the list parameter belongs
# (as a for-loop iterable, X[0]/X[1] subscript, or X.remove(...) target)
# ----------------------------------------------------------------------

def _undefined_to_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef) or not func.args.args:
            continue
        param = func.args.args[0].arg
        defined = _defined_names(tree, func)
        by_name = {}
        for node in ast.walk(func):
            name = None
            target = None
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id not in defined:
                name, target = node.iter.id, node.iter
            elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id not in defined:
                sl = node.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
                    name, target = node.value.id, node.value
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == 'remove' and isinstance(node.func.value, ast.Name)
                  and node.func.value.id not in defined):
                name, target = node.func.value.id, node.func.value
            if name and name != param:
                by_name.setdefault(name, []).append(_span(source, target))
        for name, spans in by_name.items():
            out.append(_multi_splice(source, list(set(spans)), param))
    return out


# ----------------------------------------------------------------------
# Rule: result container used under an undefined name while it was
# initialised under a different name (append/return mismatch)
# ----------------------------------------------------------------------

def _container_unify(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = _defined_names(tree, func)
        container = None
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.List) and len(node.value.elts) == 0):
                container = node.targets[0].id
                break
        if container is None:
            continue
        spans = []
        for node in ast.walk(func):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)
                    and node.func.value.id != container and node.func.value.id not in defined):
                spans.append(_span(source, node.func.value))
            elif (isinstance(node, ast.Return) and isinstance(node.value, ast.Name)
                    and node.value.id != container and node.value.id not in defined):
                spans.append(_span(source, node.value))
        if spans:
            out.append(_multi_splice(source, list(set(spans)), container))
    return out


# ----------------------------------------------------------------------
# Rule: append target used entirely undefined (no init anywhere) ->
# insert `name = []` right before the enclosing loop
# ----------------------------------------------------------------------

def _insert_missing_container_init(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = _defined_names(tree, func)
        seen = set()
        for node in ast.walk(func):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)):
                x = node.func.value.id
                if x in defined or x in seen:
                    continue
                seen.add(x)
                top = _top_level_ancestor(func, node)
                if top not in func.body:
                    continue
                s, e = _span(source, top)
                line_start = source.rfind('\n', 0, s) + 1
                indent = source[line_start:s]
                insertion = f"{indent}{x} = []\n"
                out.append(source[:line_start] + insertion + source[line_start:])
    return out


# ----------------------------------------------------------------------
# Rule: `X = UNDEFINED` inside a for-loop's if-body where UNDEFINED
# should have been the loop target
# ----------------------------------------------------------------------

def _assign_undefined_loop_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = _defined_names(tree, func)
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Name) and node.value.id not in defined):
                cur = getattr(node, 'parent', None)
                forloop = None
                while cur is not None and cur is not func:
                    if isinstance(cur, ast.For) and isinstance(cur.target, ast.Name):
                        forloop = cur
                        break
                    cur = getattr(cur, 'parent', None)
                if forloop is None:
                    continue
                t = forloop.target.id
                if t == node.value.id:
                    continue
                out.append(_splice(source, node.value, t))
    return out


# ----------------------------------------------------------------------
# Rule: comparison references an undefined variable that should be the
# tracked "best so far" variable (e.g. `element[1] > smallest[1]` where
# `smallest` is undefined but `biggest` is the tracked one)
# ----------------------------------------------------------------------

def _compare_var_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = _defined_names(tree, func)
        for node in ast.walk(func):
            if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
                continue
            for sub in node.body:
                if not (isinstance(sub, ast.If) and isinstance(sub.test, ast.Compare) and len(sub.test.ops) == 1):
                    continue
                left, right = sub.test.left, sub.test.comparators[0]

                def base(n):
                    if isinstance(n, ast.Name):
                        return n
                    if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
                        return n.value
                    return None

                lb, rb = base(left), base(right)
                if lb is None or rb is None:
                    continue
                track = None
                for st in sub.body:
                    if (isinstance(st, ast.Assign) and len(st.targets) == 1
                            and isinstance(st.targets[0], ast.Name)
                            and isinstance(st.value, ast.Name) and st.value.id == node.target.id):
                        track = st.targets[0].id
                        break
                if track is None:
                    continue
                if lb.id == track and rb.id != track and rb.id not in defined:
                    out.append(_splice(source, rb, track))
                elif rb.id == track and lb.id != track and lb.id not in defined:
                    out.append(_splice(source, lb, track))
    return out


# ----------------------------------------------------------------------
# Rule: undefined name used in the statements following the inner
# for-loop (typically `lst.remove(X)` / `result.append(X)`) that should
# reference the variable tracked by `TRACK = lst[0]` at loop start
# ----------------------------------------------------------------------

def _track_var_trailing(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = _defined_names(tree, func)
        for node in ast.walk(func):
            if not isinstance(node, ast.While):
                continue
            body = node.body
            if not body:
                continue
            first = body[0]
            track = None
            if (isinstance(first, ast.Assign) and len(first.targets) == 1
                    and isinstance(first.targets[0], ast.Name)
                    and isinstance(first.value, ast.Subscript)):
                track = first.targets[0].id
            if track is None:
                continue
            spans = []
            for stmt in body[1:]:
                for sub in ast.walk(stmt):
                    if (isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load)
                            and sub.id not in defined and sub.id != track):
                        spans.append(_span(source, sub))
            if spans:
                out.append(_multi_splice(source, list(set(spans)), track))
    return out


# ----------------------------------------------------------------------
# Rule: `X == ()` should be `X == []` (empty-list check written as tuple)
# ----------------------------------------------------------------------

def _empty_tuple_to_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            for side in (node.left, node.comparators[0]):
                if isinstance(side, ast.Tuple) and len(side.elts) == 0:
                    out.append(_splice(source, side, "[]"))
    return out


# ----------------------------------------------------------------------
# Rule: flip all min()<->max() calls (descending vs ascending mixup)
# ----------------------------------------------------------------------

def _flip_min_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    spans_min, spans_max = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == 'min':
                spans_min.append(_span(source, node.func))
            elif node.func.id == 'max':
                spans_max.append(_span(source, node.func))
    out = []
    if spans_min:
        out.append(_multi_splice(source, spans_min, 'max'))
    if spans_max:
        out.append(_multi_splice(source, spans_max, 'min'))
    return out


# ----------------------------------------------------------------------
# Rule: recursive merge-sort slices the parameter directly instead of
# recursing on it (`lst1 = lst[:mid]` should be `lst1 = sort_age(lst[:mid])`)
# ----------------------------------------------------------------------

def _wrap_unrecursed_slice(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef) or not func.args.args:
            continue
        is_recursive = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == func.name
            for n in ast.walk(func) if n is not func
        )
        if not is_recursive:
            continue
        param = func.args.args[0].arg
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Subscript):
                sub = node.value
                if (isinstance(sub.value, ast.Name) and sub.value.id == param
                        and isinstance(sub.slice, ast.Slice)):
                    s, e = _span(source, sub)
                    text = source[s:e]
                    out.append(source[:s] + f"{func.name}({text})" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: function ends without a `return` (missing/misplaced return)
# ----------------------------------------------------------------------

def _ensure_final_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        body = func.body
        last = body[-1]
        if isinstance(last, ast.Return):
            continue
        container = None
        for stmt in body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.List) and len(stmt.value.elts) == 0):
                container = stmt.targets[0].id
                break
        if container is None:
            continue
        indent = ' ' * body[0].col_offset
        if isinstance(last, (ast.Pass, ast.Expr)):
            ls, le = _span(source, last)
            out.append(source[:ls] + f"return {container}" + source[le:])
        else:
            ls, le = _span(source, last)
            out.append(source[:le] + f"\n{indent}return {container}" + source[le:])
    return out


# ----------------------------------------------------------------------
# Rule: last statement inside a `while` is a `return`/`.reverse` call
# that must run only after the loop finishes -> dedent it
# ----------------------------------------------------------------------

def _dedent_trailing_loop_stmt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.While) and len(node.body) >= 2):
            continue
        last = node.body[-1]
        new_stmt_text = None
        if isinstance(last, ast.Return):
            ls, le = _span(source, last)
            new_stmt_text = source[ls:le]
        elif (isinstance(last, ast.Expr) and isinstance(last.value, ast.Attribute)
                and last.value.attr == 'reverse' and isinstance(last.value.value, ast.Name)):
            ls, le = _span(source, last)
            new_stmt_text = f"{last.value.value.id}.reverse()"
        elif (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
                and isinstance(last.value.func, ast.Attribute) and last.value.func.attr == 'reverse'
                and isinstance(last.value.func.value, ast.Name)):
            ls, le = _span(source, last)
            new_stmt_text = source[ls:le]
        else:
            continue
        ws, we = _span(source, node)
        line_start = source.rfind('\n', 0, ls) + 1
        w_line_start = source.rfind('\n', 0, ws) + 1
        w_indent = source[w_line_start:ws]
        new_source = source[:line_start] + source[le:]
        removed_len = le - line_start
        we_adj = we - removed_len
        insertion = "\n" + w_indent + new_stmt_text
        new_source = new_source[:we_adj] + insertion + new_source[we_adj:]
        out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule: `return X.reverse` / `return X.reverse()` returns None instead
# of the reversed list
# ----------------------------------------------------------------------

def _fix_bare_reverse_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Return) and node.value is not None):
            continue
        val = node.value
        name = None
        if isinstance(val, ast.Attribute) and val.attr == 'reverse' and isinstance(val.value, ast.Name):
            name = val.value.id
        elif (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                and val.func.attr == 'reverse' and isinstance(val.func.value, ast.Name) and not val.args):
            name = val.func.value.id
        if name is None:
            continue
        s, e = _span(source, node)
        line_start = source.rfind('\n', 0, s) + 1
        indent = source[line_start:s]
        replacement = f"{name}.reverse()\n{indent}return {name}"
        out.append(source[:s] + replacement + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: `helper(lst).reverse` as a bare statement does nothing useful
# ----------------------------------------------------------------------

def _fix_dangling_reverse_call_stmt(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute)
                and node.value.attr == 'reverse' and isinstance(node.value.value, ast.Call)):
            continue
        call = node.value.value
        if not call.args or not isinstance(call.args[0], ast.Name):
            continue
        s, e = _span(source, node)
        call_s, call_e = _span(source, call)
        call_src = source[call_s:call_e]
        line_start = source.rfind('\n', 0, s) + 1
        indent = source[line_start:s]
        replacement = f"{call_src}\n{indent}{call.args[0].id}.reverse()"
        out.append(source[:s] + replacement + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: `X.pop[i]` should be `X.pop(i)`
# ----------------------------------------------------------------------

def _fix_pop_subscript_to_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr == 'pop'):
            continue
        sl = node.slice
        s_s, s_e = _span(source, sl)
        slice_src = source[s_s:s_e]
        v_s, v_e = _span(source, node.value)
        val_src = source[v_s:v_e]
        whole_s, whole_e = _span(source, node)
        replacement = f"{val_src}({slice_src})"
        out.append(source[:whole_s] + replacement + source[whole_e:])
    return out


# ----------------------------------------------------------------------
# Rule: `X = X.append(y)` reassigns the None returned by list.append
# ----------------------------------------------------------------------

def _fix_self_append_reassign(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        x = node.targets[0].id
        val = node.value
        if not (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                and val.func.attr == 'append' and isinstance(val.func.value, ast.Name)
                and val.func.value.id == x and len(val.args) == 1):
            continue
        arg_s, arg_e = _span(source, val.args[0])
        arg_src = source[arg_s:arg_e]
        s, e = _span(source, node)
        replacement = f"{x}.append({arg_src})"
        out.append(source[:s] + replacement + source[e:])
    return out


# ----------------------------------------------------------------------
# Fallback: flip a strict/relational comparison operator on ages
# ----------------------------------------------------------------------

def _flip_age_comparison(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    swap = {ast.Lt: '>', ast.Gt: '<', ast.LtE: '>=', ast.GtE: '<='}
    pattern = re.compile(r'<=|>=|<|>')
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in swap:
            left = node.left
            right = node.comparators[0]
            try:
                _, le = _span(source, left)
                rs, _ = _span(source, right)
            except Exception:
                continue
            if rs < le:
                continue
            between = source[le:rs]
            m = pattern.search(between)
            if not m:
                continue
            new_between = between[:m.start()] + swap[type(node.ops[0])] + between[m.end():]
            out.append(source[:le] + new_between + source[rs:])
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="list_to_param", apply=_safe(_list_to_param),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_to_param", apply=_safe(_undefined_to_param),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="container_unify", apply=_safe(_container_unify),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="insert_missing_container_init", apply=_safe(_insert_missing_container_init),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="assign_undefined_loop_target", apply=_safe(_assign_undefined_loop_target),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="compare_var_mismatch", apply=_safe(_compare_var_mismatch),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="track_var_trailing", apply=_safe(_track_var_trailing),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="empty_tuple_to_list", apply=_safe(_empty_tuple_to_list),
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="flip_min_max", apply=_safe(_flip_min_max),
                 symptoms=("wrong",)),
            Rule(name="wrap_unrecursed_slice", apply=_safe(_wrap_unrecursed_slice),
                 symptoms=("wrong",)),
            Rule(name="ensure_final_return", apply=_safe(_ensure_final_return),
                 symptoms=("wrong", "err:NameError")),
            Rule(name="dedent_trailing_loop_stmt", apply=_safe(_dedent_trailing_loop_stmt),
                 symptoms=("wrong",)),
            Rule(name="fix_bare_reverse_return", apply=_safe(_fix_bare_reverse_return),
                 symptoms=("wrong",)),
            Rule(name="fix_dangling_reverse_call_stmt", apply=_safe(_fix_dangling_reverse_call_stmt),
                 symptoms=("wrong",)),
            Rule(name="fix_pop_subscript_to_call", apply=_safe(_fix_pop_subscript_to_call),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_self_append_reassign", apply=_safe(_fix_self_append_reassign),
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="flip_age_comparison", apply=_safe(_flip_age_comparison),
                 symptoms=("wrong",)),
        ]