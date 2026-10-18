"""
Local, deterministic repair tool for the "remove_extras" dedup assignment.

Each Rule targets one narrow misconception observed in buggy submissions and
performs a small, local AST-span splice on the ORIGINAL source text.
"""

import ast
import re
import difflib
import builtins as _builtins

from src.core.repair import Rule


# --------------------------------------------------------------------------
# Generic AST/text helpers
# --------------------------------------------------------------------------

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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _safe(fn):
    def wrapped(source):
        try:
            return [c for c in fn(source) if c and c != source]
        except Exception:
            return []
    return wrapped


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _funcs(tree, name="remove_extras"):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name]


def _all_funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _find_acc(stmts):
    """Find the name of a list being built via append/extend/+= in a stmt list."""
    for st in stmts:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            f = st.value.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
               and f.attr in ("append", "extend"):
                return f.value.id
        if isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name) \
           and isinstance(st.op, ast.Add):
            return st.target.id
        if isinstance(st, ast.Assign) and len(st.targets) == 1 \
           and isinstance(st.targets[0], ast.Name):
            tgt = st.targets[0].id
            if isinstance(st.value, ast.BinOp) and isinstance(st.value.op, ast.Add):
                left = st.value.left
                if isinstance(left, ast.Name) and left.id == tgt:
                    return tgt
    return None


def _empty_list_or_tuple_assign(func):
    """Return name of first var assigned to [] or () at top of function body."""
    for st in func.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 \
           and isinstance(st.targets[0], ast.Name):
            if isinstance(st.value, (ast.List, ast.Tuple)) and len(st.value.elts) == 0:
                return st.targets[0].id
    return None


# --------------------------------------------------------------------------
# Rule 1: bare `list` builtin used instead of the parameter name
# --------------------------------------------------------------------------

