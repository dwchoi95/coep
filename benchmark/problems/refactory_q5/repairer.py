"""Local, LLM-free automatic repair for the Top-K assignment.

Combines problem-specific AST rewrite rules (targeting common misconceptions
for this assignment) with the generic mutation search from coep.repairlib.
Every returned candidate is validated by first_passing (test suite + rps cap).
"""

import ast
import copy

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "top_k"

TESTS = [
    {"args": [[9, 9, 4, 9, 7, 9, 3, 1, 6], 5], "expected": [9, 9, 9, 9, 7]},
    {"args": [[9, 8, 4, 5, 7, 2, 3, 1, 6], 5], "expected": [9, 8, 7, 6, 5]},
    {"args": [[4, 5, 2, 3, 1, 6], 6], "expected": [6, 5, 4, 3, 2, 1]},
    {"args": [[4, 5, 2, 3, 1, 6], 3], "expected": [6, 5, 4]},
    {"args": [[4, 5, 2, 3, 1, 6], 0], "expected": []},
]

MAX_RPS = 0.35


# ---------------------------------------------------------------- utilities

def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


def _unparse_safe(tree):
    try:
        return ast.unparse(tree)
    except Exception:
        return None


def _norm(src):
    t = _parse(src)
    if t is None:
        return src
    u = _unparse_safe(t)
    return u if u is not None else src


def _entry_func(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            return node
    return None


def _kname(tree):
    f = _entry_func(tree)
    if f is not None and len(f.args.args) >= 2:
        return f.args.args[1].arg
    return "k"


def _rev(v):
    return ast.Subscript(
        value=v,
        slice=ast.Slice(lower=None, upper=None,
                        step=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1))),
        ctx=ast.Load(),
    )


def _slice_upper_name(v, kname):
    return ast.Subscript(
        value=v,
        slice=ast.Slice(lower=None, upper=ast.Name(id=kname, ctx=ast.Load()), step=None),
        ctx=ast.Load(),
    )


def _append_target(st):
    if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
            and isinstance(st.value.func, ast.Attribute)
            and st.value.func.attr == "append"
            and isinstance(st.value.func.value, ast.Name)):
        return st.value.func.value.id
    return None


def _appended_names(node):
    out = set()
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "append" and isinstance(n.func.value, ast.Name)):
            out.add(n.func.value.id)
    return out


def _flat_add(e):
    if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
        return _flat_add(e.left) + _flat_add(e.right)
    return [e]


def _safe_iter(gen):
    it = iter(gen)
    while True:
        try:
            item = next(it)
        except StopIteration:
            return
        except Exception:
            return
        yield item


# ---------------------------------------------------------------- rules
# Every rule: source string -> list of candidate source strings.
# Candidates are only ever accepted after validation by first_passing.

def rule_strip_subscript_compare(src):
    """Fix comparisons copied from another exercise, e.g. i[1] > big[1] -> i > big."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = [False]

    def strip(x):
        if (isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name)
                and isinstance(x.slice, ast.Constant)):
            changed[0] = True
            return ast.Name(id=x.value.id, ctx=ast.Load())
        return x

    for node in list(ast.walk(tree)):
        if isinstance(node, ast.Compare):
            node.left = strip(node.left)
            node.comparators = [strip(c) for c in node.comparators]
    if not changed[0]:
        return []
    u = _unparse_safe(tree)
    return [u] if u else []


def _split_append_remove_stmt(st):
    if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)):
        return None
    call = st.value
    f = call.func
    if not (isinstance(f, ast.Attribute) and f.attr == "append" and len(call.args) == 1):
        return None
    inner = call.args[0]
    if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "remove" and len(inner.args) == 1):
        return None
    val = inner.args[0]
    s1 = ast.Expr(value=ast.Call(
        func=ast.Attribute(value=copy.deepcopy(f.value), attr="append", ctx=ast.Load()),
        args=[copy.deepcopy(val)], keywords=[]))
    s2 = ast.Expr(value=copy.deepcopy(inner))
    return [s1, s2]


def rule_split_append_remove(src):
    """new.append(lst.remove(x)) appends None -> new.append(x); lst.remove(x)."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = False
    for parent in list(ast.walk(tree)):
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(parent, field, None)
            if not isinstance(stmts, list) or not stmts:
                continue
            new_stmts, local = [], False
            for st in stmts:
                rep = _split_append_remove_stmt(st)
                if rep:
                    new_stmts.extend(rep)
                    local = True
                else:
                    new_stmts.append(st)
            if local:
                setattr(parent, field, new_stmts)
                changed = True
    if not changed:
        return []
    u = _unparse_safe(tree)
    return [u] if u else []


