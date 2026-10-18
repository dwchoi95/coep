"""
Repair module for the "Duplicate elimination" (remove_extras) assignment.

Each Rule below targets one structural misconception commonly seen in student
submissions. Rules operate purely on the AST to locate a node and then splice
a small, local text edit into the original source (never rebuilding the whole
program via ast.unparse).
"""

import ast
import difflib
import builtins

from src.core.repair import Rule


# --------------------------------------------------------------------------
# Generic helpers
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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _guard(fn):
    def wrapped(source):
        try:
            out = fn(source)
        except Exception:
            return []
        return [c for c in out if isinstance(c, str) and c != source]
    return wrapped


def _slice_value(sl):
    # Python <3.9 wraps subscript slices in ast.Index
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

@_guard
def fix_for_over_builtin_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        if param == "list":
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
                out.append(_splice(source, node.iter, param))
    return out


@_guard
def fix_broken_for_header(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        acc_names = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.Tuple)) and not n.value.elts:
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        acc_names.add(t.id)
        assigned = set(a.arg for a in func.args.args)
        for n in ast.walk(func):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    for sub in ast.walk(t):
                        if isinstance(sub, ast.Name):
                            assigned.add(sub.id)
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
                assigned.add(n.target.id)
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Name):
                tgt, it = node.target.id, node.iter.id
                bad = (tgt in acc_names) or (it in acc_names and it != param)
                if not bad:
                    continue
                free = set()
                for m in ast.walk(node):
                    if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Load):
                        if m.id not in assigned and m.id != param and m.id not in acc_names:
                            free.add(m.id)
                if len(free) == 1:
                    loopvar = next(iter(free))
                elif tgt not in acc_names:
                    loopvar = tgt
                else:
                    loopvar = "i"
                ts, _ = _span(source, node.target)
                _, ie = _span(source, node.iter)
                new_text = f"{loopvar} in {param}"
                out.append(source[:ts] + new_text + source[ie:])
    return out


@_guard
def fix_membership_wrong_container(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Name):
            continue
        iter_name = node.iter.id
        if not isinstance(node.target, ast.Name):
            continue
        target_name = node.target.id
        acc = None
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend", "insert"):
                if isinstance(n.func.value, ast.Name) and n.func.value.id != iter_name:
                    acc = n.func.value.id
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id != iter_name:
                acc = n.target.id
        for n in ast.walk(node):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], (ast.In, ast.NotIn)):
                left, right = n.left, n.comparators[0]
                if acc and isinstance(right, ast.Name) and right.id == iter_name and isinstance(left, ast.Name) and left.id == target_name:
                    out.append(_splice(source, right, acc))
                if isinstance(left, ast.Name) and left.id == iter_name and isinstance(right, ast.Name):
                    out.append(_splice(source, left, target_name))
    return out


@_guard
def fix_count_container_rename(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Name):
            continue
        iter_name = node.iter.id
        acc = None
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend"):
                if isinstance(n.func.value, ast.Name) and n.func.value.id != iter_name:
                    acc = n.func.value.id
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id != iter_name:
                acc = n.target.id
        if not acc:
            continue
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "count":
                obj = n.func.value
                if isinstance(obj, ast.Name) and obj.id == iter_name:
                    out.append(_splice(source, obj, acc))
    return out


@_guard
def fix_count_eq_one_to_zero(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            comp = node.comparators[0]
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) and left.func.attr == "count":
                if isinstance(comp, ast.Constant) and comp.value == 1:
                    out.append(_splice(source, comp, "0"))
    return out


@_guard
def fix_append_wrong_container(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                iter_name = node.iter.id
                acc = None
                for n in ast.walk(func):
                    if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.Tuple)) and not n.value.elts:
                        for t in n.targets:
                            if isinstance(t, ast.Name) and t.id != iter_name:
                                acc = t.id
                if not acc:
                    continue
                for n in ast.walk(node):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend"):
                        if isinstance(n.func.value, ast.Name) and n.func.value.id == iter_name:
                            out.append(_splice(source, n.func.value, acc))
    return out


@_guard
def fix_extend_scalar_to_append(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "extend" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, (ast.List, ast.Tuple, ast.ListComp)):
                continue
            s, e = _span(source, node.func)
            text = source[s:e]
            new_text = text[: len(text) - len("extend")] + "append"
            out.append(source[:s] + new_text + source[e:])
    return out


