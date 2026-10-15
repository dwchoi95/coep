"""
Repair module for the "remove_extras" (duplicate elimination) assignment.

Each rule is a small, local, AST-located source-span splice targeting one
specific misconception observed across the buggy submission corpus.
"""

import ast
import builtins

from src.core.repair import Rule


# ----------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------

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


def _with_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node
    return tree


def _parent(node):
    return getattr(node, "_parent", None)


def _enclosing_function(node):
    p = _parent(node)
    while p is not None and not isinstance(p, ast.FunctionDef):
        p = _parent(p)
    return p


def _enclosing_for(node):
    p = _parent(node)
    while p is not None and not isinstance(p, ast.FunctionDef):
        if isinstance(p, ast.For):
            return p
        p = _parent(p)
    return None


def _find_accumulator(func):
    """Find the list variable that looks like the dedup accumulator."""
    candidates = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.List) and len(val.elts) == 0:
                candidates.append(node.targets[0].id)
    used = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr in ("append", "extend") \
           and isinstance(node.func.value, ast.Name):
            if node.func.value.id in candidates:
                used.append(node.func.value.id)
    used = list(dict.fromkeys(used))
    if len(used) == 1:
        return used[0]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


# ----------------------------------------------------------------------
# Rule 1: iterating over builtin `list` instead of the parameter
# ----------------------------------------------------------------------

def _fix_iterate_over_builtin_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
            func = _enclosing_function(node)
            if not func or not func.args.args:
                continue
            param = func.args.args[0].arg
            if param == "list":
                continue
            out.append(_splice(source, node.iter, param))
    return out


# ----------------------------------------------------------------------
# Rule 2: membership check compares against the source list instead of
# the accumulator (both operand orders)
# ----------------------------------------------------------------------

def _fix_membership_against_source(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], (ast.In, ast.NotIn)):
            func = _enclosing_function(node)
            if not func:
                continue
            enclosing_for = _enclosing_for(node)
            if enclosing_for is None or not isinstance(enclosing_for.iter, ast.Name):
                continue
            iter_name = enclosing_for.iter.id
            loop_var = enclosing_for.target.id if isinstance(enclosing_for.target, ast.Name) else None
            acc = _find_accumulator(func)
            if not acc or acc == iter_name:
                continue
            left, right = node.left, node.comparators[0]
            new_left = None
            new_right = None
            if isinstance(left, ast.Name) and left.id == iter_name and loop_var:
                new_left = loop_var
            if isinstance(right, ast.Name) and right.id == iter_name:
                new_right = acc
            elif isinstance(right, ast.Subscript) and isinstance(right.value, ast.Name) \
                    and right.value.id == iter_name:
                new_right = acc
            if new_left is None and new_right is None:
                continue
            left_text = new_left if new_left else _text(source, left)
            right_text = new_right if new_right else _text(source, right)
            op_text = "not in" if isinstance(node.ops[0], ast.NotIn) else "in"
            out.append(_splice(source, node, f"{left_text} {op_text} {right_text}"))
    return out


# ----------------------------------------------------------------------
# Rule 3: .count() called on the source list instead of the accumulator
# ----------------------------------------------------------------------