def rule_drop_bad_assign(src):
    """x = lst.remove(...) / x = lst.sort() (returns None) -> bare mutation call."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = False
    for parent in list(ast.walk(tree)):
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(parent, field, None)
            if not isinstance(stmts, list):
                continue
            for i, st in enumerate(stmts):
                if (isinstance(st, ast.Assign) and isinstance(st.value, ast.Call)
                        and isinstance(st.value.func, ast.Attribute)
                        and st.value.func.attr in ("remove", "sort", "append",
                                                   "reverse", "insert", "extend")
                        and len(st.targets) == 1
                        and isinstance(st.targets[0], ast.Name)):
                    stmts[i] = ast.Expr(value=st.value)
                    changed = True
    if not changed:
        return []
    u = _unparse_safe(tree)
    return [u] if u else []


def rule_slice_upper(src):
    """Boundary fix in slices: X[:k-1] -> X[:k]."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = False
    for n in list(ast.walk(tree)):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice):
            up = n.slice.upper
            if (isinstance(up, ast.BinOp) and isinstance(up.op, ast.Sub)
                    and isinstance(up.right, ast.Constant) and up.right.value == 1):
                n.slice.upper = up.left
                changed = True
    if not changed:
        return []
    u = _unparse_safe(tree)
    return [u] if u else []


def _is_len_break(st, L):
    if not isinstance(st, ast.If) or st.orelse:
        return False
    if not (len(st.body) == 1 and isinstance(st.body[0], ast.Break)):
        return False
    t = st.test
    if not (isinstance(t, ast.Compare) and len(t.ops) == 1):
        return False

    def is_lenL(e):
        return (isinstance(e, ast.Call) and isinstance(e.func, ast.Name)
                and e.func.id == "len" and len(e.args) == 1
                and isinstance(e.args[0], ast.Name) and e.args[0].id == L)

    return is_lenL(t.left) or is_lenL(t.comparators[0])


def rule_swap_append_check(src):
    """out.append(x); if len(out)==k: break  -> check before appending (fixes k=0)."""
    tree = _parse(src)
    if tree is None:
        return []
    out = []
    loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
    for li, loop in enumerate(loops):
        body = loop.body
        for i in range(len(body) - 1):
            L = _append_target(body[i])
            if L is None:
                continue
            if not _is_len_break(body[i + 1], L):
                continue
            t2 = _parse(src)
            loops2 = [n for n in ast.walk(t2) if isinstance(n, (ast.For, ast.While))]
            body2 = loops2[li].body
            body2[i], body2[i + 1] = body2[i + 1], body2[i]
            u = _unparse_safe(t2)
            if u:
                out.append(u)
    return out


