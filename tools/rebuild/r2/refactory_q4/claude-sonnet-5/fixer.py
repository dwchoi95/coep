"""
Repair module for the "Sorting Tuples" (sort_age) assignment.

Each rule inspects the AST of a submission, locates a structural pattern
tied to a specific, well-known misconception, and splices a small, local
textual edit into the original source (never rebuilding the whole file).
"""

import ast
import keyword
import builtins

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


_INDEX_TYPE = getattr(ast, "Index", None)


def _unwrap_slice(sl):
    if _INDEX_TYPE is not None and isinstance(sl, _INDEX_TYPE):
        return sl.value
    return sl


def _assign_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node


def _blocks(tree):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            blk = getattr(node, field, None)
            if isinstance(blk, list) and blk and isinstance(blk[0], ast.stmt):
                yield blk


def _function_defs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _bound_names(func):
    names = {a.arg for a in func.args.args}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.For):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def _find_accumulator(func):
    best = None
    for node in ast.walk(func):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.List) and not node.value.elts):
            if best is None or (node.lineno, node.col_offset) < (best.lineno, best.col_offset):
                best = node
    return best.targets[0].id if best else None


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ----------------------------------------------------------------------
# Rule: normalize the tracker-update assignment inside a selection loop
# ----------------------------------------------------------------------

def _normalize_tracker_update(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for blk in _blocks(tree):
            for idx, node in enumerate(blk):
                if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name) and idx > 0):
                    continue
                prev = blk[idx - 1]
                track = None
                if (isinstance(prev, ast.Assign) and len(prev.targets) == 1
                        and isinstance(prev.targets[0], ast.Name)
                        and isinstance(prev.value, ast.Subscript)):
                    track = prev.targets[0].id
                if track is None:
                    continue
                L = node.target.id
                if track == L:
                    continue
                for sub in node.body:
                    if not isinstance(sub, ast.If):
                        continue
                    names_in_test = {n.id for n in ast.walk(sub.test) if isinstance(n, ast.Name)}
                    if track not in names_in_test or L not in names_in_test:
                        continue
                    if len(sub.body) != 1:
                        continue
                    stmt = sub.body[0]
                    is_correct = (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                                  and isinstance(stmt.targets[0], ast.Name)
                                  and stmt.targets[0].id == track
                                  and isinstance(stmt.value, ast.Name) and stmt.value.id == L)
                    if is_correct:
                        continue
                    s, e = _span(source, stmt)
                    new_stmt = "{} = {}".format(track, L)
                    out.append(source[:s] + new_stmt + source[e:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: after a selection for-loop, remove()/append() should use the
# tracker variable, not the raw loop variable (or some other stray name)
# ----------------------------------------------------------------------

def _fix_post_loop_var(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for blk in _blocks(tree):
            for idx, stmt in enumerate(blk):
                if not (isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name)):
                    continue
                L = stmt.target.id
                track = None
                for n in ast.walk(stmt):
                    if (isinstance(n, ast.Assign) and len(n.targets) == 1
                            and isinstance(n.targets[0], ast.Name)
                            and isinstance(n.value, ast.Name) and n.value.id == L
                            and n.targets[0].id != L):
                        track = n.targets[0].id
                        break
                if track is None:
                    continue
                replacements = []
                for later in blk[idx + 1:]:
                    for call in ast.walk(later):
                        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                                and call.func.attr in ("remove", "append") and len(call.args) == 1
                                and isinstance(call.args[0], ast.Name) and call.args[0].id != track):
                            replacements.append(call.args[0])
                if not replacements:
                    continue
                reps = [(_span(source, n)) for n in replacements]
                reps.sort(key=lambda r: -r[0])
                new_source = source
                for s, e in reps:
                    new_source = new_source[:s] + track + new_source[e:]
                out.append(new_source)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: resolve a single undefined "container" / "accumulator" name
# (e.g. `a` used instead of `lst`, `final` instead of `people`, etc.)
# ----------------------------------------------------------------------

def _resolve_undefined_names(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    try:
        _assign_parents(tree)
        out = []
        for func in _function_defs(tree):
            if not func.args.args:
                continue
            param = func.args.args[0].arg
            bound = _bound_names(func)
            acc = _find_accumulator(func)
            reps = []
            for node in ast.walk(func):
                if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)):
                    continue
                if node.id in bound:
                    continue
                parent = getattr(node, "_parent", None)
                kind = None
                if isinstance(parent, ast.Subscript) and parent.value is node:
                    kind = "container"
                elif isinstance(parent, ast.For) and parent.iter is node:
                    kind = "container"
                elif isinstance(parent, ast.While) and parent.test is node:
                    kind = "container"
                elif isinstance(parent, ast.Attribute) and parent.value is node:
                    gp = getattr(parent, "_parent", None)
                    if isinstance(gp, ast.Call) and gp.func is parent:
                        if parent.attr in ("remove", "pop"):
                            kind = "container"
                        elif parent.attr == "append":
                            kind = "accumulator"
                elif isinstance(parent, ast.Return) and parent.value is node:
                    kind = "accumulator"
                if kind == "container":
                    new_name = param
                elif kind == "accumulator" and acc is not None:
                    new_name = acc
                else:
                    continue
                if new_name == node.id:
                    continue
                reps.append((node, new_name))
            if not reps:
                continue
            spans = [(_span(source, n), txt) for n, txt in reps]
            spans.sort(key=lambda r: -r[0][0])
            new_source = source
            for (s, e), txt in spans:
                new_source = new_source[:s] + txt + new_source[e:]
            if new_source != source:
                out.append(new_source)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: typo correction via edit distance to an identifier bound in