def _fix_count_against_source(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "count" and isinstance(node.func.value, ast.Name):
            func = _enclosing_function(node)
            if not func:
                continue
            enclosing_for = _enclosing_for(node)
            if enclosing_for is None or not isinstance(enclosing_for.iter, ast.Name):
                continue
            iter_name = enclosing_for.iter.id
            acc = _find_accumulator(func)
            if not acc or acc == iter_name:
                continue
            if node.func.value.id == iter_name:
                out.append(_splice(source, node.func.value, acc))
    return out


# ----------------------------------------------------------------------
# Rule 4: .append()/.extend() targets the source list instead of the
# accumulator
# ----------------------------------------------------------------------

def _fix_append_target_wrong(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr in ("append", "extend") and isinstance(node.func.value, ast.Name):
            func = _enclosing_function(node)
            if not func:
                continue
            enclosing_for = _enclosing_for(node)
            if enclosing_for is None or not isinstance(enclosing_for.iter, ast.Name):
                continue
            iter_name = enclosing_for.iter.id
            acc = _find_accumulator(func)
            if not acc or acc == iter_name:
                continue
            if node.func.value.id == iter_name:
                out.append(_splice(source, node.func.value, acc))
    return out


# ----------------------------------------------------------------------
# Rule 5: return statement returns the loop var / parameter instead of
# the accumulator
# ----------------------------------------------------------------------

def _fix_return_wrong_variable(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        acc = _find_accumulator(func)
        if not acc:
            continue
        param_names = {a.arg for a in func.args.args}
        loop_vars = {n.target.id for n in ast.walk(func)
                     if isinstance(n, ast.For) and isinstance(n.target, ast.Name)}
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                name = node.value.id
                if name != acc and (name in param_names or name in loop_vars):
                    out.append(_splice(source, node.value, acc))
    return out


# ----------------------------------------------------------------------
# Rule 6: undefined-name typo resolved to the loop var or accumulator
# ----------------------------------------------------------------------

def _fix_undefined_name_rename(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    builtin_names = set(dir(builtins))
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        assigned = {func.name}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                assigned.add(node.id)
            if isinstance(node, ast.FunctionDef):
                assigned.add(node.name)
        assigned |= {a.arg for a in func.args.args}
        loop_vars = [n.target.id for n in ast.walk(func)
                     if isinstance(n, ast.For) and isinstance(n.target, ast.Name)]
        acc_candidates = []
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
               and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                    acc_candidates.append(node.targets[0].id)
        undefined_nodes = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in assigned or node.id in builtin_names:
                    continue
                undefined_nodes.setdefault(node.id, []).append(node)
        for name, nodes in undefined_nodes.items():
            roles = set()
            for node in nodes:
                parent = _parent(node)
                role = None
                if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute) \
                   and parent.func.attr in ("append", "extend") and node in parent.args:
                    role = "item"
                elif isinstance(parent, ast.Attribute) and parent.attr in ("append", "extend", "count") \
                        and parent.value is node:
                    role = "collection"
                elif isinstance(parent, ast.List):
                    gp = _parent(parent)
                    if isinstance(gp, ast.AugAssign) and gp.value is parent:
                        role = "item"
                elif isinstance(parent, ast.Compare):
                    if parent.left is node:
                        role = "item"
                    elif node in parent.comparators:
                        role = "collection"
                if role:
                    roles.add(role)
            if len(roles) != 1:
                continue
            role = roles.pop()
            candidate = None
            if role == "item":
                uniq = list(dict.fromkeys(loop_vars))
                if len(uniq) == 1:
                    candidate = uniq[0]
            else:
                uniq = list(dict.fromkeys(acc_candidates))
                if len(uniq) == 1:
                    candidate = uniq[0]
            if not candidate or candidate == name:
                continue
            spans = sorted((_span(source, n) for n in nodes), key=lambda x: -x[0])
            new_source = source
            for s, e in spans:
                new_source = new_source[:s] + candidate + new_source[e:]
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 7: function never returns, append a `return <accumulator>`
# ----------------------------------------------------------------------

def _fix_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(func))
        if has_return or not func.body:
            continue
        acc = _find_accumulator(func)
        if not acc:
            continue
        lines = source.splitlines(keepends=True)
        last_stmt = func.body[-1]
        end_line = last_stmt.end_lineno
        indent = " " * func.body[0].col_offset
        insertion = f"{indent}return {acc}\n"
        new_lines = lines[:end_line] + [insertion] + lines[end_line:]
        out.append("".join(new_lines))
    return out


# ----------------------------------------------------------------------
# Rule 8: `return` statement wrongly nested inside the for-loop body
# ----------------------------------------------------------------------

def _fix_return_indented_inside_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in func.body:
            if isinstance(node, ast.For) and len(node.body) > 1 and isinstance(node.body[-1], ast.Return):
                ret = node.body[-1]
                acc = _find_accumulator(func)
                if not acc:
                    continue
                lines = source.splitlines(keepends=True)
                ret_start_line = ret.lineno - 1
                ret_end_line = ret.end_lineno - 1
                for_indent = " " * node.col_offset
                new_return_line = f"{for_indent}return {acc}\n"
                new_lines = lines[:ret_start_line] + lines[ret_end_line + 1:]
                insert_at = ret_start_line
                new_lines = new_lines[:insert_at] + [new_return_line] + new_lines[insert_at:]
                out.append("".join(new_lines))
    return out


# ----------------------------------------------------------------------
# Rule 9: no-arg mutating method used without call parens
# ----------------------------------------------------------------------

_NONE_METHS = {"reverse", "pop", "sort", "clear"}


def _fix_method_call_missing_parens(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and node.attr in _NONE_METHS:
            parent = _parent(node)
            if isinstance(parent, ast.Call) and parent.func is node:
                continue
            s, e = _span(source, node)
            out.append(source[:e] + "()" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 10: `return x.reverse()` / `return x.sort()` (returns None)
# ----------------------------------------------------------------------

def _fix_return_none_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr in ("reverse", "sort") \
               and isinstance(call.func.value, ast.Name) and not call.args:
                xname = call.func.value.id
                indent = " " * node.col_offset
                s, e = _span(source, node)
                new_text = f"{xname}.{call.func.attr}()\n{indent}return {xname}"
                out.append(source[:s] + new_text + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 11: while-loop index increment not guarded by else after removal
# ----------------------------------------------------------------------

def _fix_missing_else_before_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            body = node.body
            for idx in range(len(body) - 1):
                a, b = body[idx], body[idx + 1]
                if isinstance(a, ast.If) and not a.orelse and isinstance(b, ast.AugAssign):
                    s_a, e_a = _span(source, a)
                    s_b, e_b = _span(source, b)
                    if_src = source[s_a:e_a]
                    b_src = source[s_b:e_b]
                    indent = " " * a.col_offset
                    new_block = if_src + "\n" + indent + "else:\n" + indent + "    " + b_src
                    out.append(source[:s_a] + new_block + source[e_b:])
    return out


# ----------------------------------------------------------------------
# Rule 12: `if item in acc: acc.append(item)` (backwards duplicate test)
# ----------------------------------------------------------------------

def _fix_backwards_in_check(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.In):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Expr) \
               and isinstance(node.body[0].value, ast.Call):
                call = node.body[0].value
                if isinstance(call.func, ast.Attribute) and call.func.attr in ("append", "extend"):
                    cmp = node.test
                    if isinstance(call.func.value, ast.Name) and cmp.comparators \
                       and isinstance(cmp.comparators[0], ast.Name) \
                       and cmp.comparators[0].id == call.func.value.id:
                        left_text = _text(source, cmp.left)
                        right_text = _text(source, cmp.comparators[0])
                        out.append(_splice(source, cmp, f"{left_text} not in {right_text}"))
    return out


# ----------------------------------------------------------------------
# Rule 13: `if item != acc:` used instead of `not in`
# ----------------------------------------------------------------------

def _fix_eq_neq_membership(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
            func = _enclosing_function(node)
            if not func:
                continue
            enclosing_for = _enclosing_for(node)
            if not enclosing_for or not isinstance(enclosing_for.target, ast.Name):
                continue
            loop_var = enclosing_for.target.id
            left, right = node.left, node.comparators[0]
            if isinstance(left, ast.Name) and left.id == loop_var and isinstance(right, ast.Name):
                acc = _find_accumulator(func)
                if acc and right.id == acc:
                    left_text = _text(source, left)
                    right_text = _text(source, right)
                    out.append(_splice(source, node, f"{left_text} not in {right_text}"))
    return out


# ----------------------------------------------------------------------
# Rule 14: brackets used instead of parens for a method/function call
# ----------------------------------------------------------------------

_SUBSCRIPT_CALL_ATTRS = {"append", "count", "pop", "remove", "extend", "insert", "index"}
_SUBSCRIPT_CALL_NAMES = {"len", "list", "range", "str", "int", "sorted", "tuple", "set"}


def _fix_bracket_call_as_subscript(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            target_ok = False
            if isinstance(node.value, ast.Attribute) and node.value.attr in _SUBSCRIPT_CALL_ATTRS:
                target_ok = True
            elif isinstance(node.value, ast.Name) and node.value.id in _SUBSCRIPT_CALL_NAMES:
                target_ok = True
            if not target_ok:
                continue
            sl = node.slice
            if hasattr(ast, "Index") and isinstance(sl, ast.Index):
                sl = sl.value
            try:
                value_text = _text(source, node.value)
                slice_text = _text(source, sl)
            except Exception:
                continue
            new_text = f"{value_text}({slice_text})"
            out.append(_splice(source, node, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 15: `name == expr` used as a statement instead of assignment
# ----------------------------------------------------------------------

def _fix_assignment_as_equality(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare) \
           and len(node.value.ops) == 1 and isinstance(node.value.ops[0], ast.Eq):
            cmp = node.value
            left_text = _text(source, cmp.left)
            right_text = _text(source, cmp.comparators[0])
            out.append(_splice(source, node, f"{left_text} = {right_text}"))
    return out


# ----------------------------------------------------------------------
# Rule 16: `OrderedDict` used without the needed import
# ----------------------------------------------------------------------

def _fix_import_missing_ordereddict(source):
    if "OrderedDict" not in source:
        return []
    if "from collections import OrderedDict" in source or "import collections" in source:
        return []
    try:
        ast.parse(source)
    except SyntaxError:
        return []
    return [f"from collections import OrderedDict\n{source}"]


# ----------------------------------------------------------------------
# Rule 17: `lists(...)` typo for `list(...)`
# ----------------------------------------------------------------------

def _fix_typo_lists_to_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "lists":
            out.append(_splice(source, node.func, "list"))
    return out


# ----------------------------------------------------------------------
# Rule 18: `set(...)` used for dedup (doesn't preserve order)
# ----------------------------------------------------------------------

def _fix_set_to_dict_fromkeys(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            inner = None
            if isinstance(call.func, ast.Name) and call.func.id == "set" and len(call.args) == 1:
                inner = call.args[0]
            elif isinstance(call.func, ast.Name) and call.func.id == "list" and len(call.args) == 1 \
                    and isinstance(call.args[0], ast.Call) and isinstance(call.args[0].func, ast.Name) \
                    and call.args[0].func.id == "set" and call.args[0].args:
                inner = call.args[0].args[0]
            if inner is not None:
                inner_text = _text(source, inner)
                new_val = f"list(dict.fromkeys({inner_text}))"
                out.append(_splice(source, call, new_val))
    return out


# ----------------------------------------------------------------------
# Rule 19: confusing the original list with its `.copy()`
# ----------------------------------------------------------------------

def _fix_copy_confusion(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        param_names = {a.arg for a in func.args.args}
        copy_var = None
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
               and isinstance(node.targets[0], ast.Name):
                val = node.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
                   and val.func.attr == "copy" and isinstance(val.func.value, ast.Name) \
                   and val.func.value.id in param_names:
                    copy_var = node.targets[0].id
        if not copy_var:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == copy_var:
                subs = [s for s in ast.walk(node)
                        if isinstance(s, ast.Subscript) and isinstance(s.value, ast.Name)
                        and s.value.id in param_names]
                if not subs:
                    continue
                spans = sorted((_span(source, s.value) for s in subs), key=lambda x: -x[0])
                new_source = source
                for s, e in spans:
                    new_source = new_source[:s] + copy_var + new_source[e:]
                out.append(new_source)
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="iterate_over_builtin_list",
                 apply=_fix_iterate_over_builtin_list,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="membership_against_source",
                 apply=_fix_membership_against_source,
                 symptoms=("wrong",)),
            Rule(name="count_against_source",
                 apply=_fix_count_against_source,
                 symptoms=("wrong",)),
            Rule(name="append_target_wrong",
                 apply=_fix_append_target_wrong,
                 symptoms=("wrong",)),
            Rule(name="return_wrong_variable",
                 apply=_fix_return_wrong_variable,
                 symptoms=("wrong",)),
            Rule(name="undefined_name_rename",
                 apply=_fix_undefined_name_rename,
                 symptoms=("err:NameError", "err:UnboundLocalError")),
            Rule(name="missing_return",
                 apply=_fix_missing_return,
                 symptoms=("wrong",)),
            Rule(name="return_indented_inside_loop",
                 apply=_fix_return_indented_inside_loop,
                 symptoms=("wrong",)),
            Rule(name="method_call_missing_parens",
                 apply=_fix_method_call_missing_parens,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="return_none_returning_call",
                 apply=_fix_return_none_call,
                 symptoms=("wrong",)),
            Rule(name="missing_else_before_increment",
                 apply=_fix_missing_else_before_increment,
                 symptoms=("wrong", "err:IndexError", "timeout")),
            Rule(name="backwards_in_check",
                 apply=_fix_backwards_in_check,
                 symptoms=("wrong",)),
            Rule(name="eq_neq_membership",
                 apply=_fix_eq_neq_membership,
                 symptoms=("wrong",)),
            Rule(name="bracket_call_as_subscript",
                 apply=_fix_bracket_call_as_subscript,
                 symptoms=("err:TypeError",)),
            Rule(name="assignment_as_equality",
                 apply=_fix_assignment_as_equality,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="import_missing_ordereddict",
                 apply=_fix_import_missing_ordereddict,
                 symptoms=("err:NameError",)),
            Rule(name="typo_lists_to_list",
                 apply=_fix_typo_lists_to_list,
                 symptoms=("err:NameError",)),
            Rule(name="set_to_dict_fromkeys",
                 apply=_fix_set_to_dict_fromkeys,
                 symptoms=("wrong",)),
            Rule(name="copy_confusion",
                 apply=_fix_copy_confusion,
                 symptoms=("wrong",)),
        ]