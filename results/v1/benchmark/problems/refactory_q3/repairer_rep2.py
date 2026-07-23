"""Local, LLM-free automatic repair for the `remove_extras` (duplicate
elimination) assignment.

Strategy: problem-specific, AST-located but byte-splicing rewrite rules for
the misconceptions students typically show on this task (mutating the list
while iterating so the LAST occurrence survives, using `.reverse()`/`.sort()`
as a value, accumulating into a tuple, missing base-case/fall-through return,
pair-counting duplicates without a break, `count(x)==1` instead of membership,
returning inside the loop, ...), dispatched on the observed failing-test
pattern, then chained with the generic mutation search.  Every returned
candidate is validated by `first_passing` (full test suite + rps <= 0.35
versus the student's original code)."""

import ast
import re
import time

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "remove_extras"
MAX_RPS = 0.35

TESTS = [
    {"args": [[1, 1, 1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 5, 1, 1, 3, 2]], "expected": [1, 5, 3, 2]},
    {"args": [[]], "expected": []},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
]

# --------------------------------------------------------------- utilities
# All edits are located via the AST but performed by splicing the original
# source string, so untouched code stays byte-identical (small rps).


def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


def _func(tree):
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    for f in fns:
        if f.name == ENTRY:
            return f
    return fns[0] if fns else None


def _offsets(src):
    offs, tot = [], 0
    for ln in src.splitlines(keepends=True):
        offs.append(tot)
        tot += len(ln)
    offs.append(tot)
    return offs


def _span(offs, node):
    return (offs[node.lineno - 1] + node.col_offset,
            offs[node.end_lineno - 1] + node.end_col_offset)


def _seg(src, offs, node):
    a, b = _span(offs, node)
    return src[a:b]


def _apply(src, repls):
    for a, b, txt in sorted(repls, key=lambda r: r[0], reverse=True):
        src = src[:a] + txt + src[b:]
    return src


def _lines(src):
    return src.splitlines(keepends=True)


def _indent_of(line):
    return re.match(r"[ \t]*", line).group(0)


def _insert_lines(src, at_lineno, texts):
    """Insert full lines (no trailing newline in texts) before 1-based line."""
    lines = _lines(src)
    i = min(max(at_lineno - 1, 0), len(lines))
    if i > 0 and lines and not lines[i - 1].endswith("\n"):
        lines[i - 1] += "\n"
    return "".join(lines[:i] + [t + "\n" for t in texts] + lines[i:])


def _parents(tree):
    par = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            par[c] = n
    return par


# ------------------------------------------------------- rewrite rules
# Each rule: generator of candidate sources; must never raise into caller.


def _r_fix_return(src, tree, fn):
    """Missing/None/wrong return: append `return <acc>` on fall-through,
    fill a bare `return`, or swap the returned variable name."""
    if not fn.body:
        return
    names = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id not in names:
                    names.append(t.id)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            if n.target.id not in names:
                names.append(n.target.id)
    params = [a.arg for a in fn.args.args]
    targets = []
    for nm in names + params:
        if nm not in targets:
            targets.append(nm)
    if not targets:
        return
    last = fn.body[-1]
    offs = _offsets(src)
    if isinstance(last, ast.Return):
        if last.value is None:
            a, b = _span(offs, last)
            for nm in targets:
                yield _apply(src, [(a, b, "return " + nm)])
        elif isinstance(last.value, ast.Name):
            a, b = _span(offs, last.value)
            for nm in targets:
                if nm != last.value.id:
                    yield _apply(src, [(a, b, nm)])
        return
    lines = _lines(src)
    indent = _indent_of(lines[fn.body[0].lineno - 1])
    for nm in targets:
        yield _insert_lines(src, fn.end_lineno + 1, [indent + "return " + nm])


