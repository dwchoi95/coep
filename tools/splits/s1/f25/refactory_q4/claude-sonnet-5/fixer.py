"""
Repair rules for the "Sorting Tuples" (sort_age) assignment.

Each rule performs a small, local, AST-located source-span splice that
targets one recurring misconception observed in buggy submissions.
"""

import ast
import builtins
import difflib

from src.core.repair import Rule

_BUILTIN_NAMES = set(dir(builtins))


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


def _slice_expr(sl):
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _assigned_names(func):
    names = {a.arg for a in func.args.args}
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    names.add(func.name)
    return names


def _find_acc_var(func):
    """First variable initialised to an empty list in the function body."""
    for stmt in func.body:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.List)
                and len(stmt.value.elts) == 0):
            return stmt.targets[0].id
    return None


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapped


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


# ----------------------------------------------------------------------
# Rule 1: `for x in UNDEFINED:` -> replace iterable with the lone parameter
# ----------------------------------------------------------------------

@_safe
def _r_undefined_for_iter(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        params = [a.arg for a in func.args.args]
        if len(params) != 1:
            continue
        param = params[0]
        defined = _assigned_names(func)
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                name = node.iter.id
                if name not in defined and name not in _BUILTIN_NAMES:
                    new_src = _splice(source, node.iter, param)
                    if new_src != source:
                        out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 2: `best = UNDEFINED` inside a for-loop -> replace rhs with loop var
# ----------------------------------------------------------------------

@_safe
def _r_assign_undefined_to_loopvar(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        defined = _assigned_names(func)
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loopvar = node.target.id
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                            and isinstance(sub.targets[0], ast.Name)
                            and isinstance(sub.value, ast.Name)):
                        val = sub.value.id
                        if val not in defined and val != loopvar:
                            new_src = _splice(source, sub.value, loopvar)
                            if new_src != source:
                                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 3: a stray `name - name` expression statement meant to be assignment
# ----------------------------------------------------------------------

@_safe
def _r_binop_stmt_to_assign(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        defined = _assigned_names(func)
        for node in ast.walk(func):
            if (isinstance(node, ast.Expr) and isinstance(node.value, ast.BinOp)
                    and isinstance(node.value.op, ast.Sub)
                    and isinstance(node.value.left, ast.Name)
                    and isinstance(node.value.right, ast.Name)):
                left = node.value.left.id
                right = node.value.right.id
                if left not in defined:
                    matches = difflib.get_close_matches(left, list(defined), n=1)
                    if matches:
                        left = matches[0]
                new_stmt = f"{left} = {right}"
                new_src = _splice(source, node, new_stmt)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 4: undefined name used in the selection `if` comparison -> running best
# ----------------------------------------------------------------------

@_safe
def _r_undefined_name_in_compare(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        defined = _assigned_names(func)
        for wnode in ast.walk(func):
            if not isinstance(wnode, ast.While):
                continue
            best_var = None
            for stmt in wnode.body:
                if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and isinstance(stmt.value, ast.Subscript)):
                    best_var = stmt.targets[0].id
                    break
            if not best_var:
                continue
            for fornode in ast.walk(wnode):
                if not isinstance(fornode, ast.For):
                    continue
                loopvar = (fornode.target.id
                           if isinstance(fornode.target, ast.Name) else None)
                for ifnode in ast.walk(fornode):
                    if isinstance(ifnode, ast.If) and isinstance(ifnode.test, ast.Compare):
                        for namenode in ast.walk(ifnode.test):
                            if (isinstance(namenode, ast.Name)
                                    and isinstance(namenode.ctx, ast.Load)
                                    and namenode.id not in defined
                                    and namenode.id != loopvar
                                    and namenode.id != best_var
                                    and namenode.id not in _BUILTIN_NAMES):
                                new_src = _splice(source, namenode, best_var)
                                if new_src != source:
                                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 5: `UNDEFINED.append(x)` -> replace receiver with the accumulator list
# ----------------------------------------------------------------------

@_safe
def _r_undefined_append_receiver(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        defined = _assigned_names(func)
        acc_var = _find_acc_var(func)
        if not acc_var:
            continue
        for call in ast.walk(func):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr == 'append'):
                recv = call.func.value
                if isinstance(recv, ast.Name) and recv.id not in defined:
                    new_src = _splice(source, recv, acc_var)
                    if new_src != source:
                        out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 6: `return UNDEFINED` -> return the accumulator (or closest match)
# ----------------------------------------------------------------------

@_safe
def _r_fix_undefined_return_name(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        defined = _assigned_names(func)
        acc_var = _find_acc_var(func)
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id not in defined:
                    candidate = acc_var
                    if not candidate:
                        matches = difflib.get_close_matches(
                            node.value.id, list(defined), n=1)
                        candidate = matches[0] if matches else None
                    if candidate:
                        new_src = _splice(source, node.value, candidate)
                        if new_src != source:
                            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 7: function never returns -> add `return ACC` at the end
# ----------------------------------------------------------------------

@_safe
def _r_insert_missing_return(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(func))
        if has_return:
            continue
        acc_var = _find_acc_var(func)
        if not acc_var:
            continue
        last_stmt = func.body[-1]
        indent = ' ' * last_stmt.col_offset
        _, e = _span(source, last_stmt)
        insertion = f"\n{indent}return {acc_var}"
        new_src = source[:e] + insertion + source[e:]
        if new_src != source:
            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 8: last statement is `print(x)` -> should be `return x`
# ----------------------------------------------------------------------

@_safe
def _r_print_to_return(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        if not func.body:
            continue
        last = func.body[-1]
        if (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
                and isinstance(last.value.func, ast.Name)
                and last.value.func.id == 'print'
                and len(last.value.args) == 1):
            a_s, a_e = _span(source, last.value.args[0])
            arg_text = source[a_s:a_e]
            new_src = _splice(source, last, f"return {arg_text}")
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 9: a stray debug `print(...)` statement elsewhere -> remove it
# ----------------------------------------------------------------------

@_safe
def _r_remove_debug_print(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == 'print'):
            s, e = _span(source, node)
            end = e
            if end < len(source) and source[end] == '\n':
                end += 1
            line_start = source.rfind('\n', 0, s) + 1
            new_src = source[:line_start] + source[end:]
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 10: flip a strict comparison direction on an age-subscript compare
# ----------------------------------------------------------------------

_FLIP = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}
_OPTXT = {ast.Lt: '<', ast.Gt: '>', ast.LtE: '<=', ast.GtE: '>='}


@_safe
def _r_flip_compare(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _FLIP:
            left, right = node.left, node.comparators[0]
            if not (isinstance(left, ast.Subscript) or isinstance(right, ast.Subscript)):
                continue
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            opname = _OPTXT[_FLIP[type(node.ops[0])]]
            new_cmp = source[ls:le] + f" {opname} " + source[rs:re_]
            new_src = _splice(source, node, new_cmp)
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 11: a duplicate `.append(...)` statement right after a while loop
# ----------------------------------------------------------------------

@_safe
def _r_remove_dup_append_after_while(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        body = func.body
        for i, stmt in enumerate(body[:-1]):
            if not isinstance(stmt, ast.While):
                continue
            nxt = body[i + 1]
            if not (isinstance(nxt, ast.Expr) and isinstance(nxt.value, ast.Call)
                    and isinstance(nxt.value.func, ast.Attribute)
                    and nxt.value.func.attr == 'append'):
                continue
            recv = nxt.value.func.value
            if not isinstance(recv, ast.Name):
                continue
            inside = [n for n in ast.walk(stmt)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == 'append'
                      and isinstance(n.func.value, ast.Name)
                      and n.func.value.id == recv.id]
            if not inside:
                continue
            s, e = _span(source, nxt)
            end = e
            if end < len(source) and source[end] == '\n':
                end += 1
            line_start = source.rfind('\n', 0, s) + 1
            new_src = source[:line_start] + source[end:]
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 12: `obj.method[arg]` typo'd instead of `obj.method(arg)`
# ----------------------------------------------------------------------

_LIST_METHODS = {'pop', 'remove', 'append', 'insert', 'extend'}


@_safe
def _r_subscript_to_call(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr in _LIST_METHODS):
            idx = _slice_expr(node.slice)
            vs, ve = _span(source, node.value)
            iss, ie = _span(source, idx)
            new_text = source[vs:ve] + "(" + source[iss:ie] + ")"
            new_src = _splice(source, node, new_text)
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 13: `acc = acc + [x]` should accumulate in the other order
# ----------------------------------------------------------------------

@_safe
def _r_swap_accum_add(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.BinOp)
                and isinstance(node.value.op, ast.Add)):
            target_name = node.targets[0].id
            left, right = node.value.left, node.value.right
            left_is_t = isinstance(left, ast.Name) and left.id == target_name
            right_is_t = isinstance(right, ast.Name) and right.id == target_name
            if left_is_t != right_is_t:
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_val = source[rs:re_] + " + " + source[ls:le]
                new_src = _splice(source, node.value, new_val)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 14: loop variable reassigned instead of the running-best variable
# ----------------------------------------------------------------------

@_safe
def _r_swap_loopvar_assign(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                        and isinstance(sub.targets[0], ast.Name)
                        and sub.targets[0].id == loopvar
                        and isinstance(sub.value, ast.Name)):
                    other = sub.value.id
                    if other != loopvar:
                        new_stmt = f"{other} = {loopvar}"
                        new_src = _splice(source, sub, new_stmt)
                        if new_src != source:
                            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 15: append/remove calls placed inside the inner for-loop instead of
# after it (they get executed every inner iteration instead of once).
# ----------------------------------------------------------------------

@_safe
def _r_dedent_trailing_calls(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and len(node.body) >= 2:
            first = node.body[0]
            trailing = node.body[1:]
            if not isinstance(first, ast.If):
                continue
            if not all(isinstance(t, ast.Expr) and isinstance(t.value, ast.Call)
                       and isinstance(t.value.func, ast.Attribute)
                       and t.value.func.attr in ('append', 'remove')
                       for t in trailing):
                continue
            texts = []
            for t in trailing:
                ts, te = _span(source, t)
                texts.append(source[ts:te])
            for_indent = ' ' * node.col_offset
            _, fe = _span(source, first)
            _, le = _span(source, trailing[-1])
            node_s, node_e = _span(source, node)
            insertion = "".join(f"\n{for_indent}{t}" for t in texts)
            new_src = source[:fe] + source[le:node_e] + insertion + source[node_e:]
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 16: undefined name as a sole call argument, replace with a matching
# subscript expression pulled from the enclosing `if` condition.
# ----------------------------------------------------------------------

@_safe
def _r_undefined_call_arg(source):
    tree = ast.parse(source)
    out = []
    for func in _funcs(tree):
        defined = _assigned_names(func)
        for ifnode in ast.walk(func):
            if not isinstance(ifnode, ast.If):
                continue
            subscripts = [n for n in ast.walk(ifnode.test) if isinstance(n, ast.Subscript)]
            if not subscripts:
                continue
            rs, re_ = _span(source, subscripts[0])
            repl_text = source[rs:re_]
            for call in ast.walk(ifnode):
                if (isinstance(call, ast.Call) and len(call.args) == 1
                        and isinstance(call.args[0], ast.Name)):
                    argname = call.args[0].id
                    if argname not in defined and argname not in _BUILTIN_NAMES:
                        new_src = _splice(source, call.args[0], repl_text)
                        if new_src != source:
                            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 17: off-by-one `range(a, len(x) +/- 1)` -> `range(a, len(x))`
# ----------------------------------------------------------------------

@_safe
def _r_fix_range_bounds(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'range' and len(node.args) == 2):
            hi = node.args[1]
            if (isinstance(hi, ast.BinOp) and isinstance(hi.op, (ast.Add, ast.Sub))
                    and isinstance(hi.right, ast.Constant) and hi.right.value == 1):
                ls, le = _span(source, hi.left)
                new_hi = source[ls:le]
                new_src = _splice(source, hi, new_hi)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="undefined_for_iterable",
                 apply=_r_undefined_for_iter,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_rhs_in_loop_assign",
                 apply=_r_assign_undefined_to_loopvar,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="stray_binop_should_be_assignment",
                 apply=_r_binop_stmt_to_assign,
                 symptoms=("wrong",)),
            Rule(name="undefined_name_in_comparison",
                 apply=_r_undefined_name_in_compare,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_append_target",
                 apply=_r_undefined_append_receiver,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="return_wrong_variable",
                 apply=_r_fix_undefined_return_name,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="missing_return_statement",
                 apply=_r_insert_missing_return,
                 symptoms=("wrong",)),
            Rule(name="print_instead_of_return",
                 apply=_r_print_to_return,
                 symptoms=("wrong",)),
            Rule(name="stray_debug_print",
                 apply=_r_remove_debug_print,
                 symptoms=("wrong",)),
            Rule(name="comparison_direction_flip",
                 apply=_r_flip_compare,
                 symptoms=("wrong",)),
            Rule(name="duplicate_append_after_loop",
                 apply=_r_remove_dup_append_after_while,
                 symptoms=("wrong",)),
            Rule(name="subscript_instead_of_call",
                 apply=_r_subscript_to_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="accumulator_concat_order",
                 apply=_r_swap_accum_add,
                 symptoms=("wrong",)),
            Rule(name="loopvar_reassigned_instead_of_best",
                 apply=_r_swap_loopvar_assign,
                 symptoms=("wrong",)),
            Rule(name="append_remove_inside_inner_loop",
                 apply=_r_dedent_trailing_calls,
                 symptoms=("wrong",)),
            Rule(name="undefined_call_argument",
                 apply=_r_undefined_call_arg,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="range_off_by_one",
                 apply=_r_fix_range_bounds,
                 symptoms=("err:IndexError", "wrong")),
        ]