def rule_insert_remove(src):
    """Loop appends max(lst) but never removes it -> insert lst.remove(max(lst))."""
    tree = _parse(src)
    if tree is None:
        return []
    out = []
    loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
    for li, loop in enumerate(loops):
        has_remove = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and n.func.attr in ("remove", "pop")
                         for n in ast.walk(loop))
        if has_remove:
            continue
        for si, st in enumerate(loop.body):
            if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)):
                continue
            c = st.value
            if not (isinstance(c.func, ast.Attribute) and c.func.attr == "append"
                    and len(c.args) == 1):
                continue
            a = c.args[0]
            if not (isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
                    and a.func.id in ("max", "min") and len(a.args) == 1
                    and isinstance(a.args[0], ast.Name)):
                continue
            t2 = _parse(src)
            loop2 = [n for n in ast.walk(t2) if isinstance(n, (ast.For, ast.While))][li]
            rem = ast.Expr(value=ast.Call(
                func=ast.Attribute(value=ast.Name(id=a.args[0].id, ctx=ast.Load()),
                                   attr="remove", ctx=ast.Load()),
                args=[copy.deepcopy(a)], keywords=[]))
            loop2.body.insert(si + 1, rem)
            u = _unparse_safe(t2)
            if u:
                out.append(u)
    return out


def rule_while_cond(src):
    """Replace a broken while condition by len(out) < k (or k > len(out)) for each
    list that the loop appends to; only for loops that also shrink some list."""
    tree = _parse(src)
    if tree is None:
        return []
    k = _kname(tree)
    out = []
    whiles = [n for n in ast.walk(tree) if isinstance(n, ast.While)]
    for wi, w in enumerate(whiles):
        shrinks = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr in ("remove", "pop")
                      for n in ast.walk(w)) or \
            any(isinstance(n, ast.Delete) for n in ast.walk(w))
        if not shrinks:
            continue
        for L in sorted(_appended_names(w)):
            for orient in (0, 1):
                t2 = _parse(src)
                w2 = [n for n in ast.walk(t2) if isinstance(n, ast.While)][wi]
                lenL = ast.Call(func=ast.Name(id="len", ctx=ast.Load()),
                                args=[ast.Name(id=L, ctx=ast.Load())], keywords=[])
                kn = ast.Name(id=k, ctx=ast.Load())
                if orient == 0:
                    w2.test = ast.Compare(left=lenL, ops=[ast.Lt()], comparators=[kn])
                else:
                    w2.test = ast.Compare(left=kn, ops=[ast.Gt()], comparators=[lenL])
                u = _unparse_safe(t2)
                if u:
                    out.append(u)
    return out


def _wrap_topk(name_id):
    call = ast.Call(
        func=ast.Name(id=ENTRY, ctx=ast.Load()),
        args=[ast.Name(id=name_id, ctx=ast.Load()),
              ast.Call(func=ast.Name(id="len", ctx=ast.Load()),
                       args=[ast.Name(id=name_id, ctx=ast.Load())], keywords=[])],
        keywords=[])
    return _rev(call)


def rule_partition_recurse(src):
    """One-pass pivot partition is not a sort: make the partition recursive.
    sort_list = lower + plist + higher
      -> sort_list = top_k(lower, len(lower))[::-1] + plist + top_k(higher, len(higher))[::-1]
    """
    tree = _parse(src)
    if tree is None:
        return []
    f = _entry_func(tree)
    if f is None:
        return []
    appended = _appended_names(f)
    out = []
    assigns = [n for n in ast.walk(f) if isinstance(n, ast.Assign)]
    for ai, a in enumerate(assigns):
        parts = _flat_add(a.value)
        if len(parts) not in (2, 3):
            continue
        if not all(isinstance(p, ast.Name) for p in parts):
            continue
        if len(parts) == 3:
            idxsets = [(0, 2), (0, 1, 2)]
        else:
            idxsets = [(0, 1)]
        for idxs in idxsets:
            if not all(parts[i].id in appended for i in idxs):
                continue
            t2 = _parse(src)
            f2 = _entry_func(t2)
            a2 = [n for n in ast.walk(f2) if isinstance(n, ast.Assign)][ai]
            parts2 = _flat_add(a2.value)
            newparts = []
            for i, p in enumerate(parts2):
                if i in idxs:
                    newparts.append(_wrap_topk(p.id))
                else:
                    newparts.append(p)
            expr = newparts[0]
            for p in newparts[1:]:
                expr = ast.BinOp(left=expr, op=ast.Add(), right=p)
            a2.value = expr
            u = _unparse_safe(t2)
            if u:
                out.append(u)
    return out