# the same function (e.g. `larget` -> `largest`, `biggesr` -> `biggest`)
# ----------------------------------------------------------------------

def _edit_distance(a, b):
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[lb]


def _typo_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        builtin_names = set(dir(builtins)) | set(keyword.kwlist)
        for func in _function_defs(tree):
            bound = _bound_names(func)
            undefined = {}
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.id not in bound and node.id not in builtin_names:
                        undefined.setdefault(node.id, []).append(node)
            for name, nodes in undefined.items():
                if len(name) < 3:
                    continue
                candidates = [b for b in bound if abs(len(b) - len(name)) <= 2 and b not in builtin_names]
                scored = sorted((_edit_distance(name, b), b) for b in candidates)
                if not scored or scored[0][0] > 2 or scored[0][0] == 0:
                    continue
                if len(scored) > 1 and scored[1][0] == scored[0][0]:
                    continue
                best_name = scored[0][1]
                reps = sorted((_span(source, n) for n in nodes), key=lambda r: -r[0])
                new_source = source
                for s, e in reps:
                    new_source = new_source[:s] + best_name + new_source[e:]
                out.append(new_source)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: a return statement wrongly nested as the last line of a
# while/for body (fires only once) -> dedent it to after the loop
# ----------------------------------------------------------------------

def _dedent_loop_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, (ast.While, ast.For)) and node.body and len(node.body) > 1 \
                    and isinstance(node.body[-1], ast.Return):
                ret = node.body[-1]
                s, e = _span(source, ret)
                line_start = source.rfind("\n", 0, s) + 1
                line_end = source.find("\n", e)
                line_end = line_end + 1 if line_end != -1 else len(source)
                ret_text = source[s:e]
                new_source = source[:line_start] + source[line_end:]
                indent = " " * node.col_offset
                # position right after the loop: loop's own header line is
                # unaffected by removing a later body line
                loop_s, _ = _span(source, node)
                loop_line_start = source.rfind("\n", 0, loop_s) + 1
                # length before the removed region is unchanged in new_source
                if loop_line_start >= line_start:
                    continue
                # find end of loop block in new_source: everything up to line_start
                insertion = "\n" + indent + ret_text
                candidate = new_source[:line_start] + insertion + new_source[line_start:]
                out.append(candidate)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: move a `.reverse` / `.reverse()` call on the accumulator out of
# the while-loop body (it should run once, after the loop)
# ----------------------------------------------------------------------