def _r_print_to_return(src, tree, fn):
    """Final `print(x)` instead of `return x`."""
    if not fn.body:
        return
    last = fn.body[-1]
    if (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
            and isinstance(last.value.func, ast.Name)
            and last.value.func.id == "print" and len(last.value.args) == 1):
        offs = _offsets(src)
        a, b = _span(offs, last)
        inner = _seg(src, offs, last.value.args[0])
        yield _apply(src, [(a, b, "return " + inner)])


def _r_mutator_as_value(src, tree, fn):
    """`x = L.reverse()` / `return L.sort()` misconception: these return
    None.  Replace value-position `.reverse()` with slicing and `.sort()`
    with sorted(); drop `x = x.append(v)` down to `x.append(v)`."""
    offs = _offsets(src)
    par = _parents(tree)
    repls = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and not n.args and n.func.attr in ("reverse", "sort")
                and not isinstance(par.get(n), ast.Expr)):
            base = _seg(src, offs, n.func.value)
            a, b = _span(offs, n)
            if n.func.attr == "reverse":
                repls.append((a, b, base + "[::-1]"))
            else:
                repls.append((a, b, "sorted(" + base + ")"))
    if repls:
        yield _apply(src, repls)
        if len(repls) > 1:
            for r in repls:
                yield _apply(src, [r])
    for n in ast.walk(fn):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr in ("append", "insert", "extend")):
            a, b = _span(offs, n)
            yield _apply(src, [(a, b, _seg(src, offs, n.value))])


def _r_tuple_to_list(src, tree, fn):
    """Accumulating into a tuple (`a = ()`, `a += (x,)` / `a += ((x))`):
    convert the accumulator to a list so `+=` works and a list is returned."""
    offs = _offsets(src)
    tuple_names = set()
    repls = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Tuple)
                and not n.value.elts):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    tuple_names.add(t.id)
            a, b = _span(offs, n.value)
            repls.append((a, b, "[]"))
    if not repls:
        return
    for n in ast.walk(fn):
        if (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
                and n.target.id in tuple_names and isinstance(n.op, ast.Add)):
            v = n.value
            if isinstance(v, ast.Tuple) and len(v.elts) == 1:
                a, b = _span(offs, v)
                repls.append((a, b, "[" + _seg(src, offs, v.elts[0]) + "]"))
            elif not isinstance(v, (ast.List, ast.Tuple)):
                a, b = _span(offs, v)
                repls.append((a, b, "[" + _seg(src, offs, v) + "]"))
        elif (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id in tuple_names
                and isinstance(n.value, ast.BinOp)
                and isinstance(n.value.op, ast.Add)):
            r = n.value.right
            if isinstance(r, ast.Tuple) and len(r.elts) == 1:
                a, b = _span(offs, r)
                repls.append((a, b, "[" + _seg(src, offs, r.elts[0]) + "]"))
            elif not isinstance(r, ast.List):
                a, b = _span(offs, r)
                repls.append((a, b, "[" + _seg(src, offs, r) + "]"))
    yield _apply(src, repls)


def _r_rename_def(src, tree, fn):
    """Misspelled function name: rename the def (and self-references)."""
    if fn.name == ENTRY:
        return
    offs = _offsets(src)
    lines = _lines(src)
    m = re.search(r"\bdef\s+(%s)\s*\(" % re.escape(fn.name),
                  lines[fn.lineno - 1])
    if not m:
        return
    start = offs[fn.lineno - 1] + m.start(1)
    repls = [(start, start + len(fn.name), ENTRY)]
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id == fn.name:
            a, b = _span(offs, n)
            repls.append((a, b, ENTRY))
    yield _apply(src, repls)