def rule_alias_entry(src):
    """Function misnamed (e.g. topk / top_K): add an alias top_k = <name>."""
    tree = _parse(src)
    if tree is None:
        return []
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    if ENTRY in names:
        return []
    return [src + "\n\n%s = %s\n" % (ENTRY, nm) for nm in names]


def rule_minmax(src):
    """Swap min <-> max calls (bottom-k instead of top-k misconception)."""
    out = []
    for a, b in (("min", "max"), ("max", "min")):
        tree = _parse(src)
        if tree is None:
            return out
        changed = False
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == a):
                n.func.id = b
                changed = True
        if changed:
            u = _unparse_safe(tree)
            if u:
                out.append(u)
    return out


def rule_sort_reverse(src):
    """If the student used sort()/sorted() anyway, add reverse=True."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = False
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Attribute) and n.func.attr == "sort":
            if not any(kw.arg == "reverse" for kw in n.keywords):
                n.keywords.append(ast.keyword(arg="reverse", value=ast.Constant(True)))
                changed = True
        elif isinstance(n.func, ast.Name) and n.func.id == "sorted":
            if not any(kw.arg == "reverse" for kw in n.keywords):
                n.keywords.append(ast.keyword(arg="reverse", value=ast.Constant(True)))
                changed = True
    if not changed:
        return []
    u = _unparse_safe(tree)
    return [u] if u else []


def rule_neg_slice(src):
    """Ascending list sliced X[-k:] (breaks for k=0, wrong order) -> X[::-1][:k]."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = False
    for n in list(ast.walk(tree)):
        if (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)
                and n.slice.upper is None and n.slice.step is None
                and isinstance(n.slice.lower, ast.UnaryOp)
                and isinstance(n.slice.lower.op, ast.USub)):
            operand = n.slice.lower.operand
            n.value = _rev(copy.deepcopy(n.value))
            n.slice = ast.Slice(lower=None, upper=copy.deepcopy(operand), step=None)
            changed = True
    if not changed:
        return []
    u = _unparse_safe(tree)
    return [u] if u else []


def rule_return_slice(src):
    """Forgot to slice / built ascending: return X -> X[:k], X[::-1][:k], X[::-1];
    return X[a:b] -> return X[::-1][a:b]."""
    tree = _parse(src)
    if tree is None:
        return []
    f = _entry_func(tree)
    if f is None:
        return []
    k = _kname(tree)
    out = []
    rets = [n for n in ast.walk(f) if isinstance(n, ast.Return) and n.value is not None]
    for ri, r in enumerate(rets):
        v = r.value
        if isinstance(v, ast.Name) and v.id != k:
            templates = ["slice_k", "rev_slice_k", "rev"]
        elif isinstance(v, ast.Call):
            templates = ["slice_k", "rev_slice_k"]
        elif isinstance(v, ast.Subscript):
            templates = ["rev_inside"]
        else:
            continue
        for tpl in templates:
            t2 = _parse(src)
            f2 = _entry_func(t2)
            r2 = [n for n in ast.walk(f2)
                  if isinstance(n, ast.Return) and n.value is not None][ri]
            v2 = r2.value
            if tpl == "slice_k":
                r2.value = _slice_upper_name(v2, k)
            elif tpl == "rev_slice_k":
                r2.value = _slice_upper_name(_rev(v2), k)
            elif tpl == "rev":
                r2.value = _rev(v2)
            elif tpl == "rev_inside":
                v2.value = _rev(v2.value)
            u = _unparse_safe(t2)
            if u:
                out.append(u)
    return out


