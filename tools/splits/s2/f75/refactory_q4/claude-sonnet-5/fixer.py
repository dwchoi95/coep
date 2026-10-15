"""
Repair module for the "Sorting Tuples" (sort_age) assignment.

Each rule performs one small, local, AST-located edit addressing a specific
observed misconception. Rules are meant to be composed by the search harness
across multiple passes (e.g. "initialize missing accumulator" then "add
missing return").
"""

import ast

from src.core.repair import Rule


# ----------------------------------------------------------------------
# generic helpers
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


def _parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _collect_defined_names(fn):
    defined = set()
    args = fn.args
    for a in list(args.args) + list(getattr(args, "posonlyargs", [])) + list(args.kwonlyargs):
        defined.add(a.arg)
    if args.vararg:
        defined.add(args.vararg.arg)
    if args.kwarg:
        defined.add(args.kwarg.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined.add(node.id)
        if isinstance(node, ast.FunctionDef):
            defined.add(node.name)
        if isinstance(node, ast.arg):
            defined.add(node.arg)
    return defined


def _is_empty_list_assign(node):
    return (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.List) and len(node.value.elts) == 0)


def _dedent_last_stmt(source, loop_node, stmt_node):
    rs, re_ = _span(source, stmt_node)
    stmt_text = source[rs:re_]
    line_start = source.rfind('\n', 0, rs) + 1
    line_end = source.find('\n', re_)
    if line_end == -1:
        line_end = len(source)
    else:
        line_end += 1
    without = source[:line_start] + source[line_end:]
    loop_start = _span(source, loop_node)[0]
    loop_line_start = source.rfind('\n', 0, loop_start) + 1
    indent = source[loop_line_start:loop_start]
    insertion_point = line_start
    return without[:insertion_point] + indent + stmt_text + "\n" + without[insertion_point:]


# ----------------------------------------------------------------------
# Rule 1: undefined name used as the receiver of .remove(...) -> parameter
# ----------------------------------------------------------------------

def fix_undefined_remove_target(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        fn = _find_function(tree, "sort_age")
        if fn is None or not fn.args.args:
            return []
        param = fn.args.args[0].arg
        defined = _collect_defined_names(fn)
        bad = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "remove" and isinstance(node.func.value, ast.Name)):
                name = node.func.value.id
                if name not in defined and name != param:
                    bad.add(name)
        if not bad:
            return []
        nodes = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Name) and n.id in bad and isinstance(n.ctx, ast.Load)]
        if not nodes:
            return []
        nodes.sort(key=lambda n: _span(source, n)[0], reverse=True)
        new_source = source
        for n in nodes:
            new_source = _splice(new_source, n, param)
        return [new_source] if new_source != source else []
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 2: undefined name used as .append(...) receiver / bare return value
# -> rename to the actual accumulator list variable
# ----------------------------------------------------------------------

def fix_undefined_append_or_return_target(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        fn = _find_function(tree, "sort_age")
        if fn is None:
            return []
        defined = _collect_defined_names(fn)
        acc = None
        for node in ast.walk(fn):
            if _is_empty_list_assign(node):
                acc = node.targets[0].id
                break
        if acc is None:
            return []
        bad = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "append" and isinstance(node.func.value, ast.Name)):
                name = node.func.value.id
                if name not in defined and name != acc:
                    bad.add(name)
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                name = node.value.id
                if name not in defined and name != acc:
                    bad.add(name)
        if not bad:
            return []
        nodes = [n for n in ast.walk(fn)
                 if isinstance(n, ast.Name) and n.id in bad and isinstance(n.ctx, ast.Load)]
        if not nodes:
            return []
        nodes.sort(key=lambda n: _span(source, n)[0], reverse=True)
        new_source = source
        for n in nodes:
            new_source = _splice(new_source, n, acc)
        return [new_source] if new_source != source else []
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 2b: undefined accumulator never initialized anywhere -> insert "name = []"
# ----------------------------------------------------------------------

def fix_uninitialized_accumulator(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        fn = _find_function(tree, "sort_age")
        if fn is None or not fn.body:
            return []
        for node in ast.walk(fn):
            if _is_empty_list_assign(node):
                return []
        defined = _collect_defined_names(fn)
        bad = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "append" and isinstance(node.func.value, ast.Name)):
                name = node.func.value.id
                if name not in defined:
                    bad.add(name)
        if len(bad) != 1:
            return []
        name = next(iter(bad))
        first_stmt = fn.body[0]
        indent = " " * first_stmt.col_offset
        s, _e = _span(source, first_stmt)
        insertion = f"{indent}{name} = []\n"
        return [source[:s] + insertion + source[s:]]
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 3: function never returns -> append "return ACC" at the end
# ----------------------------------------------------------------------

