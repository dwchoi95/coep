"""
Repair module for the "Sorting Tuples" (sort_age) assignment.

Each rule performs a small, local, AST-span-based edit targeting one
recurring misconception observed in buggy student submissions.
"""

import ast
import builtins
from src.core.repair import Rule


# ----------------------------------------------------------------------
# helpers
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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _base_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.value.id
    return None


def _op_str(op):
    return {
        ast.Lt: " < ", ast.LtE: " <= ", ast.Gt: " > ", ast.GtE: " >= ",
        ast.Eq: " == ", ast.NotEq: " != ",
    }.get(type(op), " < ")


def _functions(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _assigned_names(func):
    names = set()
    for n in ast.walk(func):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.add(n.id)
        if isinstance(n, ast.arg):
            names.add(n.arg)
    names.add(func.name)
    return names


# ----------------------------------------------------------------------
# Rule 1: comparator picks minimum but algorithm removes-and-appends once
# per pass (selects the youngest instead of the oldest).
# ----------------------------------------------------------------------

def flip_selection_comparator(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        loopvar = node.target.id
        for if_node in ast.walk(node):
            if not (isinstance(if_node, ast.If) and isinstance(if_node.test, ast.Compare)
                    and len(if_node.test.ops) == 1):
                continue
            op = if_node.test.ops[0]
            if not isinstance(op, (ast.Lt, ast.LtE)):
                continue
            left, right = if_node.test.left, if_node.test.comparators[0]
            lb, rb = _base_name(left), _base_name(right)
            if lb is None or rb is None or lb == rb:
                continue
            if len(if_node.body) != 1 or not isinstance(if_node.body[0], ast.Assign):
                continue
            assign = if_node.body[0]
            if (len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name)
                    or not isinstance(assign.value, ast.Name)):
                continue
            t, v = assign.targets[0].id, assign.value.id
            if lb == loopvar and rb == t and v == loopvar:
                flip = " >= " if isinstance(op, ast.LtE) else " > "
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + flip + source[rs:re_]
                new_src = _splice(source, if_node.test, new_cmp)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 2: tracker update assignment written backwards
# (`loopvar = tracker` instead of `tracker = loopvar`)
# ----------------------------------------------------------------------

def swap_reversed_tracker_assignment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        loopvar = node.target.id
        for if_node in ast.walk(node):
            if not isinstance(if_node, ast.If):
                continue
            if len(if_node.body) != 1 or not isinstance(if_node.body[0], ast.Assign):
                continue
            assign = if_node.body[0]
            if (len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name)
                    or not isinstance(assign.value, ast.Name)):
                continue
            t, v = assign.targets[0].id, assign.value.id
            if t == loopvar and v != loopvar:
                new_text = f"{v} = {t}"
                new_src = _splice(source, assign, new_text)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 3: tracker assignment references an undefined name that should
# have been the for-loop variable (typo).
# ----------------------------------------------------------------------

def fix_undefined_rhs_in_tracker_assign(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        assigned = _assigned_names(func)
        for node in ast.walk(func):
            if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
                continue
            loopvar = node.target.id
            for assign in ast.walk(node):
                if not isinstance(assign, ast.Assign):
                    continue
                if (len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name)
                        or not isinstance(assign.value, ast.Name)):
                    continue
                v = assign.value.id
                if v == loopvar:
                    continue
                if v in assigned or v in dir(builtins):
                    continue
                new_src = _splice(source, assign.value, loopvar)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 4: `return X` where X is undefined but an accumulator exists.
# ----------------------------------------------------------------------