def _r_dedent_return(src, tree, fn):
    """`return` accidentally indented inside the loop: move the final
    return line out to a shallower block."""
    if not fn.body:
        return
    lines = _lines(src)
    body_indent = _indent_of(lines[fn.body[0].lineno - 1])
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and n.lineno == fn.end_lineno:
            ln = lines[n.lineno - 1]
            cur = _indent_of(ln)
            if len(cur) <= len(body_indent):
                continue
            levels = [body_indent]
            if cur.startswith("\t"):
                levels.append(cur[1:])
            else:
                levels.append(cur[:max(len(body_indent), len(cur) - 4)])
            seen = set()
            for ind in levels:
                if ind == cur or ind in seen:
                    continue
                seen.add(ind)
                nl = list(lines)
                nl[n.lineno - 1] = ind + ln.lstrip()
                yield "".join(nl)


def _r_pair_collect_fix(src, tree, fn):
    """Pair-counting duplicates (nested i/j loops appending lst[j] for every
    equal pair) over-collects for triples; students patch with `a[:-1]`.
    Correct fix: drop the `[:-1]` and `break` after the first match, so each
    occurrence contributes at most one removal."""
    offs = _offsets(src)
    lines = _lines(src)
    slice_repl = None
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Subscript):
            sl = n.value.slice
            if (isinstance(sl, ast.Slice) and sl.lower is None
                    and sl.step is None and isinstance(sl.upper, ast.UnaryOp)
                    and isinstance(sl.upper.op, ast.USub)
                    and isinstance(sl.upper.operand, ast.Constant)
                    and sl.upper.operand.value == 1):
                a, b = _span(offs, n.value)
                slice_repl = (a, b, _seg(src, offs, n.value.value))
    break_ins = None
    for outer in ast.walk(fn):
        if not isinstance(outer, ast.For):
            continue
        for inner in ast.walk(outer):
            if inner is outer or not isinstance(inner, ast.For):
                continue
            for node in ast.walk(inner):
                if not isinstance(node, ast.If):
                    continue
                for st in node.body:
                    acc = isinstance(st, ast.AugAssign) or (
                        isinstance(st, ast.Expr)
                        and isinstance(st.value, ast.Call)
                        and isinstance(st.value.func, ast.Attribute)
                        and st.value.func.attr == "append")
                    if acc:
                        ind = _indent_of(lines[st.lineno - 1])
                        break_ins = (st.end_lineno + 1, ind + "break")
    if slice_repl and break_ins:
        s2 = _apply(src, [slice_repl])
        yield _insert_lines(s2, break_ins[0], [break_ins[1]])
    if slice_repl:
        yield _apply(src, [slice_repl])
    if break_ins:
        yield _insert_lines(src, break_ins[0], [break_ins[1]])


def _r_count_to_membership(src, tree, fn):
    """`if lst.count(x) == 1: acc.append(x)` drops every duplicated value
    entirely; the intended guard is `x not in acc`."""
    offs = _offsets(src)
    if not fn.args.args:
        return
    p = fn.args.args[0].arg
    for n in ast.walk(fn):
        if not isinstance(n, ast.If):
            continue
        t = n.test
        if not (isinstance(t, ast.Compare) and len(t.ops) == 1):
            continue
        left = t.left
        if not (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                and left.func.attr == "count"
                and isinstance(left.func.value, ast.Name)
                and left.func.value.id == p and len(left.args) == 1):
            continue
        arg_src = _seg(src, offs, left.args[0])
        for st in n.body:
            acc = None
            if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                    and isinstance(st.value.func, ast.Attribute)
                    and st.value.func.attr == "append"
                    and isinstance(st.value.func.value, ast.Name)):
                acc = st.value.func.value.id
            elif isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name):
                acc = st.target.id
            if acc:
                a, b = _span(offs, t)
                yield _apply(src, [(a, b, arg_src + " not in " + acc)])
                break