def fix_missing_return(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        fn = _find_function(tree, "sort_age")
        if fn is None or not fn.body:
            return []
        for node in ast.walk(fn):
            if isinstance(node, ast.Return):
                return []
        acc = None
        for node in ast.walk(fn):
            if _is_empty_list_assign(node):
                acc = node.targets[0].id
                break
        if acc is None:
            return []
        indent = " " * fn.body[0].col_offset
        last_stmt = fn.body[-1]
        _s, e = _span(source, last_stmt)
        insertion = f"\n{indent}return {acc}"
        return [source[:e] + insertion + source[e:]]
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 4: a `return` statement sits as the LAST statement inside a loop body
# (causes premature return / wrong result) -> dedent it to after the loop
# ----------------------------------------------------------------------

def dedent_trailing_return_in_loop(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.While, ast.For)) and node.body and isinstance(node.body[-1], ast.Return):
                out.append(_dedent_last_stmt(source, node, node.body[-1]))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 5: a bare `X.reverse()` call is the LAST statement inside a loop body
# (reverses every iteration instead of once) -> dedent to after the loop
# ----------------------------------------------------------------------

def dedent_trailing_reverse_in_loop(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.While, ast.For)) and node.body:
                last = node.body[-1]
                if (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
                        and isinstance(last.value.func, ast.Attribute)
                        and last.value.func.attr == "reverse" and not last.value.args):
                    out.append(_dedent_last_stmt(source, node, last))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 6: tracking-variable update swapped: `loopvar = acc` instead of
# `acc = loopvar` inside an `if` whose test compares loopvar vs acc
# ----------------------------------------------------------------------

def fix_swapped_tracking_assign(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loopvar = node.target.id
                for sub in ast.walk(node):
                    if isinstance(sub, ast.If):
                        test_names = {n.id for n in ast.walk(sub.test) if isinstance(n, ast.Name)}
                        if loopvar not in test_names:
                            continue
                        for stmt in sub.body:
                            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                                    and isinstance(stmt.targets[0], ast.Name)
                                    and stmt.targets[0].id == loopvar
                                    and isinstance(stmt.value, ast.Name)):
                                acc = stmt.value.id
                                if acc in test_names and acc != loopvar:
                                    new_text = f"{acc} = {loopvar}"
                                    out.append(_splice(source, stmt, new_text))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 7: `return X.reverse()` (or `return list.reverse(X)`) returns None
# ----------------------------------------------------------------------

