"""
Repair module for the "Sorting Tuples" (sort_age) assignment.

Each rule performs a small, localized, AST-located edit (a span splice on
the original source text) that targets one recurring misconception seen in
student submissions. Rules are pure candidate generators: they never raise,
never return the unchanged source, and never rewrite whole functions.
"""

import ast
import builtins

from src.core.repair import Rule

BUILTIN_NAMES = set(dir(builtins))


# --------------------------------------------------------------------------
# generic helpers
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


def _line_span(source, node):
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    start = starts[node.lineno - 1]
    end_idx = node.end_lineno - 1
    end = starts[end_idx] + len(lines[end_idx])
    return start, end


def _splice_many(source, nodes_and_texts):
    spans = [(_span(source, n), t) for n, t in nodes_and_texts]
    spans.sort(key=lambda x: x[0][0], reverse=True)
    for (s, e), t in spans:
        source = source[:s] + t + source[e:]
    return source


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _funcdefs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _set_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node


def _slice_value(sl):
    if isinstance(sl, ast.Index):  # py<3.9 compatibility
        return sl.value
    return sl


def _in_body(p, n):
    for stmt in p.body:
        for d in ast.walk(stmt):
            if d is n:
                return True
    return False


def _bound_names(func, module_funcnames):
    bound = set(module_funcnames)
    bound.add(func.name)
    for a in func.args.args:
        bound.add(a.arg)
    for n in ast.walk(func):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            bound.add(n.id)
        if isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        if isinstance(n, ast.FunctionDef) and n is not func:
            bound.add(n.name)
    return bound


def _undefined_loads(func, bound):
    result = {}
    for n in ast.walk(func):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            if n.id in bound or n.id in BUILTIN_NAMES:
                continue
            result.setdefault(n.id, []).append(n)
    return result


def _safe(fn):
    def wrapper(source):
        try:
            results = fn(source)
        except Exception:
            return []
        out = []
        seen = set()
        for r in results:
            if r and r != source and r not in seen:
                seen.add(r)
                out.append(r)
        return out
    return wrapper


# --------------------------------------------------------------------------
# Rule: rename an undefined identifier to a plausible in-scope variable
# --------------------------------------------------------------------------

def fix_undefined_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    _set_parents(tree)
    module_funcnames = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for func in _funcdefs(tree):
        bound = _bound_names(func, module_funcnames)
        undef = _undefined_loads(func, bound)
        if not undef:
            continue

        accumulators = []
        bestvars = []
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                tgt = n.targets[0].id
                val = n.value
                if isinstance(val, (ast.List, ast.Tuple)) and len(val.elts) == 0:
                    accumulators.append(tgt)
                if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name):
                    sl = _slice_value(val.slice)
                    if isinstance(sl, ast.Constant) and sl.value == 0:
                        bestvars.append(tgt)

        param_name = func.args.args[0].arg if func.args.args else None

        for nid, nodes in undef.items():
            candidates = []
            for n in nodes:
                p = getattr(n, '_parent', None)
                while p is not None and p is not func:
                    if isinstance(p, ast.For) and isinstance(p.target, ast.Name) and _in_body(p, n):
                        candidates.append(p.target.id)
                        break
                    p = getattr(p, '_parent', None)
            if param_name:
                candidates.append(param_name)
            candidates.extend(accumulators)
            candidates.extend(bestvars)

            seen = set()
            for cand in candidates:
                if cand == nid or cand in seen:
                    continue
                seen.add(cand)
                new_src = _splice_many(source, [(n, cand) for n in nodes])
                out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule: insert a missing `acc = []` when an accumulator is never initialized
# --------------------------------------------------------------------------

def insert_missing_accumulator_init(source):
    tree = _parse(source)
    if tree is None:
        return []
    module_funcnames = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    out = []
    for func in _funcdefs(tree):
        bound = _bound_names(func, module_funcnames)
        candidates = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'append':
                val = n.func.value
                if isinstance(val, ast.Name) and val.id not in bound and val.id not in BUILTIN_NAMES:
                    candidates.add(val.id)
        if not candidates or not func.body:
            continue
        first_stmt = func.body[0]
        indent = ' ' * first_stmt.col_offset
        insert_s, _ = _span(source, first_stmt)
        for name in candidates:
            new_line = f"{name} = []\n{indent}"
            out.append(source[:insert_s] + new_line + source[insert_s:])
    return out