def fix_undefined_return_name(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        assigned = _assigned_names(func)
        for node in ast.walk(func):
            if not (isinstance(node, ast.Return) and isinstance(node.value, ast.Name)):
                continue
            name = node.value.id
            if name in assigned:
                continue
            candidates = []
            for m in ast.walk(func):
                if (isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute)
                        and m.func.attr == "append" and isinstance(m.func.value, ast.Name)):
                    candidates.append(m.func.value.id)
                if (isinstance(m, ast.AugAssign) and isinstance(m.target, ast.Name)
                        and isinstance(m.op, ast.Add)):
                    candidates.append(m.target.id)
            candidates = list(dict.fromkeys(candidates))
            if len(candidates) == 1 and candidates[0] != name:
                new_src = _splice(source, node.value, candidates[0])
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 5: a single undefined identifier used throughout (append/return)
# while exactly one declared-but-unused empty-list accumulator exists.
# ----------------------------------------------------------------------

def fix_undefined_accumulator_name(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    builtin_names = set(dir(builtins))
    for func in _functions(tree):
        assigned = _assigned_names(func)
        loads = [n for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)]
        undefined = sorted(set(n.id for n in loads
                                if n.id not in assigned and n.id not in builtin_names))
        if len(undefined) != 1:
            continue
        bad = undefined[0]
        declared_lists = []
        for stmt in func.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.List) and len(stmt.value.elts) == 0):
                declared_lists.append(stmt.targets[0].id)
        if len(declared_lists) != 1:
            continue
        good = declared_lists[0]
        if good == bad:
            continue
        occs = sorted([n for n in loads if n.id == bad],
                       key=lambda n: _span(source, n)[0], reverse=True)
        new_source = source
        for occ in occs:
            s, e = _span(source, occ)
            new_source = new_source[:s] + good + new_source[e:]
        if new_source != source:
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 6: wrong/undefined container-variable name in `.remove/.append/pop`
# or subscript (e.g. `list[0]` or `a.remove(x)` when the parameter is `lst`).
# ----------------------------------------------------------------------

def fix_wrong_container_name(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    builtin_names = set(dir(builtins))
    for func in _functions(tree):
        params = [a.arg for a in func.args.args]
        if len(params) != 1:
            continue
        param = params[0]
        assigned = _assigned_names(func)
        for n in ast.walk(func):
            base = None
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("remove", "append", "pop")
                    and isinstance(n.func.value, ast.Name)):
                base = n.func.value
            elif isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
                base = n.value
            if base is None:
                continue
            name = base.id
            if name == param:
                continue
            if name in assigned:
                continue
            if name in builtin_names or name not in assigned:
                new_src = _splice(source, base, param)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 7/8: trailing `print(x)` should be `return x` (or the accumulator).
# ----------------------------------------------------------------------

def _last_stmt(func):
    return func.body[-1] if func.body else None


def trailing_print_to_return_same_arg(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        stmt = _last_stmt(func)
        if not isinstance(stmt, ast.Expr):
            continue
        call = stmt.value
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "print" and len(call.args) == 1
                and isinstance(call.args[0], ast.Name)):
            new_text = f"return {call.args[0].id}"
            new_src = _splice(source, stmt, new_text)
            if new_src != source:
                out.append(new_src)
    return out