@_guard
def fix_list_call_wrap_scalar(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "list" and len(node.args) == 1:
            if isinstance(node.args[0], ast.Name):
                arg_s, arg_e = _span(source, node.args[0])
                out.append(_splice(source, node, "[" + source[arg_s:arg_e] + "]"))
    return out


@_guard
def fix_insert_to_append(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "insert" and len(node.args) == 2:
            obj_s, obj_e = _span(source, node.func.value)
            arg_s, arg_e = _span(source, node.args[1])
            new_text = f"{source[obj_s:obj_e]}.append({source[arg_s:arg_e]})"
            out.append(_splice(source, node, new_text))
    return out


@_guard
def fix_tuple_missing_comma(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    tuple_vars = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Tuple) and not n.value.elts:
            for t in n.targets:
                if isinstance(t, ast.Name):
                    tuple_vars.add(t.id)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) and isinstance(n.target, ast.Name) and n.target.id in tuple_vars:
            if not isinstance(n.value, ast.Tuple):
                s, e = _span(source, n.value)
                out.append(source[:s] + "(" + source[s:e] + ",)" + source[e:])
    return out


@_guard
def fix_add_element_not_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    list_vars = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.List) and not n.value.elts:
            for t in n.targets:
                if isinstance(t, ast.Name):
                    list_vars.add(t.id)
    out = []
    for n in ast.walk(tree):
        target_name = None
        value_node = None
        if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) and isinstance(n.target, ast.Name):
            target_name = n.target.id
            value_node = n.value
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and isinstance(n.value, ast.BinOp) and isinstance(n.value.op, ast.Add):
            target_name = n.targets[0].id
            left, right = n.value.left, n.value.right
            if isinstance(left, ast.Name) and left.id == target_name:
                value_node = right
            elif isinstance(right, ast.Name) and right.id == target_name:
                value_node = left
        if target_name is None or target_name not in list_vars or value_node is None:
            continue
        if isinstance(value_node, ast.List):
            continue
        if isinstance(value_node, ast.Call) and isinstance(value_node.func, ast.Name) and value_node.func.id == "list":
            continue
        refs_target = any(isinstance(m, ast.Name) and m.id == target_name for m in ast.walk(value_node))
        if refs_target:
            continue
        s, e = _span(source, value_node)
        out.append(source[:s] + "[" + source[s:e] + "]" + source[e:])
    return out


@_guard
def fix_broken_append_statement(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        call = None
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
        elif isinstance(node, ast.AugAssign) and isinstance(node.value, ast.Call):
            call = node.value
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq) and isinstance(cmp.comparators[0], ast.Call):
                call = cmp.comparators[0]
        if call is None:
            continue
        if isinstance(call.func, ast.Attribute) and call.func.attr in ("append", "extend", "insert"):
            s, e = _span(source, node)
            cs, ce = _span(source, call)
            out.append(source[:s] + source[cs:ce] + source[e:])
    return out


@_guard
def fix_append_dot_arg(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute):
            outer = node.value
            if isinstance(outer.value, ast.Attribute) and outer.value.attr == "append":
                arg_name = outer.attr
                obj_s, obj_e = _span(source, outer.value.value)
                new_text = f"{source[obj_s:obj_e]}.append({arg_name})"
                out.append(_splice(source, node.value, new_text))
    return out


@_guard
def fix_append_subscript(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr in ("append", "count"):
            sl = _slice_value(node.slice)
            obj_s, obj_e = _span(source, node.value)
            arg_s, arg_e = _span(source, sl)
            new_text = f"{source[obj_s:obj_e]}({source[arg_s:arg_e]})"
            out.append(_splice(source, node, new_text))
    return out


@_guard
def fix_comparison_as_assignment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq) and isinstance(cmp.left, ast.Name):
                right = cmp.comparators[0]
                if isinstance(right, ast.Call):
                    continue
                ls, le = _span(source, cmp.left)
                rs, re_ = _span(source, right)
                between = source[le:rs]
                if "==" in between:
                    new_between = between.replace("==", "=", 1)
                    out.append(source[:le] + new_between + source[rs:])
    return out