# --------------------------------------------------------------------------
# Rule: min()/max() confusion
# --------------------------------------------------------------------------

def swap_min_max(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for src_name, dst_name in (('min', 'max'), ('max', 'min')):
        call_funcs = [n.func for n in ast.walk(tree)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == src_name]
        if not call_funcs:
            continue
        out.append(_splice_many(source, [(n, dst_name) for n in call_funcs]))
    return out


# --------------------------------------------------------------------------
# Rule: comparing a list parameter to () instead of []
# --------------------------------------------------------------------------

def empty_tuple_to_list(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            for side in (n.left, n.comparators[0]):
                if isinstance(side, ast.Tuple) and len(side.elts) == 0:
                    out.append(_splice(source, side, '[]'))
    return out


# --------------------------------------------------------------------------
# Rule: `return X.reverse` (attribute, never called) -> `return X`
# --------------------------------------------------------------------------

def fix_bare_reverse_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Attribute) and n.value.attr == 'reverse':
            base = n.value.value
            bs, be = _span(source, base)
            base_text = source[bs:be]
            ns, ne = _span(source, n.value)
            out.append(source[:ns] + base_text + source[ne:])
    return out


# --------------------------------------------------------------------------
# Rule: `for x in lst:` with `lst.remove(...)` inside -> `while lst:`
# --------------------------------------------------------------------------

def for_to_while_mutating(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and isinstance(n.iter, ast.Name):
            iter_name = n.iter.id
            loopvar = n.target.id
            used = False
            for stmt in n.body:
                for x in ast.walk(stmt):
                    if isinstance(x, ast.Name) and x.id == loopvar:
                        used = True
            if used:
                continue
            has_remove = False
            for stmt in n.body:
                for x in ast.walk(stmt):
                    if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == 'remove' \
                       and isinstance(x.func.value, ast.Name) and x.func.value.id == iter_name:
                        has_remove = True
            if not has_remove:
                continue
            start_s, _ = _span(source, n)
            iter_s, iter_e = _span(source, n.iter)
            try:
                idx = source.index(':', iter_e)
            except ValueError:
                continue
            header_new = "while " + source[iter_s:iter_e] + ":"
            out.append(source[:start_s] + header_new + source[idx + 1:])
    return out


# --------------------------------------------------------------------------
# Rule: comparing full tuple instead of its age -> add missing [1]
# --------------------------------------------------------------------------

def add_missing_subscript(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        tuple_vars = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                val = n.value
                if isinstance(val, ast.Subscript):
                    sl = _slice_value(val.slice)
                    if isinstance(sl, ast.Constant) and sl.value == 0:
                        tuple_vars.add(n.targets[0].id)
        for n in ast.walk(func):
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                left, right = n.left, n.comparators[0]
                for side, other in ((left, right), (right, left)):
                    if isinstance(side, ast.Name) and side.id in tuple_vars and isinstance(other, ast.Subscript):
                        osl = _slice_value(other.slice)
                        if isinstance(osl, ast.Constant) and osl.value == 1:
                            out.append(_splice(source, side, side.id + "[1]"))
    return out


# --------------------------------------------------------------------------
# Rule: function never returns -> append `return <accumulator>`
# --------------------------------------------------------------------------

def add_missing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        if not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, ast.Return):
            continue
        acc_names = []
        for n in ast.walk(func):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'append':
                if isinstance(n.func.value, ast.Name) and n.func.value.id not in acc_names:
                    acc_names.append(n.func.value.id)
        candidates = list(acc_names)
        if func.args.args:
            candidates.append(func.args.args[0].arg)
        if not candidates:
            continue
        indent = ' ' * last.col_offset
        _, end_off = _line_span(source, last)
        seen = set()
        for cand in candidates:
            if cand in seen:
                continue
            seen.add(cand)
            new_src = source[:end_off] + indent + f"return {cand}\n" + source[end_off:]
            out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule: a trailing no-arg call at the end of a loop body that belongs after it
# --------------------------------------------------------------------------

def dedent_trailing_loop_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.While, ast.For)) and n.body:
            last = n.body[-1]
            if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call) \
               and isinstance(last.value.func, ast.Attribute) and not last.value.args \
               and isinstance(last.value.func.value, ast.Name):
                name = last.value.func.value.id
                used_append = False
                for stmt in n.body[:-1]:
                    for x in ast.walk(stmt):
                        if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) \
                           and x.func.attr == 'append' and isinstance(x.func.value, ast.Name) \
                           and x.func.value.id == name:
                            used_append = True
                if not used_append:
                    continue
                line_s, line_e = _line_span(source, last)
                content = source[line_s:line_e].lstrip(' ')
                new_line = ' ' * n.col_offset + content
                out.append(source[:line_s] + new_line + source[line_e:])
    return out