def fix_return_reverse_call(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                call = node.value
                if not isinstance(call.func, ast.Attribute) or call.func.attr != "reverse":
                    continue
                indent = " " * node.col_offset
                if isinstance(call.func.value, ast.Name) and not call.args:
                    name = call.func.value.id
                    new_text = f"{name}.reverse()\n{indent}return {name}"
                    out.append(_splice(source, node, new_text))
                elif (isinstance(call.func.value, ast.Name) and call.func.value.id == "list"
                      and len(call.args) == 1 and isinstance(call.args[0], ast.Name)):
                    name = call.args[0].id
                    new_text = f"{name}.reverse()\n{indent}return {name}"
                    out.append(_splice(source, node, new_text))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 8: max(lst) / min(lst) used without a key on a list of tuples
# ----------------------------------------------------------------------

def add_key_to_max_min_call(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("max", "min") and len(node.args) == 1
                    and not node.keywords):
                arg_s, arg_e = _span(source, node.args[0])
                arg_text = source[arg_s:arg_e]
                new_text = f"{node.func.id}({arg_text}, key=lambda p: p[1])"
                out.append(_splice(source, node, new_text))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 9: plain `.sort()` with no key on a list of tuples
# ----------------------------------------------------------------------

def add_key_to_sort_call(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "sort" and not node.args and not node.keywords):
                recv_s, recv_e = _span(source, node.func.value)
                recv_text = source[recv_s:recv_e]
                out.append(_splice(source, node, f"{recv_text}.sort(key=lambda p: p[1])"))
                out.append(_splice(source, node, f"{recv_text}.sort(key=lambda p: p[1], reverse=True)"))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 10: recursive base case `len(x) == 1` misses the empty-list case
# ----------------------------------------------------------------------

def fix_len_eq_one_base_case(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left = node.left
                comp = node.comparators[0]
                if (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                        and left.func.id == "len" and isinstance(comp, ast.Constant) and comp.value == 1):
                    ls, le = _span(source, left)
                    left_text = source[ls:le]
                    out.append(_splice(source, node, f"{left_text} <= 1"))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 11: comparing against an empty tuple `()` when input is a list
# ----------------------------------------------------------------------

def fix_empty_tuple_compare(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                sides = [node.left] + list(node.comparators)
                for s in sides:
                    if isinstance(s, ast.Tuple) and len(s.elts) == 0:
                        out.append(_splice(source, s, "[]"))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 12: `X.pop[i]` / `X.remove[i]` (subscript instead of call)
# ----------------------------------------------------------------------

def fix_bracket_instead_of_call(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                    and node.value.attr in ("pop", "remove")):
                val_s, val_e = _span(source, node.value)
                val_text = source[val_s:val_e]
                sl = node.slice
                if isinstance(sl, ast.Index):
                    sl = sl.value
                sl_s, sl_e = _span(source, sl)
                sl_text = source[sl_s:sl_e]
                out.append(_splice(source, node, f"{val_text}({sl_text})"))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 13: `acc += a_tuple_name` instead of `acc += (a_tuple_name,)`
# ----------------------------------------------------------------------

def fix_augassign_tuple_wrap(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        fn = _find_function(tree, "sort_age")
        if fn is None:
            return []
        list_accs = set()
        for node in ast.walk(fn):
            if _is_empty_list_assign(node):
                list_accs.add(node.targets[0].id)
        out = []
        for node in ast.walk(fn):
            if (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                    and isinstance(node.target, ast.Name) and node.target.id in list_accs
                    and isinstance(node.value, ast.Name)):
                vs, ve = _span(source, node.value)
                vtext = source[vs:ve]
                out.append(_splice(source, node.value, f"({vtext},)"))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 14: generic flip of a strict/non-strict comparison operator when it
# directly compares people's ages (subscript `[1]`)
# ----------------------------------------------------------------------

_OP_FLIP = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}
_OP_TEXT = {ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=", ast.GtE: ">="}


def _is_age_subscript(node):
    if not isinstance(node, ast.Subscript):
        return False
    sl = node.slice
    if isinstance(sl, ast.Index):
        sl = sl.value
    return isinstance(sl, ast.Constant) and sl.value == 1


def flip_age_comparison_operator(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _OP_FLIP:
                sides = [node.left] + list(node.comparators)
                if not any(_is_age_subscript(s) for s in sides):
                    continue
                left = node.left
                right = node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_op = _OP_TEXT[_OP_FLIP[type(node.ops[0])]]
                new_text = source[ls:le] + f" {new_op} " + source[rs:re_]
                out.append(_splice(source, node, new_text))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 15: swapped function call `thing(builtin_name)` instead of
# `builtin_name(thing)`, e.g. `first = test(max)`
# ----------------------------------------------------------------------

_SWAPPABLE_BUILTINS = {"max", "min", "sum", "len", "sorted"}


def fix_swapped_call_target_and_arg(source):
    try:
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id not in _SWAPPABLE_BUILTINS
                    and len(node.args) == 1 and not node.keywords
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in _SWAPPABLE_BUILTINS):
                fname = node.func.id
                argname = node.args[0].id
                out.append(_splice(source, node, f"{argname}({fname})"))
        return out
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 16: `print(...)` where the function should `return` a value, and no
# return exists anywhere -> add return of the accumulator after it.
# (handled generically by fix_missing_return; kept separate trivial guard
#  not needed since fix_missing_return already covers any trailing stmt)
# ----------------------------------------------------------------------


class Fixer:
    def rules(self):
        return [
            Rule(
                name="undefined_remove_target_to_param",
                apply=fix_undefined_remove_target,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="undefined_append_return_target_to_accumulator",
                apply=fix_undefined_append_or_return_target,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="initialize_uninitialized_accumulator",
                apply=fix_uninitialized_accumulator,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="append_missing_return",
                apply=fix_missing_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="dedent_trailing_return_in_loop",
                apply=dedent_trailing_return_in_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="dedent_trailing_reverse_in_loop",
                apply=dedent_trailing_reverse_in_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_swapped_tracking_assign",
                apply=fix_swapped_tracking_assign,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_return_reverse_call_returns_none",
                apply=fix_return_reverse_call,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="add_key_to_max_min_call",
                apply=add_key_to_max_min_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_key_to_sort_call",
                apply=add_key_to_sort_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_len_eq_one_base_case",
                apply=fix_len_eq_one_base_case,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="fix_empty_tuple_compare",
                apply=fix_empty_tuple_compare,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="fix_bracket_instead_of_call",
                apply=fix_bracket_instead_of_call,
                symptoms=("err:TypeError",),
            ),
            Rule(
                name="fix_augassign_tuple_wrap",
                apply=fix_augassign_tuple_wrap,
                symptoms=("wrong",),
            ),
            Rule(
                name="flip_age_comparison_operator",
                apply=flip_age_comparison_operator,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_swapped_call_target_and_arg",
                apply=fix_swapped_call_target_and_arg,
                symptoms=("err:TypeError", "wrong"),
            ),
        ]