def _r_if_while_swap(src, tree, fn):
    """Swap `if`/`while` on a count-guarded remove: one removal per visit
    vs. repeat-until-single are commonly confused."""
    offs = _offsets(src)
    for n in ast.walk(fn):
        if not isinstance(n, (ast.If, ast.While)):
            continue
        try:
            cond_src = _seg(src, offs, n.test)
        except Exception:
            continue
        has_remove = any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr in ("remove", "pop")
            for b in n.body for c in ast.walk(b))
        if ".count(" in cond_src and has_remove:
            kw = "if" if isinstance(n, ast.If) else "while"
            new_kw = "while" if kw == "if" else "if"
            a = offs[n.lineno - 1] + n.col_offset
            if src[a:a + len(kw)] == kw:
                yield src[:a] + new_kw + src[a + len(kw):]


def _r_reverse_wrap(src, tree, fn):
    """In-place `lst.remove(x)` while looping keeps the LAST occurrence
    (remove deletes the first).  Wrap the loop in reverse()/reverse() so the
    first occurrence survives; list ends in original order (idempotent)."""
    if not fn.args.args:
        return
    p = fn.args.args[0].arg
    lines = _lines(src)
    for st in fn.body:
        if not isinstance(st, ast.For):
            continue
        has_rm = any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
            and c.func.attr == "remove" and isinstance(c.func.value, ast.Name)
            and c.func.value.id == p for c in ast.walk(st))
        if not has_rm:
            continue
        ind = _indent_of(lines[st.lineno - 1])
        rev = ind + p + ".reverse()"
        s2 = _insert_lines(src, st.end_lineno + 1, [rev])
        s2 = _insert_lines(s2, st.lineno, [rev])
        yield s2
        t2 = _parse(s2)
        f2 = _func(t2) if t2 else None
        if f2:
            for c in _r_if_while_swap(s2, t2, f2):
                yield c


def _r_set_order(src, tree, fn):
    """`list(set(lst))` loses order: keep first-occurrence order via
    sorted(..., key=lst.index)."""
    offs = _offsets(src)
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "list" and len(n.args) == 1
                and isinstance(n.args[0], ast.Call)
                and isinstance(n.args[0].func, ast.Name)
                and n.args[0].func.id == "set" and len(n.args[0].args) == 1
                and isinstance(n.args[0].args[0], ast.Name)):
            inner = n.args[0].args[0].id
            a, b = _span(offs, n)
            yield _apply(src, [(a, b, "sorted(set(%s), key=%s.index)"
                                % (inner, inner))])


def _r_init_empty(src, tree, fn):
    """Accumulator wrongly initialised from the input (`new = lst`):
    try starting it empty."""
    offs = _offsets(src)
    params = {a.arg for a in fn.args.args}
    for st in fn.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)):
            uses_param = any(isinstance(x, ast.Name) and x.id in params
                             for x in ast.walk(st.value))
            if uses_param:
                a, b = _span(offs, st.value)
                yield _apply(src, [(a, b, "[]")])


ALL_RULES = [_r_fix_return, _r_print_to_return, _r_mutator_as_value,
             _r_tuple_to_list, _r_rename_def, _r_dedent_return,
             _r_pair_collect_fix, _r_count_to_membership, _r_if_while_swap,
             _r_reverse_wrap, _r_set_order, _r_init_empty]

STAGE2_RULES = (_r_fix_return, _r_if_while_swap, _r_mutator_as_value,
                _r_tuple_to_list, _r_count_to_membership)


# ------------------------------------------------- dispatch and pipeline