def trailing_print_to_return_accumulator(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        stmt = _last_stmt(func)
        if not isinstance(stmt, ast.Expr):
            continue
        call = stmt.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "print" and len(call.args) == 1):
            continue
        candidates = []
        for m in ast.walk(func):
            if (isinstance(m, ast.Call) and isinstance(m.func, ast.Attribute)
                    and m.func.attr == "append" and isinstance(m.func.value, ast.Name)):
                candidates.append(m.func.value.id)
        candidates = list(dict.fromkeys(candidates))
        if len(candidates) == 1:
            new_text = f"return {candidates[0]}"
            new_src = _splice(source, stmt, new_text)
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 9: `return` left indented one level too deep (inside the while
# loop) causing it to fire after the first iteration.
# ----------------------------------------------------------------------

def dedent_trailing_return_from_while(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and node.body and isinstance(node.body[-1], ast.Return):
            ret = node.body[-1]
            rs, re_ = _span(source, ret)
            line_start = source.rfind("\n", 0, rs) + 1
            line_end = source.find("\n", re_)
            line_end = line_end + 1 if line_end != -1 else len(source)
            ret_text = source[rs:re_]
            removed = source[:line_start] + source[line_end:]
            indent = " " * node.col_offset
            insertion = indent + ret_text + "\n"
            new_src = removed[:line_start] + insertion + removed[line_start:]
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 10: a statement right after a while-loop duplicates the loop's
# final statement (stray extra append/remove executed once more).
# ----------------------------------------------------------------------

def remove_duplicate_trailing_stmt(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        body = func.body
        for i, stmt in enumerate(body):
            if not (isinstance(stmt, ast.While) and stmt.body):
                continue
            last_inner = stmt.body[-1]
            if i + 1 >= len(body):
                continue
            nxt = body[i + 1]
            if isinstance(nxt, ast.Return):
                continue
            if ast.dump(nxt) == ast.dump(last_inner):
                s, e = _span(source, nxt)
                line_start = source.rfind("\n", 0, s) + 1
                line_end = source.find("\n", e)
                line_end = line_end + 1 if line_end != -1 else len(source)
                new_src = source[:line_start] + source[line_end:]
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 11: `lst += item` where item should be a singleton tuple.
# ----------------------------------------------------------------------

def fix_missing_singleton_tuple(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                and isinstance(node.value, ast.Name)):
            new_text = f"({node.value.id},)"
            new_src = _splice(source, node.value, new_text)
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 12: `x = x.append(y)` (append returns None, discarding the list).
# ----------------------------------------------------------------------

def fix_append_reassignment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        tgt = node.targets[0].id
        val = node.value
        if (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                and val.func.attr == "append" and isinstance(val.func.value, ast.Name)
                and val.func.value.id == tgt):
            s, e = _span(source, val)
            call_text = source[s:e]
            new_src = _splice(source, node, call_text)
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 13: index-shuffling bubble loop forgets to reset the index after
# moving an element.
# ----------------------------------------------------------------------

def fix_missing_index_reset(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        for if_node in ast.walk(node):
            if not isinstance(if_node, ast.If):
                continue
            body = if_node.body
            has_extend = any(
                isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == "extend"
                for s in body)
            has_del_or_pop = any(
                isinstance(s, ast.Delete) or
                (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                 and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == "pop")
                for s in body)
            if not (has_extend and has_del_or_pop):
                continue
            idxname = None
            for s in (if_node.orelse or []):
                if isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name):
                    idxname = s.target.id
            if idxname is None:
                continue
            already_reset = any(
                isinstance(s, ast.Assign) and len(s.targets) == 1
                and isinstance(s.targets[0], ast.Name) and s.targets[0].id == idxname
                for s in body)
            if already_reset:
                continue
            last_stmt = body[-1]
            _, e = _span(source, last_stmt)
            indent = " " * last_stmt.col_offset
            new_src = source[:e] + "\n" + indent + f"{idxname} = 0" + source[e:]
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 14: `lst.pop(lst[i])` should be `del lst[i]` (confuses pop's
# index argument with an element lookup).
# ----------------------------------------------------------------------

def fix_pop_arg_misuse(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "pop" and len(node.args) == 1):
            continue
        arg = node.args[0]
        base = node.func.value
        if (isinstance(arg, ast.Subscript) and isinstance(base, ast.Name)
                and isinstance(arg.value, ast.Name) and arg.value.id == base.id):
            s, e = _span(source, arg)
            replacement = f"del {source[s:e]}"
            new_src = _splice(source, node, replacement)
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 15: fake swap `a[i] = a[j]; a[j] = a[i]` that loses data (needs a
# simultaneous tuple swap).
# ----------------------------------------------------------------------

def fix_fake_swap(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            if not (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)
                    and len(s1.targets) == 1 and len(s2.targets) == 1):
                continue
            t1, v1 = s1.targets[0], s1.value
            t2, v2 = s2.targets[0], s2.value
            if (ast.dump(t1) == ast.dump(v2) and ast.dump(t2) == ast.dump(v1)
                    and ast.dump(t1) != ast.dump(t2)):
                s_, _ = _span(source, s1)
                _, e_ = _span(source, s2)
                t1s, t1e = _span(source, t1)
                t2s, t2e = _span(source, t2)
                t1_text, t2_text = source[t1s:t1e], source[t2s:t2e]
                new_text = f"{t1_text}, {t2_text} = {t2_text}, {t1_text}"
                new_src = source[:s_] + new_text + source[e_:]
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 16: off-by-one `range(a, len(lst) + 1)` causing IndexError.
# ----------------------------------------------------------------------

def fix_range_off_by_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "range" and len(node.args) == 2):
            continue
        second = node.args[1]
        if (isinstance(second, ast.BinOp) and isinstance(second.op, ast.Add)
                and isinstance(second.right, ast.Constant) and second.right.value == 1
                and isinstance(second.left, ast.Call) and isinstance(second.left.func, ast.Name)
                and second.left.func.id == "len"):
            s, e = _span(source, second.left)
            new_src = _splice(source, second, source[s:e])
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 17: comparing whole tuple-like names without indexing into [1].
# ----------------------------------------------------------------------

def add_missing_subscript(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        loopvar = node.target.id
        for cmp in ast.walk(node):
            if not (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1):
                continue
            left, right = cmp.left, cmp.comparators[0]
            if (isinstance(left, ast.Name) and isinstance(right, ast.Name)
                    and left.id == loopvar and right.id != loopvar):
                new_text = f"{left.id}[1]{_op_str(cmp.ops[0])}{right.id}[1]"
                new_src = _splice(source, cmp, new_text)
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 18: `for x in lst:` used purely as a repeat-counter while the
# loop body self-mutates `lst` with `.remove(...)`; should be `while lst:`
# ----------------------------------------------------------------------

def fix_for_as_while(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                and isinstance(node.iter, ast.Name)):
            continue
        var = node.target.id
        lst_name = node.iter.id
        used = any(isinstance(n, ast.Name) and n.id == var and n is not node.target
                   for n in ast.walk(node))
        removes = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "remove" and isinstance(n.func.value, ast.Name)
            and n.func.value.id == lst_name
            for n in ast.walk(node))
        if used or not removes:
            continue
        start = _span(source, node)[0]
        iter_end = _span(source, node.iter)[1]
        try:
            colon_idx = source.index(":", iter_end)
        except ValueError:
            continue
        new_header = f"while {lst_name}:"
        new_src = source[:start] + new_header + source[colon_idx + 1:]
        if new_src != source:
            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 19: recursive function with no base case for the empty list.
# ----------------------------------------------------------------------

def add_missing_base_case(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        calls_self = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == func.name
            for n in ast.walk(func))
        if not calls_self:
            continue
        has_base_case = any(isinstance(stmt, ast.If) for stmt in func.body[:2])
        if has_base_case or not func.body:
            continue
        first_stmt = func.body[0]
        s, _ = _span(source, first_stmt)
        indent = " " * first_stmt.col_offset
        insertion = f"if not {param}:\n{indent}    return []\n{indent}"
        new_src = source[:s] + insertion + source[s:]
        if new_src != source:
            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 20: recursive selection-sort that never removes the chosen
# element before recursing (`sort_age(lst[1:])` / `sort_age(lst.remove(h))`).
# ----------------------------------------------------------------------

def fix_recursive_remove(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        fname = func.name
        for node in ast.walk(func):
            if not (isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp)
                    and isinstance(node.value.op, ast.Add)):
                continue
            right = node.value.right
            left = node.value.left
            if not (isinstance(right, ast.Call) and isinstance(right.func, ast.Name)
                    and right.func.id == fname and len(right.args) == 1):
                continue
            arg = right.args[0]
            base = None
            if isinstance(arg, ast.Subscript) and isinstance(arg.value, ast.Name):
                base = arg.value.id
            elif (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                  and arg.func.attr == "remove" and isinstance(arg.func.value, ast.Name)):
                base = arg.func.value.id
            if base is None:
                continue
            holder_name = None
            if isinstance(left, ast.List) and len(left.elts) == 1 and isinstance(left.elts[0], ast.Name):
                holder_name = left.elts[0].id
            elif isinstance(left, ast.Name):
                holder_name = left.id
            if holder_name is None:
                continue

            edits = []
            arg_s, arg_e = _span(source, arg)
            edits.append((arg_s, arg_e, base))
            if isinstance(left, ast.Name):
                left_s, left_e = _span(source, left)
                edits.append((left_s, left_e, f"[{holder_name}]"))
            ret_s, _ = _span(source, node)
            indent = " " * node.col_offset
            edits.append((ret_s, ret_s, f"{base}.remove({holder_name})\n{indent}"))

            edits.sort(key=lambda e: e[0], reverse=True)
            new_src = source
            for s, e, text in edits:
                new_src = new_src[:s] + text + new_src[e:]
            if new_src != source:
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 21: `max(lst)` / `min(lst)` without a `key=` compares raw tuples.
# ----------------------------------------------------------------------

def add_max_min_key(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in _functions(tree):
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        for n in ast.walk(func):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in ("max", "min") and len(n.args) == 1
                    and not n.keywords and isinstance(n.args[0], ast.Name)
                    and n.args[0].id == param):
                s, e = _span(source, n)
                text = source[s:e]
                if not text.endswith(")"):
                    continue
                new_text = text[:-1] + ", key=lambda p: p[1])"
                new_src = source[:s] + new_text + source[e:]
                if new_src != source:
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="flip_selection_comparator", apply=flip_selection_comparator,
                 symptoms=("wrong",)),
            Rule(name="swap_reversed_tracker_assignment", apply=swap_reversed_tracker_assignment,
                 symptoms=("wrong", "timeout")),
            Rule(name="fix_undefined_rhs_in_tracker_assign", apply=fix_undefined_rhs_in_tracker_assign,
                 symptoms=("err:NameError",)),
            Rule(name="fix_undefined_return_name", apply=fix_undefined_return_name,
                 symptoms=("err:NameError",)),
            Rule(name="fix_undefined_accumulator_name", apply=fix_undefined_accumulator_name,
                 symptoms=("err:NameError",)),
            Rule(name="fix_wrong_container_name", apply=fix_wrong_container_name,
                 symptoms=("err:NameError", "err:TypeError", "wrong")),
            Rule(name="trailing_print_to_return_same_arg", apply=trailing_print_to_return_same_arg,
                 symptoms=("wrong",)),
            Rule(name="trailing_print_to_return_accumulator", apply=trailing_print_to_return_accumulator,
                 symptoms=("wrong",)),
            Rule(name="dedent_trailing_return_from_while", apply=dedent_trailing_return_from_while,
                 symptoms=("wrong",)),
            Rule(name="remove_duplicate_trailing_stmt", apply=remove_duplicate_trailing_stmt,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="fix_missing_singleton_tuple", apply=fix_missing_singleton_tuple,
                 symptoms=("wrong",)),
            Rule(name="fix_append_reassignment", apply=fix_append_reassignment,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="fix_missing_index_reset", apply=fix_missing_index_reset,
                 symptoms=("wrong", "timeout")),
            Rule(name="fix_pop_arg_misuse", apply=fix_pop_arg_misuse,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="fix_fake_swap", apply=fix_fake_swap,
                 symptoms=("wrong",)),
            Rule(name="fix_range_off_by_one", apply=fix_range_off_by_one,
                 symptoms=("err:IndexError",)),
            Rule(name="add_missing_subscript", apply=add_missing_subscript,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_for_as_while", apply=fix_for_as_while,
                 symptoms=("wrong", "err:ValueError")),
            Rule(name="add_missing_base_case", apply=add_missing_base_case,
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="fix_recursive_remove", apply=fix_recursive_remove,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="add_max_min_key", apply=add_max_min_key,
                 symptoms=("wrong",)),
        ]