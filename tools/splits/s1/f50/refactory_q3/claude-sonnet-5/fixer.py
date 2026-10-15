"""
Repair module for the "remove_extras" (duplicate elimination) assignment.

Each rule inspects the AST of a submission, looks for a narrow structural
signature of a known misconception, and -- if found -- splices a small,
local textual edit into the *original* source (never regenerating the
whole program via ast.unparse).
"""

import ast
import builtins as _builtins_mod

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

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


def _unwrap_index(node):
    if hasattr(ast, "Index") and isinstance(node, ast.Index):
        return node.value
    return node


def _first_param_name(func):
    if func.args.args:
        return func.args.args[0].arg
    return None


def _find_accumulator_name(func):
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.List) and len(val.elts) == 0:
                return node.targets[0].id
            if isinstance(val, ast.Tuple) and len(val.elts) == 0:
                return node.targets[0].id
    return None


def _is_used_as_accumulator(func, acc):
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("append", "extend") and \
               isinstance(node.func.value, ast.Name) and node.func.value.id == acc:
                return True
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) \
           and node.target.id == acc:
            return True
    return False


def _builtin_names():
    return set(dir(_builtins_mod))


def _safe(fn):
    def wrapper(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapper


# ---------------------------------------------------------------------------
# Rule 1: return the wrong (non-accumulator) variable
# ---------------------------------------------------------------------------

@_safe
def fix_return_wrong_var(source):
    tree = ast.parse(source)
    out = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        acc = _find_accumulator_name(func)
        if not acc or not _is_used_as_accumulator(func, acc):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id != acc:
                    out.append(_splice(source, node.value, acc))
    return out


# ---------------------------------------------------------------------------
# Rule 2: for-loop target/iterable swapped with accumulator/parameter
# ---------------------------------------------------------------------------

@_safe
def fix_for_loop_shadow(source):
    tree = ast.parse(source)
    out = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        param = _first_param_name(func)
        acc = _find_accumulator_name(func)
        if not param or not acc or param == acc:
            continue
        for forn in ast.walk(func):
            if not isinstance(forn, ast.For):
                continue
            if not (isinstance(forn.target, ast.Name) and isinstance(forn.iter, ast.Name)):
                continue
            t_id, i_id = forn.target.id, forn.iter.id
            ts, _ = _span(source, forn.target)
            _, ie = _span(source, forn.iter)
            if t_id == acc and i_id == param:
                is_, ie_ = _span(source, forn.iter)
                new_text = "i in " + source[is_:ie_]
                out.append(source[:ts] + new_text + source[ie:])
            elif t_id == param and i_id == acc:
                new_text = "i in " + param
                out.append(source[:ts] + new_text + source[ie:])
    return out


# ---------------------------------------------------------------------------
# Rule 3: membership tested against the original list instead of accumulator
# ---------------------------------------------------------------------------

@_safe
def fix_membership_wrong_list(source):
    tree = ast.parse(source)
    out = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for forn in ast.walk(func):
            if not isinstance(forn, ast.For):
                continue
            if not (isinstance(forn.target, ast.Name) and isinstance(forn.iter, ast.Name)):
                continue
            T, P = forn.target.id, forn.iter.id
            for ifn in ast.walk(forn):
                if ifn is forn or not isinstance(ifn, ast.If):
                    continue
                test = ifn.test
                if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                        and isinstance(test.ops[0], (ast.In, ast.NotIn))):
                    continue
                if not (isinstance(test.left, ast.Name) and test.left.id == T):
                    continue
                comp = test.comparators[0]
                if not (isinstance(comp, ast.Name) and comp.id == P):
                    continue
                acc_name = None
                for stmt in ifn.body:
                    for bn in ast.walk(stmt):
                        if isinstance(bn, ast.Call) and isinstance(bn.func, ast.Attribute) \
                           and bn.func.attr in ("append", "extend"):
                            if isinstance(bn.func.value, ast.Name) and bn.func.value.id not in (T, P):
                                acc_name = bn.func.value.id
                                break
                        if isinstance(bn, ast.AugAssign) and isinstance(bn.target, ast.Name) \
                           and isinstance(bn.op, ast.Add) and bn.target.id not in (T, P):
                            acc_name = bn.target.id
                            break
                    if acc_name:
                        break
                if acc_name:
                    out.append(_splice(source, comp, acc_name))
    return out


# ---------------------------------------------------------------------------
# Rule 4: `if x in acc:` immediately followed by adding x to acc (should be
# `not in`)
# ---------------------------------------------------------------------------