# --------------------------------------------------------------------------
# Rule: `for x in it: if cond: x = best` should be `best = x`
# --------------------------------------------------------------------------

def swap_loopvar_assignment(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            loopvar = n.target.id
            for stmt in ast.walk(n):
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                   and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == loopvar \
                   and isinstance(stmt.value, ast.Name) and stmt.value.id != loopvar:
                    other = stmt.value.id
                    out.append(_splice(source, stmt, f"{other} = {loopvar}"))
    return out


# --------------------------------------------------------------------------
# Rule: `acc.append(lst.pop(i))` with stray index -> append(best); remove(best)
# --------------------------------------------------------------------------

def fix_pop_wrong_index(source):
    tree = _parse(source)
    if tree is None:
        return []
    _set_parents(tree)
    out = []
    for func in _funcdefs(tree):
        bestvars = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                val = n.value
                if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name):
                    sl = _slice_value(val.slice)
                    if isinstance(sl, ast.Constant) and sl.value == 0:
                        bestvars.add(n.targets[0].id)
        for n in ast.walk(func):
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) \
               and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == 'append' \
               and isinstance(n.value.func.value, ast.Name) and len(n.value.args) == 1 \
               and isinstance(n.value.args[0], ast.Call):
                acc_name = n.value.func.value.id
                inner = n.value.args[0]
                if isinstance(inner.func, ast.Attribute) and inner.func.attr == 'pop' \
                   and isinstance(inner.func.value, ast.Name):
                    iter_name = inner.func.value.id
                    p = getattr(n, '_parent', None)
                    block = None
                    while p is not None:
                        if isinstance(p, (ast.While, ast.For)):
                            block = p
                            break
                        p = getattr(p, '_parent', None)
                    if block is None:
                        continue
                    found = None
                    for s2 in ast.walk(block):
                        if isinstance(s2, ast.Name) and s2.id in bestvars:
                            found = s2.id
                    if not found:
                        continue
                    stmt_s, stmt_e = _line_span(source, n)
                    indent = ' ' * n.col_offset
                    new_block = f"{indent}{acc_name}.append({found})\n{indent}{iter_name}.remove({found})\n"
                    out.append(source[:stmt_s] + new_block + source[stmt_e:])
    return out


# --------------------------------------------------------------------------
# Rule: `list_var(max)` should be `max(list_var)`
# --------------------------------------------------------------------------

def fix_reversed_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and len(n.args) == 1:
            arg = n.args[0]
            if isinstance(arg, ast.Name) and arg.id in ('max', 'min') and n.func.id not in ('max', 'min'):
                out.append(_splice(source, n, f"{arg.id}({n.func.id})"))
    return out


# --------------------------------------------------------------------------
# Rule: missing empty-list guard before indexing `param[0]`
# --------------------------------------------------------------------------

