```python
"""Local, LLM-free automatic repair for the Top-K assignment.

Strategy:
  1. Run the buggy program on the visible tests (with a trace-based step
     limiter so infinite loops cannot hang us) and classify the failure
     pattern.
  2. Generate problem-specific candidate rewrites (AST-located, surgical
     string edits so the rest of the student's code stays byte-identical):
       - strip tuple-style subscripts in comparisons (code copied from a
         "sort by age" exercise:  i[1] > big[1]  ->  i > big)
       - wrap the returned value with [:k] and/or [::-1]
       - swap min/max
       - split  acc.append(lst.remove(max(lst)))  into append + remove
       - rewrite broken while-conditions to  len(acc) < k
       - fix range(...) argument to k / len(lst)
       - swap "append; if len==k: break" into "check; append"
       - dedent a return that sits at the end of a loop body
       - insert a missing lst.remove(max(lst)) after append(max(lst))
       - return a different accumulator variable
       - swap the two parameters / rename a mis-named function
       - complete a one-level pivot partition that a submission used as a
         full sort:  lower + plist + higher  only partitions once around
         lst[0], so the < and > parts stay unsorted; emit
         sorted(lower) + plist + sorted(higher), alone and combined with
         the off-by-one slice fix below (real_016 needs both edits at
         once, which is why single specific rewrites and 1-2 generic
         edits could not repair it)
       - fix off-by-one slice bounds  x[:k-1] / x[:k+1]  ->  x[:k]
  3. Try singles, then pairs of specific rewrites, then the generic edit
     search (1 edit, specific+generic, 2 edits), pre-screening every
     candidate with the step-limited runner and the rps cap, and always
     confirming the winner through first_passing.
"""

import ast
import contextlib
import copy
import io
import re
import sys
import time

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

_IDX = getattr(ast, "Index", ())


class _Abort(Exception):
    pass


# --------------------------------------------------------------------------
# Sandboxed, step-limited execution of candidate programs
# --------------------------------------------------------------------------

def _run_tests(src, limit=120000):
    """Run src on TESTS.  Returns list of (ok, got, err) or None."""
    try:
        code = compile(src, "<cand>", "exec")
    except BaseException:
        return None
    ns = {"input": lambda *a, **k: ""}
    count = [0]

    def tracer(frame, event, arg):
        count[0] += 1
        if count[0] > limit:
            raise _Abort()
        return tracer

    old = sys.gettrace()
    res = []
    sink = io.StringIO()
    try:
        sys.settrace(tracer)
        try:
            with contextlib.redirect_stdout(sink):
                exec(code, ns)
        except BaseException:
            return None
        f = ns.get(ENTRY)
        if not callable(f):
            return None
        for t in TESTS:
            count[0] = 0
            sys.settrace(tracer)  # re-arm (a raising tracer disables itself)
            try:
                with contextlib.redirect_stdout(sink):
                    got = f(*copy.deepcopy(t["args"]))
                try:
                    ok = bool(got == t["expected"])
                except BaseException:
                    ok = False
                res.append((ok, got, None))
            except BaseException as e:
                res.append((False, None, repr(e)))
        return res
    finally:
        sys.settrace(old)


def _quick_ok(src):
    r = _run_tests(src)
    return bool(r) and all(x[0] for x in r)


# --------------------------------------------------------------------------
# Surgical source editing keyed on AST byte offsets
# --------------------------------------------------------------------------

class _Src:
    def __init__(self, text):
        self.text = text
        self.b = text.encode("utf-8")
        self.starts = [0]
        for ln in text.split("\n"):
            self.starts.append(self.starts[-1] + len(ln.encode("utf-8")) + 1)

    def pos(self, lineno, col):
        return self.starts[lineno - 1] + col

    def span(self, node):
        return (self.pos(node.lineno, node.col_offset),
                self.pos(node.end_lineno, node.end_col_offset))

    def seg(self, node):
        a, b = self.span(node)
        return self.b[a:b].decode("utf-8")

    def replace(self, repls):
        spans = []
        for n, t in repls:
            a, b = self.span(n) if isinstance(n, ast.AST) else n
            spans.append((a, b, t))
        spans.sort(key=lambda x: (x[0], x[1]))
        filt, last = [], -1
        for a, b, t in spans:
            if a < last:
                continue
            filt.append((a, b, t))
            last = b
        bb = self.b
        for a, b, t in reversed(filt):
            bb = bb[:a] + t.encode("utf-8") + bb[b:]
        return bb.decode("utf-8")


def _topk(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == ENTRY:
            return n
    return None


def _deslice(sl):
    if _IDX and isinstance(sl, _IDX):
        return getattr(sl, "value", sl)
    return sl


def _kname(fn):
    if fn is not None and len(fn.args.args) >= 2:
        return fn.args.args[1].arg
    return "k"


def _lname(fn):
    if fn is not None and len(fn.args.args) >= 1:
        return fn.args.args[0].arg
    return "lst"


def _accs(fn):
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.ListComp)):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id not in out:
                    out.append(t.id)
    return out


# --------------------------------------------------------------------------
# Problem-specific rewrite rules (each: src -> list of candidate sources)
# --------------------------------------------------------------------------

def r_subscript_cmp(src):
    """i[1] > big[1]  ->  i > big  (tuple-sort code reused for plain ints)."""
    tree = ast.parse(src)
    S = _Src(src)
    subs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for side in [node.left] + list(node.comparators):
                if isinstance(side, ast.Subscript) and isinstance(side.value, ast.Name):
                    sl = _deslice(side.slice)
                    if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
                        subs.append(side)
    if not subs:
        return []
    return [S.replace([(n, S.seg(n.value)) for n in subs])]


def r_return_wrap(src):
    """return X  ->  return X[:k] / X[::-1] / both orders."""
    tree = ast.parse(src)
    S = _Src(src)
    fn = _topk(tree)
    if fn is None:
        return []
    k = _kname(fn)
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and node.value is not None:
            v = node.value
            if isinstance(v, ast.Constant):
                continue
            seg = S.seg(v)
            simple = isinstance(v, (ast.Name, ast.Subscript, ast.Call,
                                    ast.Attribute, ast.List))
            base = seg if simple else "(" + seg + ")"
            for suf in ("[:%s]" % k, "[::-1]",
                        "[:%s][::-1]" % k, "[::-1][:%s]" % k):
                out.append(S.replace([(v, base + suf)]))
    return out[:16]


def r_minmax(src):
    tree = ast.parse(src)
    S = _Src(src)
    names = [n for n in ast.walk(tree)
             if isinstance(n, ast.Name) and n.id in ("min", "max")]
    if not names:
        return []
    out = [S.replace([(n, "max" if n.id == "min" else "min") for n in names])]
    for n in names[:8]:
        out.append(S.replace([(n, "max" if n.id == "min" else "min")]))
    return out


def r_append_split(src):
    """acc.append(lst.remove(X))  ->  acc.append(X); lst.remove(X)."""
    tree = ast.parse(src)
    S = _Src(src)
    lines = src.split("\n")
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            continue
        c = node.value
        if not (isinstance(c.func, ast.Attribute) and c.func.attr == "append"
                and len(c.args) == 1 and isinstance(c.args[0], ast.Call)):
            continue
        inner = c.args[0]
        if not (isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "remove" and len(inner.args) == 1):
            continue
        A = S.seg(c.func.value)
        B = S.seg(inner.func.value)
        C = S.seg(inner.args[0])
        line = lines[node.lineno - 1]
        indent = line[: len(line) - len(line.lstrip())]
        new = "%s.append(%s)\n%s%s.remove(%s)" % (A, C, indent, B, C)
        out.append(S.replace([(node, new)]))
    return out[:6]


def r_while_cond(src):
    """Rewrite a while condition to  len(acc) < k  (optionally 'lst and ...')."""
    tree = ast.parse(src)
    S = _Src(src)
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if len(fn.args.args) < 2:
            continue
        p0, p1 = fn.args.args[0].arg, fn.args.args[1].arg
        accs = _accs(fn)
        for node in ast.walk(fn):
            if isinstance(node, ast.While):
                cur = S.seg(node.test)
                for acc in accs:
                    for new in ("len(%s) < %s" % (acc, p1),
                                "%s and len(%s) < %s" % (p0, acc, p1)):
                        if new != cur:
                            out.append(S.replace([(node.test, new)]))
    return out[:16]


def r_range_k(src):
    tree = ast.parse(src)
    S = _Src(src)
    fn = _topk(tree)
    if fn is None or len(fn.args.args) < 2:
        return []
    l0, k = _lname(fn), _kname(fn)
    out = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "range" and len(node.args) == 1):
            cur = S.seg(node.args[0])
            for na in (k, "len(%s)" % l0, "min(%s, len(%s))" % (k, l0)):
                if na != cur:
                    out.append(S.replace([(node.args[0], na)]))
    return out[:9]


def r_swap_stmts(src):
    """[acc.append(x); if len(acc)==k: break]  ->  check before append."""
    tree = ast.parse(src)
    lines = src.split("\n")
    out = []
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        body = loop.body
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if not (isinstance(a, ast.Expr) and isinstance(a.value, ast.Call)
                    and isinstance(a.value.func, ast.Attribute)
                    and a.value.func.attr == "append"):
                continue
            if not (isinstance(b, ast.If)
                    and any(isinstance(x, ast.Break) for x in ast.walk(b))):
                continue
            la, ea = a.lineno - 1, a.end_lineno - 1
            lb, eb = b.lineno - 1, b.end_lineno - 1
            if ea < lb:
                nl = (lines[:la] + lines[lb:eb + 1]
                      + lines[la:ea + 1] + lines[eb + 1:])
                out.append("\n".join(nl))
    return out[:6]


def r_return_dedent(src):
    """Move a return that ends a loop body to just after the loop."""
    tree = ast.parse(src)
    lines = src.split("\n")
    out = []
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        if getattr(loop, "orelse", None):
            continue
        tgts = []
        if loop.body and isinstance(loop.body[-1], ast.Return):
            tgts.append(loop.body[-1])
        if (loop.body and isinstance(loop.body[-1], ast.If)
                and not loop.body[-1].orelse and loop.body[-1].body
                and isinstance(loop.body[-1].body[-1], ast.Return)):
            tgts.append(loop.body[-1].body[-1])
        for tgt in tgts:
            lr, er = tgt.lineno - 1, tgt.end_lineno - 1
            if lr != er:
                continue
            loopline = lines[loop.lineno - 1]
            indent = loopline[: len(loopline) - len(loopline.lstrip())]
            new = lines[:lr] + lines[lr + 1:]
            new.insert(loop.end_lineno - 1, indent + lines[lr].strip())
            out.append("\n".join(new))
    return out[:6]


def r_insert_remove(src):
    """Insert missing  X.remove(max(X))  after  acc.append(max(X))."""
    tree = ast.parse(src)
    lines = src.split("\n")
    out = []
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        rem = set()
        for n in ast.walk(loop):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("remove", "pop", "discard")
                    and isinstance(n.func.value, ast.Name)):
                rem.add(n.func.value.id)
        for st in ast.walk(loop):
            if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)):
                continue
            c = st.value
            if not (isinstance(c.func, ast.Attribute) and c.func.attr == "append"
                    and len(c.args) == 1):
                continue
            a0 = c.args[0]
            if (isinstance(a0, ast.Call) and isinstance(a0.func, ast.Name)
                    and a0.func.id in ("max", "min") and len(a0.args) == 1
                    and isinstance(a0.args[0], ast.Name)):
                X, f = a0.args[0].id, a0.func.id
                if X in rem:
                    continue
                line = lines[st.lineno - 1]
                indent = line[: len(line) - len(line.lstrip())]
                nl = (lines[:st.end_lineno]
                      + [indent + "%s.remove(%s(%s))" % (X, f, X)]
                      + lines[st.end_lineno:])
                out.append("\n".join(nl))
    return out[:6]


def r_return_var(src):
    """return X  ->  return Y (another accumulator), optionally sliced."""
    tree = ast.parse(src)
    S = _Src(src)
    fn = _topk(tree)
    if fn is None:
        return []
    k = _kname(fn)
    names = _accs(fn)
    if fn.args.args:
        names = names + [fn.args.args[0].arg]
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            cur = node.value.id
            for nm in names:
                if nm != cur:
                    out.append(S.replace([(node.value, nm)]))
                    out.append(S.replace([(node.value, "%s[:%s]" % (nm, k))]))
    return out[:12]


def r_swap_params(src):
    tree = ast.parse(src)
    S = _Src(src)
    fn = _topk(tree)
    if fn is None or len(fn.args.args) != 2:
        return []
    a, b = fn.args.args
    try:
        return [S.replace([(a, b.arg), (b, a.arg)])]
    except Exception:
        return []


def r_rename(src):
    tree = ast.parse(src)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not fns or any(f.name == ENTRY for f in fns):
        return []
    out = []
    for f in fns:
        if len(f.args.args) >= 2:
            out.append(re.sub(r"\b%s\b" % re.escape(f.name), ENTRY, src))
    return out[:3]


# --------------------------------------------------------------------------
# New rules for the one-level pivot-partition family (real_016).
#
# Hand trace of real_016 on the visible tests: pivot = lst[0] and a single
# partition pass build  lower / plist / higher, but the sub-lists are never
# sorted, so  sort_list = lower + plist + higher  is not a sorted list.
#   test 1: lower=[4,7,3,1,6] -> reversed concat [:5] = [9,9,9,9,6]  (exp 7)
#   test 2: lower=[8,4,5,7,2,3,1,6] -> [9,6,1,3,2]                   (exp [9,8,7,6,5])
#   test 3: k==len(lst) branch returns sort_list[:k-1] -> 5 elements (exp 6),
#           and the list is unsorted anyway.
# The repair needs TWO coordinated edits at different sites:
#   sort_list = sorted(lower) + plist + sorted(higher)   (complete the sort)
#   return sort_list[:k]                                 (drop the -1)
# No previous rule could synthesise sorted(...) wrappers, and the generic
# 1-2 edit search cannot invent them either, so no candidate ever passed.
# r_partition_sort emits that exact corrected source (byte-identical outside
# the two spans, comfortably under the 0.35 rps cap) plus generalisations.
# --------------------------------------------------------------------------

def _add_chain(node):
    """Flatten  a + b + c  into [a, b, c] when every operand is a Name."""
    parts = []

    def walk(n):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            return walk(n.left) and walk(n.right)
        if isinstance(n, ast.Name):
            parts.append(n)
            return True
        return False

    return parts if walk(node) else []


def _append_guards(fn):
    """Map accumulator name -> comparison-op class guarding its append."""
    g = {}
    for n in ast.walk(fn):
        if not (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                and len(n.test.ops) == 1):
            continue
        for st in n.body:
            if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                    and isinstance(st.value.func, ast.Attribute)
                    and st.value.func.attr == "append"
                    and isinstance(st.value.func.value, ast.Name)):
                g.setdefault(st.value.func.value.id, type(n.test.ops[0]))
    return g


def _off1_slices(root, S):
    """[(upper-node, fixed-text)] for slices like  x[:k-1]  or  x[:k+1]."""
    out = []
    for n in ast.walk(root):
        if not isinstance(n, ast.Subscript):
            continue
        sl = n.slice
        if (isinstance(sl, ast.Slice) and sl.upper is not None
                and isinstance(sl.upper, ast.BinOp)
                and isinstance(sl.upper.op, (ast.Sub, ast.Add))
                and isinstance(sl.upper.right, ast.Constant)
                and sl.upper.right.value == 1):
            out.append((sl.upper, S.seg(sl.upper.left)))
    return out


def r_partition_sort(src):
    """lower + plist + higher  ->  sorted(lower) + plist + sorted(higher),
    alone and combined with the off-by-one slice fix ([:k-1] -> [:k])."""
    tree = ast.parse(src)
    S = _Src(src)
    fn = _topk(tree) or next((n for n in ast.walk(tree)
                              if isinstance(n, ast.FunctionDef)), None)
    if fn is None:
        return []
    guards = _append_guards(fn)
    off1 = _off1_slices(fn, S)
    out = []
    for node in ast.walk(fn):
        val = None
        if isinstance(node, (ast.Assign, ast.Return)):
            val = node.value
        if not isinstance(val, ast.BinOp):
            continue
        parts = _add_chain(val)
        if len(parts) < 2:
            continue
        ordered = [p for p in parts
                   if guards.get(p.id) in (ast.Lt, ast.Gt, ast.LtE, ast.GtE)]
        plans = []
        if ordered and len(ordered) < len(parts):
            plans.append(ordered)      # sort only the </> partitions
        plans.append(parts)            # sort every concatenated part
        for plan in plans:
            for extra in ("", ", reverse=True"):
                repls = [(p, "sorted(%s%s)" % (S.seg(p), extra))
                         for p in plan]
                out.append(S.replace(repls))
                for up, txt in off1[:2]:
                    out.append(S.replace(repls + [(up, txt)]))
    return out[:12]


def r_slice_off1(src):
    """x[:k-1]  /  x[:k+1]  ->  x[:k]  (off-by-one slice bound)."""
    tree = ast.parse(src)
    S = _Src(src)
    root = _topk(tree) or tree
    sites = _off1_slices(root, S)
    out = [S.replace([(up, txt)]) for up, txt in sites[:6]]
    if len(sites) > 1:
        out.append(S.replace(list(sites)))
    return out[:8]


_BASE_RULES = [r_return_wrap, r_minmax, r_append_split, r_subscript_cmp,
               r_return_var, r_while_cond, r_range_k, r_swap_stmts,
               r_return_dedent, r_insert_remove, r_swap_params, r_rename,
               r_partition_sort, r_slice_off1]


def _rule_order(pat):
    """Reorder rules using the observed failure pattern of the original."""
    if not pat:
        return list(_BASE_RULES)
    front = []
    try:
        fails = [i for i, r in enumerate(pat) if not r[0]]
        exps = [t["expected"] for t in TESTS]
        if fails and set(fails) <= {2, 4}:
            front += [r_return_wrap, r_swap_stmts, r_while_cond]
        for i in range(len(TESTS)):
            got = pat[i][1]
            if isinstance(got, list) and got and got == exps[i][::-1]:
                front += [r_return_wrap, r_minmax]
                break
        for i in range(len(TESTS)):
            got = pat[i][1]
            low = sorted(TESTS[i]["args"][0])[: TESTS[i]["args"][1]]
            if isinstance(got, list) and got and got == low:
                front += [r_minmax, r_return_wrap]
                break
        errs = " ".join(str(r[2]) for r in pat if r[2])
        if ("NoneType" in errs or "not supported" in errs
                or "TypeError" in errs or "unorderable" in errs):
            front += [r_append_split, r_subscript_cmp]
    except Exception:
        return list(_BASE_RULES)
    out = []
    for r in front + _BASE_RULES:
        if r not in out:
            out.append(r)
    return out


def _apply_rules(src, rules, cap):
    out, seen = [], set()
    for r in rules:
        try:
            cs = r(src)
        except Exception:
            continue
        for c in cs:
            if not isinstance(c, str) or c == src or c in seen:
                continue
            try:
                ast.parse(c)
            except Exception:
                continue
            seen.add(c)
            out.append(c)
            if len(out) >= cap:
                return out
    return out


# --------------------------------------------------------------------------
# Staged validation
# --------------------------------------------------------------------------

def _stage(cands, source, seen, deadline, cap):
    def gen():
        it = iter(cands)
        n = 0
        while True:
            if n >= cap or time.monotonic() > deadline:
                return
            try:
                c = next(it)
            except StopIteration:
                return
            except Exception:
                return
            n += 1
            if not isinstance(c, str) or c in seen:
                continue
            seen.add(c)
            try:
                if rps(source, c) > 0.355:
                    continue
            except Exception:
                continue
            if _quick_ok(c):
                yield c

    try:
        return first_passing(gen(), ENTRY, TESTS, source,
                             max_rps=0.35, max_checks=200)
    except Exception:
        return None


def repair(source):
    t0 = time.monotonic()
    deadline = t0 + 8.0
    try:
        if not isinstance(source, str) or not source.strip():
            return None
        try:
            ast.parse(source)
        except Exception:
            return None

        seen = set()
        pat = _run_tests(source, 200000)
        rules = _rule_order(pat)
        singles = _apply_rules(source, rules, cap=96)

        # Stage A: original + problem-specific single rewrites
        res = _stage([source] + singles, source, seen, deadline, 300)
        if res:
            return res

        # Stage B: pairs of problem-specific rewrites
        if time.monotonic() < deadline:
            pairs = []
            for s in singles[:30]:
                if time.monotonic() > deadline or len(pairs) >= 350:
                    break
                pairs.extend(_apply_rules(s, rules, cap=25))
            res = _stage(pairs, source, seen, deadline, 400)
            if res:
                return res

        # Stage C: generic single-edit search
        if time.monotonic() < deadline:
            res = _stage(candidates_generic(source, max_edits=1, budget=2000),
                         source, seen, deadline, 2000)
            if res:
                return res

        # Stage D: specific rewrite + one generic edit on top
        for s in singles[:6]:
            if time.monotonic() > deadline:
                break
            res = _stage(candidates_generic(s, max_edits=1, budget=250),
                         source, seen, deadline, 250)
            if res:
                return res

        # Stage E: generic two-edit search
        if time.monotonic() < deadline:
            res = _stage(candidates_generic(source, max_edits=2, budget=2500),
                         source, seen, deadline, 1500)
            if res:
                return res

        # Stage F: fallback without the local pre-screen, in case the
        # trace-based runner misbehaves in this environment.
        if time.monotonic() - t0 < 6.5:
            try:
                cand = first_passing(
                    chain(iter([source]), iter(singles),
                          candidates_generic(source, max_edits=1, budget=800)),
                    ENTRY, TESTS, source, max_rps=0.35, max_checks=300)
                if cand:
                    return cand
            except Exception:
                pass
        return None
    except Exception:
        return None
```