@_guard
def fix_missing_call_parens(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    call_func_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_func_ids.add(id(node.func))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("reverse", "sort", "pop", "clear"):
            if id(node) in call_func_ids:
                continue
            s, e = _span(source, node)
            out.append(source[:e] + "()" + source[e:])
    return out


@_guard
def fix_return_inplace_mutator(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr in ("reverse", "sort", "append", "extend", "insert", "remove", "clear"):
                obj = call.func.value
                if isinstance(obj, ast.Name):
                    s, e = _span(source, node)
                    line_start = source.rfind("\n", 0, s) + 1
                    indent = source[line_start:s]
                    cs, ce = _span(source, call)
                    new_text = source[cs:ce] + "\n" + indent + "return " + obj.id
                    out.append(source[:s] + new_text + source[e:])
    return out


@_guard
def fix_return_wrong_var(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        acc_candidates = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend", "insert"):
                if isinstance(n.func.value, ast.Name):
                    acc_candidates.add(n.func.value.id)
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                acc_candidates.add(n.target.id)
        if len(acc_candidates) != 1:
            continue
        acc = next(iter(acc_candidates))
        for n in func.body:
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id != acc:
                out.append(_splice(source, n.value, acc))
    return out


@_guard
def fix_missing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if func.name != "remove_extras":
            continue
        has_return = any(isinstance(s, ast.Return) for s in func.body)
        if has_return:
            continue
        acc = None
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend"):
                if isinstance(n.func.value, ast.Name):
                    acc = n.func.value.id
        if acc is None:
            for n in ast.walk(func):
                if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                    acc = n.target.id
        if acc is None or not func.body:
            continue
        last = func.body[-1]
        s, e = _span(source, last)
        line_start = source.rfind("\n", 0, s) + 1
        indent = source[line_start:s]
        out.append(source[:e] + "\n" + indent + f"return {acc}" + source[e:])
    return out


@_guard
def fix_print_instead_of_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        has_return = any(isinstance(s, ast.Return) for s in ast.walk(func))
        if has_return or not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call) \
                and isinstance(last.value.func, ast.Name) and last.value.func.id == "print" and last.value.args:
            arg = last.value.args[0]
            arg_s, arg_e = _span(source, arg)
            out.append(_splice(source, last, f"return {source[arg_s:arg_e]}"))
    return out


@_guard
def fix_return_none_for_empty(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            out.append(_splice(source, node.value, "[]"))
    return out


def _builtin_names():
    return set(dir(builtins))


@_guard
def fix_typo_undefined_name(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    defined = set()
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            defined.add(n.name)
            for a in n.args.args:
                defined.add(a.arg)
        if isinstance(n, ast.Assign):
            for t in n.targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Name):
                        defined.add(sub.id)
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            defined.add(n.target.id)
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            defined.add(n.target.id)
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                imported.add(a.asname or a.name)
        if isinstance(n, ast.Import):
            for a in n.names:
                imported.add((a.asname or a.name).split(".")[0])

    known = defined | imported | _builtin_names()

    undefined_nodes = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in known:
            undefined_nodes.append(n)
    if not undefined_nodes:
        return []

    def best_match(bad, candidates):
        best, best_score = None, 0.0
        for c in candidates:
            if c == bad:
                continue
            score = difflib.SequenceMatcher(None, bad, c).ratio()
            if bad in c or c in bad:
                score = max(score, 0.8)
            if score > best_score:
                best_score, best = score, c
        return best if best_score >= 0.55 else None

    by_id = {}
    for n in undefined_nodes:
        by_id.setdefault(n.id, []).append(n)

    out = []
    for bad_name, nodes in by_id.items():
        good = best_match(bad_name, defined)
        if not good:
            continue
        spans = sorted((_span(source, n) for n in nodes), key=lambda x: x[0], reverse=True)
        candidate = source
        for s, e in spans:
            candidate = candidate[:s] + good + candidate[e:]
        out.append(candidate)
    return out


@_guard
def fix_missing_ordereddict_import(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    uses = any(isinstance(n, ast.Name) and n.id == "OrderedDict" for n in ast.walk(tree))
    if not uses:
        return []
    has_import = any(
        isinstance(n, ast.ImportFrom) and n.module == "collections" and any(a.name == "OrderedDict" for a in n.names)
        for n in ast.walk(tree)
    )
    if has_import:
        return []
    return ["from collections import OrderedDict\n\n" + source]


@_guard
def fix_wrap_fromkeys_in_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    wrapped_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "list":
            for a in node.args:
                wrapped_ids.add(id(a))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "fromkeys":
            if id(node) in wrapped_ids:
                continue
            s, e = _span(source, node)
            out.append(source[:s] + "list(" + source[s:e] + ")" + source[e:])
    return out


@_guard
def fix_set_to_ordereddict(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "set" and len(node.args) == 1:
            arg_s, arg_e = _span(source, node.args[0])
            replacement = f"OrderedDict.fromkeys({source[arg_s:arg_e]})"
            out.append(_splice(source, node, replacement))
    return out


@_guard
def fix_copy_var_confusion(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        copy_var = None
        for n in func.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                v = n.value
                if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "copy" \
                        and isinstance(v.func.value, ast.Name) and v.func.value.id == param:
                    copy_var = n.targets[0].id
        if not copy_var:
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == copy_var:
                occ = [m for m in ast.walk(node) if isinstance(m, ast.Name) and m.id == param and isinstance(m.ctx, ast.Load)]
                if not occ:
                    continue
                spans = sorted((_span(source, m) for m in occ), key=lambda x: x[0], reverse=True)
                candidate = source
                for s, e in spans:
                    candidate = candidate[:s] + copy_var + candidate[e:]
                out.append(candidate)
    return out


@_guard
def fix_flag_reset_each_iteration(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcs(tree):
        for node in ast.walk(func):
            if not isinstance(node, ast.For) or not node.body:
                continue
            flags_false = set()
            for n in ast.walk(node):
                if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                        and isinstance(n.value, ast.Constant) and n.value.value is False:
                    flags_false.add(n.targets[0].id)
            for flag in flags_false:
                resets_inside = any(
                    isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id == flag and isinstance(n.value, ast.Constant) and n.value.value is True
                    for n in ast.walk(node)
                )
                if resets_inside:
                    continue
                first = node.body[0]
                s, e = _span(source, first)
                line_start = source.rfind("\n", 0, s) + 1
                indent = source[line_start:s]
                out.append(source[:s] + f"{flag} = True\n{indent}" + source[s:])
    return out


@_guard
def fix_range_len_minus_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                if isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name) and arg.left.func.id == "len":
                    left_s, left_e = _span(source, arg.left)
                    out.append(_splice(source, node, f"range({source[left_s:left_e]})"))
    return out


@_guard
def fix_in_should_be_not_in(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 \
                and isinstance(node.test.ops[0], ast.In) and not node.orelse:
            cont = node.test.comparators[0]
            elem = node.test.left
            if isinstance(cont, ast.Name):
                appends = any(
                    isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("append", "extend")
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == cont.id
                    for n in ast.walk(node)
                )
                if appends:
                    ls, le = _span(source, elem)
                    rs, re_ = _span(source, cont)
                    between = source[le:rs]
                    if " in " in between and " not in " not in between:
                        new_between = between.replace(" in ", " not in ", 1)
                        out.append(source[:le] + new_between + source[rs:])
    return out


@_guard
def fix_noteq_should_be_notin(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    list_vars = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.List) and not n.value.elts:
            for t in n.targets:
                if isinstance(t, ast.Name):
                    list_vars.add(t.id)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotEq):
            left, right = node.left, node.comparators[0]
            acc, elem = None, None
            if isinstance(right, ast.Name) and right.id in list_vars:
                acc, elem = right, left
            elif isinstance(left, ast.Name) and left.id in list_vars:
                acc, elem = left, right
            if acc is None:
                continue
            es, ee = _span(source, elem)
            accs, acce = _span(source, acc)
            new_text = f"{source[es:ee]} not in {source[accs:acce]}"
            out.append(_splice(source, node, new_text))
    return out


@_guard
def fix_missing_else_before_increment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.While, ast.For)):
            body = node.body
            for idx in range(len(body) - 1):
                stmt = body[idx]
                nxt = body[idx + 1]
                if not (isinstance(stmt, ast.If) and not stmt.orelse):
                    continue
                is_incr = False
                if isinstance(nxt, ast.AugAssign) and isinstance(nxt.op, ast.Add):
                    is_incr = True
                if isinstance(nxt, ast.Assign) and len(nxt.targets) == 1 and isinstance(nxt.targets[0], ast.Name):
                    v = nxt.value
                    if isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add) and isinstance(v.left, ast.Name) \
                            and v.left.id == nxt.targets[0].id:
                        is_incr = True
                if not is_incr:
                    continue
                mutates = any(
                    isinstance(s, ast.Assign) or isinstance(s, ast.Delete)
                    or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call))
                    for s in ast.walk(stmt)
                )
                if not mutates:
                    continue
                if_s, if_e = _span(source, stmt)
                inc_s, inc_e = _span(source, nxt)
                line_start = source.rfind("\n", 0, if_s) + 1
                indent = source[line_start:if_s]
                inc_text = source[inc_s:inc_e]
                new_if_text = source[if_s:if_e] + "\n" + indent + "else:\n" + indent + "    " + inc_text
                out.append(source[:if_s] + new_if_text + source[inc_e:])
    return out


# --------------------------------------------------------------------------
# Fixer
# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="for_over_builtin_list", apply=fix_for_over_builtin_list,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="broken_for_header", apply=fix_broken_for_header,
                 symptoms=("wrong", "err:NameError", "err:TypeError")),
            Rule(name="membership_wrong_container", apply=fix_membership_wrong_container,
                 symptoms=("wrong",)),
            Rule(name="count_container_rename", apply=fix_count_container_rename,
                 symptoms=("wrong",)),
            Rule(name="count_eq_one_to_zero", apply=fix_count_eq_one_to_zero,
                 symptoms=("wrong",)),
            Rule(name="append_wrong_container", apply=fix_append_wrong_container,
                 symptoms=("wrong",)),
            Rule(name="extend_scalar_to_append", apply=fix_extend_scalar_to_append,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="list_call_wrap_scalar", apply=fix_list_call_wrap_scalar,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="insert_to_append", apply=fix_insert_to_append,
                 symptoms=("wrong",)),
            Rule(name="tuple_missing_comma", apply=fix_tuple_missing_comma,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="add_element_not_list", apply=fix_add_element_not_list,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="broken_append_statement", apply=fix_broken_append_statement,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="append_dot_arg", apply=fix_append_dot_arg,
                 symptoms=("err:AttributeError", "wrong")),
            Rule(name="append_subscript", apply=fix_append_subscript,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="comparison_as_assignment", apply=fix_comparison_as_assignment,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="missing_call_parens", apply=fix_missing_call_parens,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="return_inplace_mutator", apply=fix_return_inplace_mutator,
                 symptoms=("wrong",)),
            Rule(name="return_wrong_var", apply=fix_return_wrong_var,
                 symptoms=("wrong",)),
            Rule(name="missing_return", apply=fix_missing_return,
                 symptoms=("wrong",)),
            Rule(name="print_instead_of_return", apply=fix_print_instead_of_return,
                 symptoms=("wrong",)),
            Rule(name="return_none_for_empty", apply=fix_return_none_for_empty,
                 symptoms=("wrong",)),
            Rule(name="typo_undefined_name", apply=fix_typo_undefined_name,
                 symptoms=("err:NameError",)),
            Rule(name="missing_ordereddict_import", apply=fix_missing_ordereddict_import,
                 symptoms=("err:NameError",)),
            Rule(name="wrap_fromkeys_in_list", apply=fix_wrap_fromkeys_in_list,
                 symptoms=("wrong",)),
            Rule(name="set_to_ordereddict", apply=fix_set_to_ordereddict,
                 symptoms=("wrong",)),
            Rule(name="copy_var_confusion", apply=fix_copy_var_confusion,
                 symptoms=("wrong",)),
            Rule(name="flag_reset_each_iteration", apply=fix_flag_reset_each_iteration,
                 symptoms=("wrong",)),
            Rule(name="range_len_minus_one", apply=fix_range_len_minus_one,
                 symptoms=("wrong",)),
            Rule(name="in_should_be_not_in", apply=fix_in_should_be_not_in,
                 symptoms=("wrong",)),
            Rule(name="noteq_should_be_notin", apply=fix_noteq_should_be_notin,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="missing_else_before_increment", apply=fix_missing_else_before_increment,
                 symptoms=("wrong",)),
        ]