def _move_reverse_after_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.While) and node.body and len(node.body) > 1):
                continue
            last = node.body[-1]
            target_name = None
            if isinstance(last, ast.Expr):
                v = last.value
                if isinstance(v, ast.Attribute) and v.attr == "reverse" and isinstance(v.value, ast.Name):
                    target_name = v.value.id
                elif (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                        and v.func.attr == "reverse" and isinstance(v.func.value, ast.Name)
                        and not v.args):
                    target_name = v.func.value.id
            if target_name is None:
                continue
            s, e = _span(source, last)
            line_start = source.rfind("\n", 0, s) + 1
            line_end = source.find("\n", e)
            line_end = line_end + 1 if line_end != -1 else len(source)
            new_source = source[:line_start] + source[line_end:]
            indent = " " * node.col_offset
            insertion = "\n" + indent + target_name + ".reverse()"
            candidate = new_source[:line_start] + insertion + new_source[line_start:]
            out.append(candidate)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `return X.reverse` / `return X.reverse()` is wrong (returns
# None); either drop the stray reverse or hoist it to its own statement
# ----------------------------------------------------------------------

def _fix_return_reverse(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Return) and node.value is not None):
                continue
            v = node.value
            target_name = None
            if isinstance(v, ast.Attribute) and v.attr == "reverse" and isinstance(v.value, ast.Name):
                target_name = v.value.id
            elif (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                    and v.func.attr == "reverse" and isinstance(v.func.value, ast.Name)
                    and not v.args):
                target_name = v.func.value.id
            if target_name is None:
                continue
            s, e = _span(source, node)
            indent = " " * node.col_offset
            out.append(source[:s] + "return {}".format(target_name) + source[e:])
            out.append(source[:s] + "{0}.reverse()\n{1}return {0}".format(target_name, indent) + source[e:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `obj.method[idx]` instead of `obj.method(idx)` for list mutators
# ----------------------------------------------------------------------

def _fix_subscript_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                    and node.value.attr in ("pop", "remove", "append")):
                obj_s, obj_e = _span(source, node.value.value)
                sl = _unwrap_slice(node.slice)
                idx_s, idx_e = _span(source, sl)
                obj_text = source[obj_s:obj_e]
                idx_text = source[idx_s:idx_e]
                new_text = "{}.{}({})".format(obj_text, node.value.attr, idx_text)
                out.append(_splice(source, node, new_text))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `X = X.append(Y)` clobbers the list with None -> `X.append(Y)`
# ----------------------------------------------------------------------

def _fix_assign_from_append(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                continue
            tgt = node.targets[0].id
            v = node.value
            if (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "append"
                    and isinstance(v.func.value, ast.Name) and v.func.value.id == tgt):
                s, e = _span(source, node)
                vs, ve = _span(source, v)
                out.append(source[:s] + source[vs:ve] + source[e:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: assigning *to* the for-loop variable instead of from it
# (e.g. `j = tpl` inside `for j in ...`, should be `tpl = j`)
# ----------------------------------------------------------------------

def _swap_loop_target_assign(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
                continue
            L = node.target.id
            for sub in ast.walk(node):
                if sub is node:
                    continue
                if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                        and isinstance(sub.targets[0], ast.Name) and sub.targets[0].id == L
                        and isinstance(sub.value, ast.Name) and sub.value.id != L):
                    other = sub.value.id
                    s, e = _span(source, sub)
                    out.append(source[:s] + "{} = {}".format(other, L) + source[e:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: recursive base case `len(lst) == 1` should also stop on empty
# ----------------------------------------------------------------------

def _fix_base_case(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left = node.left
                right = node.comparators[0]
                if (isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len"
                        and isinstance(right, ast.Constant) and right.value == 1):
                    ls, le = _span(source, left)
                    new_cmp = source[ls:le] + " <= 1"
                    out.append(_splice(source, node, new_cmp))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: `range(1, len(lst) + 1)` style off-by-one causing IndexError
# ----------------------------------------------------------------------

def _fix_range_plus_one(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                for arg in node.args:
                    if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)
                            and isinstance(arg.right, ast.Constant) and arg.right.value == 1
                            and isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name)
                            and arg.left.func.id == "len"):
                        ls, le = _span(source, arg.left)
                        out.append(_splice(source, arg, source[ls:le]))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: comparing two tuple-valued names directly, missing the `[1]`
# age-field access (e.g. `if i > largest:` should be `if i[1] > largest[1]:`)
# ----------------------------------------------------------------------

def _fix_bare_tuple_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    op_txt = {ast.Gt: ">", ast.Lt: "<", ast.GtE: ">=", ast.LtE: "<="}
    try:
        for func in _function_defs(tree):
            tuple_like = set()
            for node in ast.walk(func):
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Subscript)):
                    sl = _unwrap_slice(node.value.slice)
                    if isinstance(sl, ast.Constant) and sl.value == 0:
                        tuple_like.add(node.targets[0].id)
                if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                    tuple_like.add(node.target.id)
            for node in ast.walk(func):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in op_txt:
                    left, right = node.left, node.comparators[0]
                    if (isinstance(left, ast.Name) and isinstance(right, ast.Name)
                            and left.id in tuple_like and right.id in tuple_like):
                        new_cmp = "{}[1] {} {}[1]".format(left.id, op_txt[type(node.ops[0])], right.id)
                        out.append(_splice(source, node, new_cmp))
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: tracker initialised *inside* the for-loop body (reset every
# iteration) when it should be initialised once, before the loop
# ----------------------------------------------------------------------

def _hoist_tracker_init(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for blk in _blocks(tree):
            for stmt in blk:
                if not (isinstance(stmt, ast.For) and stmt.body and len(stmt.body) > 1):
                    continue
                first = stmt.body[0]
                if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                        and isinstance(first.targets[0], ast.Name) and isinstance(first.value, ast.Subscript)):
                    continue
                track = first.targets[0].id
                used_later = any(
                    isinstance(n, ast.Name) and n.id == track
                    for sub in stmt.body[1:] for n in ast.walk(sub)
                )
                if not used_later:
                    continue
                s, e = _span(source, first)
                line_start = source.rfind("\n", 0, s) + 1
                line_end = source.find("\n", e)
                line_end = line_end + 1 if line_end != -1 else len(source)
                stmt_text = source[s:e]
                new_source = source[:line_start] + source[line_end:]
                loop_s, _ = _span(source, stmt)
                loop_line_start = source.rfind("\n", 0, loop_s) + 1
                if loop_line_start >= line_start:
                    continue
                indent = " " * stmt.col_offset
                insertion = indent + stmt_text + "\n"
                candidate = new_source[:loop_line_start] + insertion + new_source[loop_line_start:]
                out.append(candidate)
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: function body falls through without a return -> add one using
# the detected accumulator variable
# ----------------------------------------------------------------------

def _add_missing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for func in _function_defs(tree):
            if any(isinstance(n, ast.Return) for n in ast.walk(func)):
                continue
            acc = _find_accumulator(func)
            if acc is None:
                continue
            last = func.body[-1]
            s, e = _span(source, last)
            indent = " " * last.col_offset
            if isinstance(last, ast.Pass):
                out.append(source[:s] + "return {}".format(acc) + source[e:])
            else:
                out.append(source[:e] + "\n{}return {}".format(indent, acc) + source[e:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Rule: an accumulator used via `.append(...)`/`return` is never
# initialised anywhere -> insert `ACC = []` at the top of the function
# ----------------------------------------------------------------------

def _init_missing_accumulator(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        _assign_parents(tree)
        for func in _function_defs(tree):
            bound = _bound_names(func)
            candidates = set()
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in bound:
                    parent = getattr(node, "_parent", None)
                    if isinstance(parent, ast.Attribute) and parent.value is node:
                        gp = getattr(parent, "_parent", None)
                        if isinstance(gp, ast.Call) and gp.func is parent and parent.attr == "append":
                            candidates.add(node.id)
                    if isinstance(parent, ast.Return) and parent.value is node:
                        candidates.add(node.id)
            if len(candidates) != 1 or not func.body:
                continue
            name = next(iter(candidates))
            first = func.body[0]
            indent = " " * first.col_offset
            s, _ = _span(source, first)
            insertion = "{} = []\n{}".format(name, indent)
            out.append(source[:s] + insertion + source[s:])
    except Exception:
        return []
    return out


# ----------------------------------------------------------------------
# Fixer
# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="normalize_tracker_update_in_selection_if",
                apply=_normalize_tracker_update,
                symptoms=("wrong", "err:NameError", "err:UnboundLocalError"),
            ),
            Rule(
                name="post_loop_use_tracker_not_loopvar",
                apply=_fix_post_loop_var,
                symptoms=("wrong", "err:NameError", "err:ValueError"),
            ),
            Rule(
                name="resolve_undefined_container_or_accumulator",
                apply=_resolve_undefined_names,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="typo_correction_to_bound_name",
                apply=_typo_fix,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="dedent_return_out_of_loop",
                apply=_dedent_loop_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="move_reverse_after_loop",
                apply=_move_reverse_after_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_return_reverse",
                apply=_fix_return_reverse,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_subscript_used_as_call",
                apply=_fix_subscript_call,
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="fix_assign_from_append",
                apply=_fix_assign_from_append,
                symptoms=("wrong", "err:AttributeError"),
            ),
            Rule(
                name="swap_loop_target_assignment",
                apply=_swap_loop_target_assign,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_recursive_base_case_off_by_one",
                apply=_fix_base_case,
                symptoms=("err:IndexError", "wrong"),
            ),
            Rule(
                name="fix_range_plus_one_off_by_one",
                apply=_fix_range_plus_one,
                symptoms=("err:IndexError", "wrong"),
            ),
            Rule(
                name="fix_bare_tuple_comparison",
                apply=_fix_bare_tuple_compare,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="hoist_tracker_init_out_of_for_loop",
                apply=_hoist_tracker_init,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_missing_return",
                apply=_add_missing_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="init_missing_accumulator",
                apply=_init_missing_accumulator,
                symptoms=("err:NameError", "wrong"),
            ),
        ]