def _ordered_rules(res):
    """Reorder rules by the observed failure pattern."""
    front = []
    try:
        fails = list(getattr(res, "failures", []) or []) if res is not None else []
        errs = " ".join(str(f.get("error")) for f in fails if f.get("error"))
        gots = [f.get("got") for f in fails]
        exps = [f.get("expected") for f in fails]
        if res is not None and not getattr(res, "compiled", True):
            front.append(_r_rename_def)
        if "not defined" in errs or "NameError" in errs:
            front.append(_r_rename_def)
        if "NoneType" in errs or any(g is None for g in gots):
            front += [_r_mutator_as_value, _r_fix_return, _r_print_to_return]
        if "tuple" in errs or any(isinstance(g, tuple) for g in gots):
            front.append(_r_tuple_to_list)
        if any(isinstance(g, list) and isinstance(e, list) and g != e
               and sorted(map(repr, g)) == sorted(map(repr, e))
               for g, e in zip(gots, exps)):
            front += [_r_reverse_wrap, _r_if_while_swap]
        if any(isinstance(g, list) and isinstance(e, list) and len(g) > len(e)
               for g, e in zip(gots, exps)):
            front += [_r_pair_collect_fix, _r_if_while_swap]
    except Exception:
        front = []
    out, seen = [], set()
    for r in front + ALL_RULES:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _rule_candidates(src, tree, fn, rules, seen):
    out = []
    for rule in rules:
        try:
            for c in rule(src, tree, fn):
                if isinstance(c, str) and c not in seen and _parse(c) is not None:
                    seen.add(c)
                    out.append(c)
        except Exception:
            continue
    return out


def _stage2(stage1, seen):
    """Pairs of misconceptions: re-apply key rules on top of stage-1 fixes."""
    out = []
    for c in stage1[:20]:
        t = _parse(c)
        f = _func(t) if t else None
        if not f:
            continue
        for rule in STAGE2_RULES:
            try:
                for c2 in rule(c, t, f):
                    if isinstance(c2, str) and c2 not in seen and _parse(c2):
                        seen.add(c2)
                        out.append(c2)
                        if len(out) >= 60:
                            return out
            except Exception:
                continue
    return out


def _prefilter(source, cands):
    out = []
    for c in cands:
        try:
            if rps(source, c) <= MAX_RPS:
                out.append(c)
        except Exception:
            out.append(c)
    return out


def _promising(cands, base_fail):
    scored = []
    for c in cands[:20]:
        try:
            r = failing_tests(c, ENTRY, TESTS)
            if getattr(r, "compiled", False):
                nf = len(getattr(r, "failures", []) or [])
                if 0 < nf and (base_fail is None or nf <= base_fail):
                    scored.append((nf, c))
        except Exception:
            pass
    scored.sort(key=lambda x: x[0])
    return [c for _, c in scored]


def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    tree = _parse(source)
    if tree is None:
        return None
    fn = _func(tree)
    if fn is None:
        return None
    t0 = time.time()

    def left():
        return 9.0 - (time.time() - t0)

    def check(cands, max_checks=300):
        try:
            return first_passing(iter(cands), ENTRY, TESTS, source,
                                 max_rps=MAX_RPS, max_checks=max_checks)
        except Exception:
            return None

    fixed = check([source], max_checks=2)
    if fixed is not None:
        return fixed

    try:
        res = failing_tests(source, ENTRY, TESTS)
    except Exception:
        res = None

    seen = {source}
    stage1 = _rule_candidates(source, tree, fn, _ordered_rules(res), seen)
    stage1 = _prefilter(source, stage1)
    fixed = check(stage1, max_checks=len(stage1) + 2)
    if fixed is not None or left() < 0.5:
        return fixed

    stage2 = _prefilter(source, _stage2(stage1, seen))
    fixed = check(stage2, max_checks=len(stage2) + 2)
    if fixed is not None or left() < 0.5:
        return fixed

    fixed = check(candidates_generic(source, max_edits=1), max_checks=400)
    if fixed is not None or left() < 1.0:
        return fixed

    base_fail = None
    if res is not None:
        try:
            base_fail = len(getattr(res, "failures", []) or [])
        except Exception:
            base_fail = None
    promising = _promising(stage1 + stage2, base_fail)
    gens = [candidates_generic(c, max_edits=1, budget=300)
            for c in promising[:4]]
    if gens and left() > 1.0:
        fixed = check(chain(*gens), max_checks=240)
        if fixed is not None:
            return fixed

    if left() > 1.5:
        return check(candidates_generic(source, max_edits=2, budget=1500),
                     max_checks=350)
    return None


def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None