@_safe
def flip_in_to_notin(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.In)):
            continue
        if not isinstance(test.left, ast.Name) or not isinstance(test.comparators[0], ast.Name):
            continue
        T = test.left.id
        X = test.comparators[0].id
        action = False
        for stmt in node.body:
            for bn in ast.walk(stmt):
                if isinstance(bn, ast.Call) and isinstance(bn.func, ast.Attribute) \
                   and bn.func.attr in ("append", "extend") \
                   and isinstance(bn.func.value, ast.Name) and bn.func.value.id == X:
                    if bn.args:
                        a0 = bn.args[0]
                        if isinstance(a0, ast.Name) and a0.id == T:
                            action = True
                        elif isinstance(a0, ast.List) and len(a0.elts) == 1 \
                                and isinstance(a0.elts[0], ast.Name) and a0.elts[0].id == T:
                            action = True
                if isinstance(bn, ast.AugAssign) and isinstance(bn.target, ast.Name) \
                   and bn.target.id == X and isinstance(bn.op, ast.Add):
                    if isinstance(bn.value, ast.Name) and bn.value.id == T:
                        action = True
                    elif isinstance(bn.value, ast.List) and len(bn.value.elts) == 1 \
                            and isinstance(bn.value.elts[0], ast.Name) and bn.value.elts[0].id == T:
                        action = True
        if action:
            ls, le = _span(source, test.left)
            cs, ce = _span(source, test.comparators[0])
            new_test = source[ls:le] + " not in " + source[cs:ce]
            out.append(_splice(source, test, new_test))
    return out


# ---------------------------------------------------------------------------
# Rule 5: `acc = acc.append(x)` (append returns None) assign-back bug
# ---------------------------------------------------------------------------

@_safe
def fix_append_assign_back(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            value = node.value
        else:
            continue
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) \
           and value.func.attr == "append":
            vs, ve = _span(source, value)
            call_text = source[vs:ve]
            out.append(_splice(source, node, call_text))
    return out


# ---------------------------------------------------------------------------
# Rule 6: bare-element concatenation instead of list-wrapped concatenation
# ---------------------------------------------------------------------------

@_safe
def wrap_add_in_list(source):
    tree = ast.parse(source)
    out = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        acc = _find_accumulator_name(func)
        if not acc:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) \
               and isinstance(node.target, ast.Name) and node.target.id == acc:
                if not isinstance(node.value, (ast.List, ast.Tuple)):
                    vs, ve = _span(source, node.value)
                    out.append(source[:vs] + "[" + source[vs:ve] + "]" + source[ve:])
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name) and node.targets[0].id == acc:
                if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                    left, right = node.value.left, node.value.right
                    if isinstance(left, ast.Name) and left.id == acc \
                       and not isinstance(right, (ast.List, ast.Tuple)):
                        vs, ve = _span(source, right)
                        out.append(source[:vs] + "[" + source[vs:ve] + "]" + source[ve:])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "extend" and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id == acc and len(node.args) == 1:
                arg = node.args[0]
                if not isinstance(arg, (ast.List, ast.Tuple)):
                    vs, ve = _span(source, arg)
                    out.append(source[:vs] + "[" + source[vs:ve] + "]" + source[ve:])
    return out


# ---------------------------------------------------------------------------
# Rule 7: `.insert(0, x)` used to simulate append
# ---------------------------------------------------------------------------