def guard_empty_list(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _funcdefs(tree):
        if not func.args.args or not func.body:
            continue
        param = func.args.args[0].arg
        first = func.body[0]
        if isinstance(first, ast.If):
            continue
        found = False
        for n in ast.walk(first):
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == param:
                sl = _slice_value(n.slice)
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    found = True
        if not found:
            continue
        indent = ' ' * first.col_offset
        insert_s, _ = _span(source, first)
        guard = f"if not {param}:\n{indent}    return []\n{indent}"
        out.append(source[:insert_s] + guard + source[insert_s:])
    return out


# --------------------------------------------------------------------------
# Rule: flip a strict comparison between two subscripted operands
# --------------------------------------------------------------------------

def flip_subscript_comparison(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    flip_map = {ast.Lt: (ast.Gt, '>'), ast.Gt: (ast.Lt, '<'),
                ast.LtE: (ast.GtE, '>='), ast.GtE: (ast.LtE, '<=')}
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in flip_map:
            left, right = n.left, n.comparators[0]
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Subscript):
                _, op_text = flip_map[type(n.ops[0])]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + f" {op_text} " + source[rs:re_]
                out.append(_splice(source, n, new_cmp))
    return out


# --------------------------------------------------------------------------
# Rule: off-by-one insertion index in manual insertion sort
# --------------------------------------------------------------------------

def fix_insert_offset(source):
    tree = _parse(source)
    if tree is None:
        return []
    _set_parents(tree)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'insert' \
           and len(n.args) == 2 and isinstance(n.args[0], ast.Name):
            idx_arg = n.args[0]
            p = getattr(n, '_parent', None)
            while p is not None and not isinstance(p, ast.If):
                p = getattr(p, '_parent', None)
            if p is None:
                continue
            found_plus1 = False
            for sub in ast.walk(p.test):
                if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.BinOp):
                    bo = sub.slice
                    if isinstance(bo.op, ast.Add) and isinstance(bo.right, ast.Constant) \
                       and bo.right.value == 1 and isinstance(bo.left, ast.Name) and bo.left.id == idx_arg.id:
                        found_plus1 = True
            if found_plus1:
                out.append(_splice(source, idx_arg, f"{idx_arg.id} + 1"))
    return out


# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="fix_undefined_name_rename",
                 apply=_safe(fix_undefined_name),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="insert_missing_accumulator_init",
                 apply=_safe(insert_missing_accumulator_init),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="swap_min_max_builtin",
                 apply=_safe(swap_min_max),
                 symptoms=("wrong",)),
            Rule(name="empty_tuple_vs_list_compare",
                 apply=_safe(empty_tuple_to_list),
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="drop_bare_reverse_in_return",
                 apply=_safe(fix_bare_reverse_return),
                 symptoms=("wrong",)),
            Rule(name="for_to_while_mutating_iterable",
                 apply=_safe(for_to_while_mutating),
                 symptoms=("wrong",)),
            Rule(name="add_missing_tuple_subscript_in_compare",
                 apply=_safe(add_missing_subscript),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="add_missing_return_statement",
                 apply=_safe(add_missing_return),
                 symptoms=("wrong",)),
            Rule(name="dedent_trailing_loop_call",
                 apply=_safe(dedent_trailing_loop_call),
                 symptoms=("wrong",)),
            Rule(name="swap_loopvar_best_assignment",
                 apply=_safe(swap_loopvar_assignment),
                 symptoms=("wrong",)),
            Rule(name="fix_pop_wrong_index_append",
                 apply=_safe(fix_pop_wrong_index),
                 symptoms=("wrong", "err:IndexError", "err:ValueError")),
            Rule(name="fix_reversed_call_args",
                 apply=_safe(fix_reversed_call),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="guard_empty_list_input",
                 apply=_safe(guard_empty_list),
                 symptoms=("err:IndexError",)),
            Rule(name="flip_subscript_comparison",
                 apply=_safe(flip_subscript_comparison),
                 symptoms=("wrong",)),
            Rule(name="fix_insert_offset",
                 apply=_safe(fix_insert_offset),
                 symptoms=("wrong",)),
        ]