def rule_for_range_k(src):
    """Selection loop iterating over the wrong thing -> for _ in range(k)."""
    tree = _parse(src)
    if tree is None:
        return []
    f = _entry_func(tree)
    if f is None:
        return []
    k = _kname(tree)
    out = []
    fors = [n for n in ast.walk(f) if isinstance(n, ast.For)]
    for fi, fr in enumerate(fors):
        it = fr.iter
        if (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                and it.func.id == "range" and len(it.args) == 1
                and isinstance(it.args[0], ast.Name) and it.args[0].id == k):
            continue
        if not _appended_names(fr):
            continue
        t2 = _parse(src)
        f2 = _entry_func(t2)
        fr2 = [n for n in ast.walk(f2) if isinstance(n, ast.For)][fi]
        fr2.iter = ast.Call(func=ast.Name(id="range", ctx=ast.Load()),
                            args=[ast.Name(id=k, ctx=ast.Load())], keywords=[])
        u = _unparse_safe(t2)
        if u:
            out.append(u)
    return out


# Rules whose fixes are worth composing with each other (applied to the whole
# growing pool, so e.g. split-append-remove + while-condition compose).
COMBO_RULES = [
    rule_strip_subscript_compare,
    rule_split_append_remove,
    rule_drop_bad_assign,
    rule_insert_remove,
    rule_slice_upper,
    rule_swap_append_check,
    rule_while_cond,
    rule_partition_recurse,
]

# Rules applied only to the original source.
SINGLE_RULES = [
    rule_minmax,
    rule_sort_reverse,
    rule_neg_slice,
    rule_return_slice,
    rule_for_range_k,
]


def _rule_variants(source):
    seen = {_norm(source)}
    pool = [source]

    def add(lst, v):
        if not v:
            return
        key = _norm(v)
        if key in seen:
            return
        seen.add(key)
        lst.append(v)

    # Alias variants first (they unlock everything else when the name is wrong).
    alias = []
    try:
        for v in rule_alias_entry(source):
            add(alias, v)
    except Exception:
        pass

    for rule in COMBO_RULES:
        additions = []
        for s in list(pool):
            if len(additions) >= 16:
                break
            try:
                vs = rule(s)
            except Exception:
                vs = []
            for v in vs:
                add(additions, v)
                if len(additions) >= 16:
                    break
        pool.extend(additions)
        if len(pool) > 48:
            pool = pool[:48]

    singles = []
    for rule in SINGLE_RULES:
        try:
            vs = rule(source)
        except Exception:
            vs = []
        for v in vs:
            add(singles, v)

    variants = alias + pool[1:] + singles
    return variants[:60]


def _repair(source):
    if not isinstance(source, str):
        return None
    if _parse(source) is None:
        return None

    try:
        variants = _rule_variants(source)
    except Exception:
        variants = []

    # Phase 1: original, rule-based variants, 1-edit generic search on the
    # original, then 1-edit generic search chained on the best rule variants.
    gens = [iter([source])]
    if variants:
        gens.append(iter(list(variants)))
    try:
        gens.append(_safe_iter(candidates_generic(source, max_edits=1, budget=1500)))
    except Exception:
        pass
    for v in variants[:12]:
        try:
            gens.append(_safe_iter(candidates_generic(v, max_edits=1, budget=250)))
        except Exception:
            pass
    cand = None
    try:
        cand = first_passing(chain(*gens), ENTRY, TESTS, source,
                             max_rps=MAX_RPS, max_checks=800)
    except Exception:
        cand = None
    if cand is not None:
        return cand

    # Phase 2: 2-edit generic search on the original as a fallback.
    try:
        cand = first_passing(
            _safe_iter(candidates_generic(source, max_edits=2, budget=2500)),
            ENTRY, TESTS, source, max_rps=MAX_RPS, max_checks=600)
    except Exception:
        cand = None
    return cand


def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None