@_safe
def _fix_bare_list_builtin(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        if param == "list":
            continue
        call_funcs = {id(n.func) for n in ast.walk(func) if isinstance(n, ast.Call)}
        targets = [n for n in ast.walk(func)
                   if isinstance(n, ast.Name) and n.id == "list" and id(n) not in call_funcs]
        if not targets:
            continue
        new_source = source
        for s, e in sorted((_span(source, n) for n in targets), key=lambda t: -t[0]):
            new_source = new_source[:s] + param + new_source[e:]
        out.append(new_source)
    return out


# --------------------------------------------------------------------------
# Rule 2/3: membership test comparing against the wrong operand
# --------------------------------------------------------------------------

@_safe
def _fix_membership_comparator(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                for st in node.body:
                    if isinstance(st, ast.If) and isinstance(st.test, ast.Compare) \
                       and len(st.test.ops) == 1 and isinstance(st.test.ops[0], (ast.In, ast.NotIn)):
                        acc = _find_acc(st.body) or _find_acc(st.orelse)
                        if not acc:
                            continue
                        comparator = st.test.comparators[0]
                        if isinstance(comparator, ast.Name) and comparator.id != acc:
                            out.append(_splice(source, comparator, acc))
    return out


@_safe
def _fix_membership_left_operand(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                loopvar = node.target.id
                for st in node.body:
                    if isinstance(st, ast.If) and isinstance(st.test, ast.Compare) \
                       and len(st.test.ops) == 1 and isinstance(st.test.ops[0], (ast.In, ast.NotIn)):
                        acc = _find_acc(st.body) or _find_acc(st.orelse)
                        if not acc:
                            continue
                        left = st.test.left
                        if isinstance(left, ast.Name) and left.id != loopvar:
                            out.append(_splice(source, left, loopvar))
    return out


# --------------------------------------------------------------------------
# Rule 4: `in` used where `not in` was meant right before an append
# --------------------------------------------------------------------------

@_safe
def _flip_in_to_notin(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.In) \
           and not node.orelse:
            acc = _find_acc(node.body)
            comparator = node.test.comparators[0]
            if acc and isinstance(comparator, ast.Name) and comparator.id == acc:
                left_txt = _text(source, node.test.left)
                right_txt = _text(source, comparator)
                new_test = f"{left_txt} not in {right_txt}"
                out.append(_splice(source, node.test, new_test))
    return out


# --------------------------------------------------------------------------
# Rule: `!=`/`==` used instead of `not in`/`in` against the accumulator
# --------------------------------------------------------------------------

@_safe
def _fix_neq_to_notin(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], (ast.NotEq, ast.Eq)):
            right = node.test.comparators[0]
            acc = _find_acc(node.body) or _find_acc(node.orelse)
            if acc and isinstance(right, ast.Name) and right.id == acc:
                op_txt = "not in" if isinstance(node.test.ops[0], ast.NotEq) else "in"
                left_txt = _text(source, node.test.left)
                right_txt = _text(source, right)
                new_test = f"{left_txt} {op_txt} {right_txt}"
                out.append(_splice(source, node.test, new_test))
    return out


# --------------------------------------------------------------------------
# Rule 5: append/extend targets an undefined name or the source list
#          instead of the real accumulator
# --------------------------------------------------------------------------

@_safe
def _fix_append_target(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        acc = _empty_list_or_tuple_assign(func)
        if not acc:
            continue
        assigned = set(a.arg for a in func.args.args)
        source_names = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    assigned.add(node.target.id)
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    assigned.add(node.target.id)
                if isinstance(node.iter, ast.Name):
                    source_names.add(node.iter.id)
        for node in ast.walk(func):
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                   and f.attr in ("append", "extend"):
                    y = f.value.id
                    if y != acc and (y not in assigned or y in source_names):
                        out.append(_splice(source, f.value, acc))
    return out


# --------------------------------------------------------------------------
# Rule 6: `x = y.append(z)` (or AugAssign) should just be the call itself
# --------------------------------------------------------------------------

@_safe
def _simplify_assign_from_append(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        value = None
        if isinstance(node, ast.Assign):
            value = node.value
        elif isinstance(node, ast.AugAssign):
            value = node.value
        else:
            continue
        if isinstance(value, ast.Call):
            f = value.func
            if isinstance(f, ast.Attribute) and f.attr in ("append", "extend"):
                call_text = _text(source, value)
                out.append(_splice(source, node, call_text))
    return out


# --------------------------------------------------------------------------
# Rule 7: bare `.pop` / `.reverse` / `.sort` missing call parentheses
# --------------------------------------------------------------------------

@_safe
def _add_missing_parens(source):
    tree = _parse(source)
    if tree is None:
        return []
    call_funcs = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("pop", "reverse", "sort") \
           and id(node) not in call_funcs:
            out.append(_splice(source, node, _text(source, node) + "()"))
    return out


# --------------------------------------------------------------------------
# Rule 8: `return lst.reverse()` returns None; reverse then return the list
# --------------------------------------------------------------------------

@_safe
def _fix_return_reverse_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Attribute) and f.attr == "reverse" \
               and isinstance(f.value, ast.Name) and not node.value.args:
                obj = f.value.id
                indent = " " * node.col_offset
                new_text = f"{obj}.reverse()\n{indent}return {obj}"
                out.append(_splice(source, node, new_text))
    return out


# --------------------------------------------------------------------------
# Rule 9: return statement returns the wrong name instead of the accumulator
# --------------------------------------------------------------------------

@_safe
def _fix_return_wrong_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        acc = _empty_list_or_tuple_assign(func)
        if not acc:
            continue
        found_idiom = False
        for node in ast.walk(func):
            if isinstance(node, ast.For):
                for st in node.body:
                    if isinstance(st, ast.If) and isinstance(st.test, ast.Compare) \
                       and len(st.test.ops) == 1 and isinstance(st.test.ops[0], ast.NotIn):
                        if _find_acc(st.body) == acc:
                            found_idiom = True
        if not found_idiom or not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, ast.Return) and isinstance(last.value, ast.Name) \
           and last.value.id != acc:
            out.append(_splice(source, last.value, acc))
    return out


# --------------------------------------------------------------------------
# Rule 10: missing return statement entirely
# --------------------------------------------------------------------------

@_safe
def _insert_missing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        acc = _empty_list_or_tuple_assign(func)
        if not acc or not func.body:
            continue
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        last = func.body[-1]
        indent = " " * last.col_offset
        s, e = _span(source, last)
        out.append(source[:e] + f"\n{indent}return {acc}" + source[e:])
    return out


# --------------------------------------------------------------------------
# Rule 11: the accumulator used in `not in` / `.append` is never declared
# --------------------------------------------------------------------------

@_safe
def _declare_missing_accumulator(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        assigned = set(a.arg for a in func.args.args)
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    assigned.add(node.target.id)
        for node in ast.walk(func):
            if isinstance(node, ast.For):
                for st in node.body:
                    if isinstance(st, ast.If) and isinstance(st.test, ast.Compare) \
                       and len(st.test.ops) == 1 and isinstance(st.test.ops[0], ast.NotIn):
                        comp = st.test.comparators[0]
                        if isinstance(comp, ast.Name) and comp.id not in assigned:
                            indent = " " * node.col_offset
                            s, e = _span(source, node)
                            out.append(source[:s] + f"{comp.id} = []\n{indent}" + source[s:])
    return out


# --------------------------------------------------------------------------
# Rule 12: `.insert(idx, x)` used where `.append(x)` keeps correct order
# --------------------------------------------------------------------------

@_safe
def _convert_insert_to_append(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "insert" \
               and isinstance(f.value, ast.Name) and len(node.args) == 2:
                obj = f.value.id
                elt_text = _text(source, node.args[1])
                out.append(_splice(source, node, f"{obj}.append({elt_text})"))
    return out


# --------------------------------------------------------------------------
# Rule 13: `.count()` check uses the source list instead of the accumulator,
#          and/or uses the wrong threshold
# --------------------------------------------------------------------------

@_safe
def _fix_count_object(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        acc = _empty_list_or_tuple_assign(func)
        if not acc:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.For):
                for st in node.body:
                    if isinstance(st, ast.If) and isinstance(st.test, ast.Compare) \
                       and len(st.test.ops) == 1 and isinstance(st.test.ops[0], (ast.Eq, ast.Lt)):
                        left = st.test.left
                        if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) \
                           and left.func.attr == "count":
                            obj = left.func.value
                            if isinstance(obj, ast.Name) and obj.id != acc:
                                out.append(_splice(source, obj, acc))
    return out


@_safe
def _fix_count_threshold(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], (ast.Eq, ast.Lt)):
            left = node.test.left
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) \
               and left.func.attr == "count":
                comparator = node.test.comparators[0]
                op_ok = isinstance(node.test.ops[0], ast.Eq)
                num_ok = isinstance(comparator, ast.Constant) and comparator.value == 0
                if not (op_ok and num_ok):
                    left_txt = _text(source, left)
                    out.append(_splice(source, node.test, f"{left_txt} == 0"))
    return out


# --------------------------------------------------------------------------
# Rule 14: OrderedDict idiom typos
# --------------------------------------------------------------------------

@_safe
def _fix_ordereddict_typos(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "lists":
            out.append(_splice(source, node.func, "list"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Attribute) and f.attr == "fromkeys" \
               and isinstance(f.value, ast.Name) and f.value.id == "OrderedDict":
                call_text = _text(source, node.value)
                out.append(_splice(source, node.value, f"list({call_text})"))
    has_import = any(
        isinstance(n, ast.ImportFrom) and n.module == "collections"
        and any(a.name == "OrderedDict" for a in n.names)
        for n in ast.walk(tree)
    )
    uses_od = any(isinstance(n, ast.Name) and n.id == "OrderedDict" for n in ast.walk(tree))
    if uses_od and not has_import:
        out.append("from collections import OrderedDict\n" + source)
    return out


# --------------------------------------------------------------------------
# Rule 15: `set(...)` used for dedup loses order; prefer OrderedDict idiom
# --------------------------------------------------------------------------

@_safe
def _fix_set_to_ordereddict(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "list" and len(call.args) == 1 \
               and isinstance(call.args[0], ast.Call) and isinstance(call.args[0].func, ast.Name) \
               and call.args[0].func.id == "set":
                arg_text = _text(source, call.args[0].args[0])
                out.append(_splice(source, call, f"list(OrderedDict.fromkeys({arg_text}))"))
            elif isinstance(call.func, ast.Name) and call.func.id == "set" and len(call.args) == 1:
                arg_text = _text(source, call.args[0])
                out.append(_splice(source, call, f"list(OrderedDict.fromkeys({arg_text}))"))
    return out


# --------------------------------------------------------------------------
# Rule 16: method call written with subscript syntax: `obj.append[x]`
# --------------------------------------------------------------------------

@_safe
def _fix_subscript_as_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
           and node.value.attr in ("append", "count", "extend", "remove"):
            obj_text = _text(source, node.value)
            sl = node.slice
            if isinstance(sl, ast.Index):  # pragma: no cover (py<3.9 compat)
                sl = sl.value
            arg_text = _text(source, sl)
            out.append(_splice(source, node, f"{obj_text}({arg_text})"))
    return out


# --------------------------------------------------------------------------
# Rule 17: `acc += x` should be `acc += [x]` (or `(x,)` for tuple accs)
# --------------------------------------------------------------------------

@_safe
def _fix_augassign_wrap(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        acc_type = {}
        for st in func.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 \
               and isinstance(st.targets[0], ast.Name):
                if isinstance(st.value, ast.List) and len(st.value.elts) == 0:
                    acc_type[st.targets[0].id] = "list"
                elif isinstance(st.value, ast.Tuple) and len(st.value.elts) == 0:
                    acc_type[st.targets[0].id] = "tuple"
        for node in ast.walk(func):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) \
               and isinstance(node.target, ast.Name):
                tname = node.target.id
                if tname in acc_type and isinstance(node.value, ast.Name):
                    val_text = _text(source, node.value)
                    wrapped = f"[{val_text}]" if acc_type[tname] == "list" else f"({val_text},)"
                    out.append(_splice(source, node.value, wrapped))
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
               and isinstance(node.targets[0], ast.Name):
                tname = node.targets[0].id
                if tname in acc_type and isinstance(node.value, ast.BinOp) \
                   and isinstance(node.value.op, ast.Add):
                    left, right = node.value.left, node.value.right
                    if isinstance(left, ast.Name) and left.id == tname and isinstance(right, ast.Name):
                        val_text = _text(source, right)
                        wrapped = f"[{val_text}]" if acc_type[tname] == "list" else f"({val_text},)"
                        out.append(_splice(source, right, wrapped))
    return out


# --------------------------------------------------------------------------
# Rule 18: generic misspelled-identifier fix (NameError-style typos)
# --------------------------------------------------------------------------

def _collect_defined(tree, func):
    defined = set(a.arg for a in func.args.args)
    defined.update(dir(_builtins))
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            defined.add(n.name)
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                defined.add(a.asname or a.name)
        if isinstance(n, ast.Import):
            for a in n.names:
                defined.add((a.asname or a.name).split(".")[0])
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                for nn in ast.walk(t):
                    if isinstance(nn, ast.Name):
                        defined.add(nn.id)
        elif isinstance(n, ast.AugAssign):
            if isinstance(n.target, ast.Name):
                defined.add(n.target.id)
        elif isinstance(n, ast.For):
            for nn in ast.walk(n.target):
                if isinstance(nn, ast.Name):
                    defined.add(nn.id)
    return defined


@_safe
def _fix_misspelled_identifier(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    builtin_names = set(dir(_builtins))
    for func in _all_funcs(tree):
        defined = _collect_defined(tree, func)
        used_undefined = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in defined:
                    used_undefined.setdefault(node.id, []).append(node)
        if not used_undefined:
            continue
        pool = sorted(n for n in defined if n not in builtin_names and n.isidentifier())
        if not pool:
            continue
        s_func, e_func = _span(source, func)
        func_src = source[s_func:e_func]
        for bad in used_undefined:
            matches = difflib.get_close_matches(bad, pool, n=1, cutoff=0.6)
            if not matches or matches[0] == bad:
                continue
            good = matches[0]
            new_func_src = re.sub(r"\b" + re.escape(bad) + r"\b", good, func_src)
            if new_func_src != func_src:
                out.append(source[:s_func] + new_func_src + source[e_func:])
    return out


# --------------------------------------------------------------------------
# Rule 19: nested while-loop remove idiom increments index even on a removal
# --------------------------------------------------------------------------

@_safe
def _fix_while_missing_else(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            body = node.body
            for i in range(len(body) - 1):
                a, b = body[i], body[i + 1]
                if isinstance(a, ast.If) and not a.orelse \
                   and isinstance(b, ast.AugAssign) and isinstance(b.op, ast.Add):
                    has_slice = any(isinstance(n, ast.Slice) for n in ast.walk(a))
                    if not has_slice:
                        continue
                    s_a, e_a = _span(source, a)
                    s_b, e_b = _span(source, b)
                    if_indent = " " * a.col_offset
                    inner_indent = if_indent + "    "
                    aug_text = source[s_b:e_b]
                    new_block = source[s_a:e_a] + f"\n{if_indent}else:\n{inner_indent}{aug_text}"
                    out.append(source[:s_a] + new_block + source[e_b:])
    return out


# --------------------------------------------------------------------------
# Rule 20: outer while loop never increments its index (infinite loop)
# --------------------------------------------------------------------------

@_safe
def _fix_while_missing_increment(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare) \
           and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Lt) \
           and isinstance(node.test.left, ast.Name):
            var = node.test.left.id
            incremented = False
            for st in ast.walk(node):
                if isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name) \
                   and st.target.id == var and isinstance(st.op, ast.Add):
                    incremented = True
                if isinstance(st, ast.Assign) and len(st.targets) == 1 \
                   and isinstance(st.targets[0], ast.Name) and st.targets[0].id == var:
                    if isinstance(st.value, ast.BinOp) and isinstance(st.value.op, ast.Add):
                        l = st.value.left
                        if isinstance(l, ast.Name) and l.id == var:
                            incremented = True
            if not incremented and node.body:
                last = node.body[-1]
                indent = " " * last.col_offset
                s, e = _span(source, last)
                out.append(source[:e] + f"\n{indent}{var} += 1" + source[e:])
    return out


# --------------------------------------------------------------------------
# Fixer
# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="bare_list_builtin_instead_of_param",
                 apply=_fix_bare_list_builtin,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="membership_comparator_wrong_object",
                 apply=_fix_membership_comparator,
                 symptoms=("wrong",)),
            Rule(name="membership_left_operand_wrong",
                 apply=_fix_membership_left_operand,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="in_should_be_notin_before_append",
                 apply=_flip_in_to_notin,
                 symptoms=("wrong",)),
            Rule(name="neq_eq_should_be_in_notin",
                 apply=_fix_neq_to_notin,
                 symptoms=("wrong",)),
            Rule(name="append_target_wrong_or_undefined",
                 apply=_fix_append_target,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="assign_from_append_call",
                 apply=_simplify_assign_from_append,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="missing_call_parens_on_method",
                 apply=_add_missing_parens,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="return_reverse_call_returns_none",
                 apply=_fix_return_reverse_call,
                 symptoms=("wrong",)),
            Rule(name="return_wrong_name_instead_of_accumulator",
                 apply=_fix_return_wrong_name,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="missing_return_statement",
                 apply=_insert_missing_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="accumulator_never_declared",
                 apply=_declare_missing_accumulator,
                 symptoms=("err:NameError",)),
            Rule(name="insert_should_be_append",
                 apply=_convert_insert_to_append,
                 symptoms=("wrong",)),
            Rule(name="count_check_wrong_object",
                 apply=_fix_count_object,
                 symptoms=("wrong",)),
            Rule(name="count_check_wrong_threshold",
                 apply=_fix_count_threshold,
                 symptoms=("wrong",)),
            Rule(name="ordereddict_idiom_typos",
                 apply=_fix_ordereddict_typos,
                 symptoms=("err:NameError", "wrong", "err:AttributeError")),
            Rule(name="set_loses_order_use_ordereddict",
                 apply=_fix_set_to_ordereddict,
                 symptoms=("wrong",)),
            Rule(name="subscript_used_instead_of_call",
                 apply=_fix_subscript_as_call,
                 symptoms=("err:TypeError",)),
            Rule(name="augassign_missing_sequence_wrap",
                 apply=_fix_augassign_wrap,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="misspelled_identifier",
                 apply=_fix_misspelled_identifier,
                 symptoms=("err:NameError",)),
            Rule(name="while_remove_missing_else_skip",
                 apply=_fix_while_missing_else,
                 symptoms=("wrong",)),
            Rule(name="while_missing_outer_increment",
                 apply=_fix_while_missing_increment,
                 symptoms=("timeout",)),
        ]