@_safe
def fix_insert_zero_to_append(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "insert" and len(node.args) == 2:
            first = node.args[0]
            if isinstance(first, ast.Constant) and first.value == 0:
                os_, oe = _span(source, node.func.value)
                as_, ae = _span(source, node.args[1])
                new_call = source[os_:oe] + ".append(" + source[as_:ae] + ")"
                out.append(_splice(source, node, new_call))
    return out


# ---------------------------------------------------------------------------
# Rule 8: `x.append[y]` subscript instead of call
# ---------------------------------------------------------------------------

@_safe
def fix_subscript_append(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
           and node.value.attr == "append":
            os_, oe = _span(source, node.value.value)
            sl = _unwrap_index(node.slice)
            ss, se = _span(source, sl)
            new_text = source[os_:oe] + ".append(" + source[ss:se] + ")"
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 9: builtin name `list` used where the parameter should be
# ---------------------------------------------------------------------------

@_safe
def fix_builtin_list_name(source):
    tree = ast.parse(source)
    out = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        param = _first_param_name(func)
        if not param or param == "list":
            continue
        assigned = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                assigned.add(n.id)
        if "list" in assigned:
            continue
        targets = [n for n in ast.walk(func)
                   if isinstance(n, ast.Name) and n.id == "list" and isinstance(n.ctx, ast.Load)]
        if not targets:
            continue
        new_source = source
        for n in sorted(targets, key=lambda x: (x.lineno, x.col_offset), reverse=True):
            s, e = _span(new_source, n)
            new_source = new_source[:s] + param + new_source[e:]
        out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 10: accumulator is built but never returned
# ---------------------------------------------------------------------------

@_safe
def add_missing_return(source):
    tree = ast.parse(source)
    out = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(func))
        if has_return:
            continue
        acc = _find_accumulator_name(func)
        if not acc or not func.body:
            continue
        last = func.body[-1]
        indent = " " * last.col_offset
        _, e = _span(source, last)
        insertion = "\n" + indent + "return " + acc
        out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 11: loop variable unused while an undefined name is referenced instead
# ---------------------------------------------------------------------------

@_safe
def fix_undefined_loop_var_ref(source):
    tree = ast.parse(source)
    out = []
    builtin_names = _builtin_names()
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        defined = set(a.arg for a in func.args.args)
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                defined.add(n.id)
            if isinstance(n, ast.FunctionDef):
                defined.add(n.name)
        for node in ast.walk(func):
            if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
                continue
            T = node.target.id
            used_T = False
            undefined_ids = {}
            for n in ast.walk(node):
                if n is node:
                    continue
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    if n.id == T:
                        used_T = True
                    elif n.id not in defined and n.id not in builtin_names:
                        undefined_ids.setdefault(n.id, []).append(n)
            if not used_T and len(undefined_ids) == 1:
                _, nodes_ = next(iter(undefined_ids.items()))
                new_source = source
                for n in sorted(nodes_, key=lambda x: (x.lineno, x.col_offset), reverse=True):
                    s, e = _span(new_source, n)
                    new_source = new_source[:s] + T + new_source[e:]
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Rule 12: missing guard before indexing `lst[0]` on an (possibly empty) list
# ---------------------------------------------------------------------------

@_safe
def guard_empty_list_before_index0(source):
    tree = ast.parse(source)
    out = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        param = _first_param_name(func)
        if not param:
            continue
        fs, fe = _span(source, func)
        func_text = source[fs:fe]
        guard_markers = (
            param + " == []", param + "==[]",
            "len(" + param + ") == 0", "len(" + param + ")==0",
            param + " != []", param + "!=[]",
        )
        if any(m in func_text for m in guard_markers):
            continue
        target_stmt = None
        for stmt in func.body:
            found = False
            for n in ast.walk(stmt):
                if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) \
                   and n.value.id == param:
                    sl = _unwrap_index(n.slice)
                    if isinstance(sl, ast.Constant) and sl.value == 0:
                        found = True
                        break
            if found:
                target_stmt = stmt
                break
        if target_stmt is None:
            continue
        indent = " " * target_stmt.col_offset
        s, _ = _span(source, target_stmt)
        guard = "if len(" + param + ") == 0:\n" + indent + "    return []\n" + indent
        out.append(source[:s] + guard + source[s:])
    return out


# ---------------------------------------------------------------------------
# Rule 13: off-by-one `range(len(x) + 1)`
# ---------------------------------------------------------------------------

@_safe
def fix_range_off_by_one(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                left, right = arg.left, arg.right
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) \
                   and left.func.id == "len" and isinstance(right, ast.Constant) \
                   and right.value == 1:
                    ls, le = _span(source, left)
                    out.append(_splice(source, arg, source[ls:le]))
    return out


# ---------------------------------------------------------------------------
# Rule 14: `acc.append(lst.remove(x))` -- remove() returns None
# ---------------------------------------------------------------------------

@_safe
def fix_remove_call_as_append_arg(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr in ("append", "extend") and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) \
               and arg.func.attr == "remove" and len(arg.args) == 1:
                inner = arg.args[0]
                s, e = _span(source, inner)
                out.append(_splice(source, arg, source[s:e]))
    return out


# ---------------------------------------------------------------------------
# Fixer
# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="return_wrong_var", apply=fix_return_wrong_var,
                 symptoms=("wrong",)),
            Rule(name="for_loop_shadow_swap", apply=fix_for_loop_shadow,
                 symptoms=("wrong", "err:TypeError", "err:AttributeError")),
            Rule(name="membership_checked_against_wrong_list", apply=fix_membership_wrong_list,
                 symptoms=("wrong",)),
            Rule(name="flip_in_to_notin", apply=flip_in_to_notin,
                 symptoms=("wrong",)),
            Rule(name="append_assign_back", apply=fix_append_assign_back,
                 symptoms=("wrong", "err:AttributeError", "err:TypeError")),
            Rule(name="wrap_bare_element_in_list", apply=wrap_add_in_list,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="insert_zero_to_append", apply=fix_insert_zero_to_append,
                 symptoms=("wrong",)),
            Rule(name="subscript_append_to_call", apply=fix_subscript_append,
                 symptoms=("err:TypeError",)),
            Rule(name="builtin_list_name_typo", apply=fix_builtin_list_name,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="add_missing_return", apply=add_missing_return,
                 symptoms=("wrong",)),
            Rule(name="undefined_loop_var_reference", apply=fix_undefined_loop_var_ref,
                 symptoms=("err:NameError",)),
            Rule(name="guard_empty_list_before_index0", apply=guard_empty_list_before_index0,
                 symptoms=("err:IndexError",)),
            Rule(name="range_len_plus_one_off_by_one", apply=fix_range_off_by_one,
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="remove_call_used_as_append_arg", apply=fix_remove_call_as_append_arg,
                 symptoms=("wrong",)),
        ]