You previously wrote the following per-assignment repair module for the assignment "refactory_q4":

```python
"""Local, LLM-free automatic repair for the 'Sorting Tuples' (sort_age) task.

Strategy: problem-specific rewrite rules for the misconceptions typical of
this assignment (ascending instead of descending order, min/max confusion,
print-instead-of-return, missing or misplaced return, `return lst.reverse()`,
tracking ages instead of person elements, broken pop/insert insertion sort),
composed with the generic mutation search. Every candidate is validated by
`first_passing`, which enforces the visible tests and the 0.35 RPS cap.
All rewrites splice text at exact AST spans so untouched lines stay
byte-identical to the student's code.
"""

import ast
import itertools

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401  (documented helper API)

ENTRY = "sort_age"

TESTS = [
    {"args": [[["F", 19]]], "expected": [["F", 19]]},
    {"args": [[["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]],
     "expected": [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]],
     "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30]]],
     "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18]]},
    {"args": [[["M", 23], ["F", 19], ["M", 30]]],
     "expected": [["M", 30], ["M", 23], ["F", 19]]},
    {"args": [[]], "expected": []},
]


# ---------------------------------------------------------------- utilities

def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


def _func(tree, name=ENTRY):
    if tree is None:
        return None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _line_starts(src):
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _span(src, node, starts):
    a = starts[node.lineno - 1] + node.col_offset
    b = starts[node.end_lineno - 1] + node.end_col_offset
    return a, b


def _apply(src, edits):
    """Apply (start, end, text) edits given in original coordinates."""
    out = src
    for a, b, t in sorted(edits, key=lambda e: (-e[0], -e[1])):
        out = out[:a] + t + out[b:]
    return out


def _result_names(f):
    """Likely result variables: append targets, list inits, then params."""
    appended, inits = [], []
    for n in ast.walk(f):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "append"
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id not in appended):
            appended.append(n.func.value.id)
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, (ast.List, ast.ListComp))
                and n.targets[0].id not in inits):
            inits.append(n.targets[0].id)
    out = []
    for nm in appended + inits + [a.arg for a in f.args.args]:
        if nm not in out:
            out.append(nm)
    return out


def _flip_cmp_edit(src, starts, c):
    """Edit flipping the single comparison operator of Compare `c`."""
    if len(c.ops) != 1:
        return None
    _, lb = _span(src, c.left, starts)
    ra, _ = _span(src, c.comparators[0], starts)
    mid = src[lb:ra]
    for old, new in (("<=", ">="), (">=", "<="), ("<", ">"), (">", "<")):
        i = mid.find(old)
        if i >= 0:
            return (lb + i, lb + i + len(old), new)
    return None


# ------------------------------------------------------- structural rules

def g_print_to_return(src):
    """print(x) as a statement -> return x  (last print first)."""
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    prints = [n for n in ast.walk(f)
              if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
              and isinstance(n.value.func, ast.Name)
              and n.value.func.id == "print"
              and len(n.value.args) == 1 and not n.value.keywords]
    for p in reversed(prints):
        a, b = _span(src, p.value, starts)
        aa, ab = _span(src, p.value.args[0], starts)
        yield _apply(src, [(a, b, "return " + src[aa:ab])])


def g_fix_return_mutator(src):
    """return L.reverse()/L.sort(...) -> mutate then return L (+ variants)."""
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    for n in ast.walk(f):
        if not (isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr in ("reverse", "sort")):
            continue
        a, b = _span(src, n, starts)
        ca, cb = _span(src, n.value, starts)
        oa, ob = _span(src, n.value.func.value, starts)
        obj, callsrc = src[oa:ob], src[ca:cb]
        ind = " " * n.col_offset
        yield _apply(src, [(a, b, callsrc + "\n" + ind + "return " + obj)])
        if n.value.func.attr == "reverse" and not n.value.args:
            yield _apply(src, [(a, b, "return " + obj + "[::-1]")])
        if n.value.func.attr == "sort" and callsrc.endswith(")"):
            kw = {k.arg for k in n.value.keywords}
            if "key" not in kw and "reverse" not in kw:
                pre = ", " if (n.value.args or n.value.keywords) else ""
                aug = callsrc[:-1] + pre + "key=lambda x: x[1], reverse=True)"
                yield _apply(src, [(a, b, aug + "\n" + ind + "return " + obj)])


def _split_return_mutator_edits(src, f, starts):
    for n in ast.walk(f):
        if (isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr in ("reverse", "sort")):
            a, b = _span(src, n, starts)
            ca, cb = _span(src, n.value, starts)
            oa, ob = _span(src, n.value.func.value, starts)
            ind = " " * n.col_offset
            return [(a, b, src[ca:cb] + "\n" + ind + "return " + src[oa:ob])]
    return []


def g_move_return(src):
    """A return nested inside a loop -> move it to end of function body."""
    f = _func(_parse(src))
    if not f or not f.body:
        return
    starts = _line_starts(src)
    top = {id(s) for s in f.body}
    ind = " " * f.body[0].col_offset
    for n in ast.walk(f):
        if (isinstance(n, ast.Return) and id(n) not in top
                and n.value is not None and n.lineno == n.end_lineno):
            va, vb = _span(src, n.value, starts)
            expr = src[va:vb]
            ls, le = starts[n.lineno - 1], starts[n.end_lineno]
            trimmed = src[:ls] + src[le:]
            if not trimmed.endswith("\n"):
                trimmed += "\n"
            yield trimmed + ind + "return " + expr + "\n"


def g_add_return(src):
    """No trailing return -> append `return <accumulator>` at body indent."""
    f = _func(_parse(src))
    if not f or not f.body or isinstance(f.body[-1], ast.Return):
        return
    ind = " " * f.body[0].col_offset
    base = src if src.endswith("\n") else src + "\n"
    for nm in _result_names(f)[:4]:
        yield base + ind + "return " + nm + "\n"


def g_swap_return_name(src):
    """`return lst` where the result was built in another variable."""
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    names = _result_names(f)[:4]
    for n in ast.walk(f):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Name):
            a, b = _span(src, n.value, starts)
            for nm in names:
                if nm != n.value.id:
                    yield _apply(src, [(a, b, nm)])


def g_strip_subscript_arg(src):
    """remove(x[1]) / append(x[1]) -> remove(x) / append(x)."""
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    for n in ast.walk(f):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("remove", "append") and len(n.args) == 1
                and isinstance(n.args[0], ast.Subscript)
                and isinstance(n.args[0].slice, ast.Constant)):
            a, b = _span(src, n.args[0], starts)
            ia, ib = _span(src, n.args[0].value, starts)
            yield _apply(src, [(a, b, src[ia:ib])])


# ------------------------------------------------------ ordering rules

def g_minmax(src):
    """Swap min<->max (all sites together, then each site alone)."""
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    sites = [n for n in ast.walk(f)
             if isinstance(n, ast.Name) and n.id in ("min", "max")]
    if not sites:
        return
    other = {"min": "max", "max": "min"}
    edits = []
    for n in sites:
        a, b = _span(src, n, starts)
        edits.append((a, b, other[n.id]))
    yield _apply(src, edits)
    if 1 < len(sites) <= 4:
        for a, b, t in edits:
            yield _apply(src, [(a, b, t)])


def g_reverse_return(src):
    """Ascending result -> return <expr>[::-1]."""
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    for n in ast.walk(f):
        if (isinstance(n, ast.Return)
                and isinstance(n.value, (ast.Name, ast.Subscript, ast.Call))):
            a, b = _span(src, n.value, starts)
            expr = src[a:b]
            if not expr.endswith("[::-1]"):
                yield _apply(src, [(a, b, expr + "[::-1]")])


def g_sortcall(src):
    """Add key=lambda x: x[1] / reverse=True to sorted(...) or .sort(...)."""
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    for n in ast.walk(f):
        if not isinstance(n, ast.Call):
            continue
        is_sorted = isinstance(n.func, ast.Name) and n.func.id == "sorted"
        is_sort = isinstance(n.func, ast.Attribute) and n.func.attr == "sort"
        if not (is_sorted or is_sort):
            continue
        a, b = _span(src, n, starts)
        if b <= a or src[b - 1] != ")":
            continue
        kw = {k.arg for k in n.keywords}
        pre = ", " if (n.args or n.keywords) else ""
        adds = []
        if "key" not in kw and "reverse" not in kw:
            adds.append("key=lambda x: x[1], reverse=True")
        if "reverse" not in kw:
            adds.append("reverse=True")
        if "key" not in kw:
            adds.append("key=lambda x: x[1]")
        for add in adds:
            yield src[:b - 1] + pre + add + src[b - 1:]


# --------------------------------------------------- deep pattern rules

def g_track_element(src):
    """Student tracks the AGE (v = elem[1]) but removes/appends v.

    Rewrite to track the element: strip the trailing [1] from assignments,
    compare v[1] instead of v, optionally move a pre-loop init inside the
    `while` loop, and optionally flip the comparison to select the oldest.
    """
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    by_name = {}
    for n in ast.walk(f):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Subscript)
                and isinstance(n.value.slice, ast.Constant)
                and n.value.slice.value == 1):
            by_name.setdefault(n.targets[0].id, []).append(n)
    consumed = set()
    for n in ast.walk(f):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("remove", "append") and len(n.args) == 1
                and isinstance(n.args[0], ast.Name)):
            consumed.add(n.args[0].id)
    for name, asgs in by_name.items():
        if name not in consumed:
            continue
        strips = {}
        for a_node in asgs:
            va, vb = _span(src, a_node.value, starts)
            ia, ib = _span(src, a_node.value.value, starts)
            strips[id(a_node)] = (va, vb, src[ia:ib])
        wraps, flips = [], []
        for c in ast.walk(f):
            if not isinstance(c, ast.Compare):
                continue
            hit = False
            for side in [c.left] + c.comparators:
                if isinstance(side, ast.Name) and side.id == name:
                    sa, sb = _span(src, side, starts)
                    wraps.append((sa, sb, name + "[1]"))
                    hit = True
            if hit:
                fe = _flip_cmp_edit(src, starts, c)
                if fe:
                    flips.append(fe)
        wh = next((s for s in f.body if isinstance(s, ast.While)), None)
        init = next((a_ for a_ in asgs if a_ in f.body), None)
        variants = []
        if (wh is not None and wh.body and init is not None
                and init.end_lineno < wh.lineno
                and init.lineno == init.end_lineno):
            ls, le = starts[init.lineno - 1], starts[init.end_lineno]
            ia, ib = _span(src, init.value.value, starts)
            new_line = (" " * wh.body[0].col_offset + name + " = "
                        + src[ia:ib] + "\n")
            ins = starts[wh.body[0].lineno - 1]
            move = [(ls, le, ""), (ins, ins, new_line)]
            move += [strips[id(a_)] for a_ in asgs if a_ is not init]
            variants.append(move + wraps + flips)
            variants.append(move + wraps)
        allstrip = list(strips.values())
        variants.append(allstrip + wraps + flips)
        variants.append(allstrip + wraps)
        for edits in variants:
            yield _apply(src, edits)


def g_insertion_fix(src):
    """Broken insertion-sort idiom:

        while L[i][1] < L[i-1][1]:
            L.pop(i)
            L.insert(i-1, L[i])

    -> guard `i and`, combine into L.insert(i-1, L.pop(i)), decrement i;
    also split any trailing `return L.reverse()`.
    """
    f = _func(_parse(src))
    if not f:
        return
    starts = _line_starts(src)
    for wh in ast.walk(f):
        if not (isinstance(wh, ast.While) and len(wh.body) == 2):
            continue
        calls = {}
        for st in wh.body:
            if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                    and isinstance(st.value.func, ast.Attribute)
                    and isinstance(st.value.func.value, ast.Name)):
                calls[st.value.func.attr] = st.value
        if set(calls) != {"pop", "insert"}:
            continue
        pop_c, ins_c = calls["pop"], calls["insert"]
        L = pop_c.func.value.id
        if not (len(pop_c.args) == 1 and isinstance(pop_c.args[0], ast.Name)
                and len(ins_c.args) == 2):
            continue
        ivar = pop_c.args[0].id
        pa, pb = _span(src, ins_c.args[0], starts)
        ind = " " * wh.body[0].col_offset
        body_a = starts[wh.body[0].lineno - 1]
        body_b = starts[wh.body[-1].end_lineno]
        new_body = (ind + L + ".insert(" + src[pa:pb] + "," + L + ".pop("
                    + ivar + "))\n" + ind + ivar + " -= 1\n")
        ta, _ = _span(src, wh.test, starts)
        edits = [(body_a, body_b, new_body), (ta, ta, ivar + " and ")]
        extra = _split_return_mutator_edits(src, f, starts)
        if extra:
            yield _apply(src, edits + extra)
        yield _apply(src, edits)


# ------------------------------------------------------------ dispatcher

def _looks_reversed(res):
    try:
        if not getattr(res, "compiled", False):
            return False
        for fl in res.failures:
            exp, got = fl.get("expected"), fl.get("got")
            if isinstance(exp, list) and len(exp) > 1 and got == exp[::-1]:
                return True
    except Exception:
        pass
    return False


def _targeted(src, order_first):
    out, seen = [], {src}

    def add(gen):
        try:
            for cand in gen:
                if (isinstance(cand, str) and cand not in seen
                        and _parse(cand) is not None):
                    seen.add(cand)
                    out.append(cand)
        except Exception:
            pass

    structural = (g_print_to_return, g_fix_return_mutator, g_move_return,
                  g_swap_return_name, g_add_return, g_strip_subscript_arg)
    orderers = (g_minmax, g_reverse_return, g_sortcall)
    first, second = (orderers, structural) if order_first else (structural,
                                                                orderers)
    for g in first:
        add(g(src))
    for g in second:
        add(g(src))
    add(g_track_element(src))
    add(g_insertion_fix(src))
    # Compose: apply each rule family on top of the first-round candidates,
    # so e.g. print->return combines with a min/max swap or a reversal.
    for t in list(out)[:8]:
        for g in structural + orderers:
            add(g(t))
    return out[:100]


def _repair(src):
    if _parse(src) is None:
        return None
    order_first = False
    try:
        res = failing_tests(src, ENTRY, TESTS)
        if getattr(res, "compiled", False) and res.passed == res.total:
            hit = first_passing(iter([src]), ENTRY, TESTS, src,
                                max_rps=0.35, max_checks=5)
            if hit is not None:
                return hit
        order_first = _looks_reversed(res)
    except Exception:
        pass

    targeted = _targeted(src, order_first)

    def followups():
        # Safety net: one generic edit on top of the best targeted rewrites.
        for t in targeted[:8]:
            try:
                yield from itertools.islice(
                    candidates_generic(t, max_edits=1), 150)
            except Exception:
                return

    cands = chain(
        iter(targeted),
        candidates_generic(src, max_edits=1),
        followups(),
        candidates_generic(src, max_edits=2, budget=1200),
    )
    return first_passing(cands, ENTRY, TESTS, src,
                         max_rps=0.35, max_checks=800)


def repair(source: str) -> "str | None":
    try:
        return _repair(source)
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- real_146.py: NOT REPAIRED — no_patch
- real_186.py: NOT REPAIRED — no_patch
- real_202.py: NOT REPAIRED — no_patch
- real_334.py: NOT REPAIRED — no_patch
- real_344.py: NOT REPAIRED — no_patch

For reference, the submissions the module failed on:

### Failed submission real_146.py
```python
def sort_age(lst):
    youngest = lst[0][1]
    sorted = []
    while lst:
        for elem in lst:
            if elem[1] < youngest:
                youngest = elem[1]
        lst.remove(youngest)
        sorted.append(youngest)
    return sorted

```

### Failed submission real_186.py
```python
def sort_age(lst):
    a = lst
    sort = []
    while a:
        largest = a[0]
        for item in a:
            if item[1] >largest[1]:
                largest = item
        a.remove(largest)
        sort.append(largest)

    print(sort)# Fill in your code here
    

```

### Failed submission real_202.py
```python
def sort_age(lst):
    decoy = []
    decoy2 = []
    final = []
    for i in lst:
        decoy.append(i[1])
    while decoy != []:
        decoy2.append(min(decoy))
        decoy.remove(min(decoy))
    for i in decoy2:
        for j in lst:
            if i == j[1]:
                final.append(j)
    return final
    
    

```

### Failed submission real_334.py
```python
def sort_age(lst):
    for i in range(1,len(lst)):
        while lst[i][1]<lst[i-1][1]:
            lst.pop(i)
            lst.insert(i-1,lst[i])# Fill in your code here
    return lst.reverse()

```

### Failed submission real_344.py
```python
def sort_age(lst):
    current=0
    tup=()
    for i in lst:
        if i[1]>current:
            tup+=tuple(i)
            current=i[1]
        else:
            tuple(i)+tup
    return tup
            

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
