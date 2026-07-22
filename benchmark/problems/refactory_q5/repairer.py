"""Local, LLM-free automatic repair for the Top-K assignment.

Round 2. The previous version generated semantically correct candidates but
emitted them through ast.unparse, which reformats the WHOLE file (indentation,
blank lines, spacing). That inflated the relative patch size past the 0.35
cap, so first_passing rejected otherwise-correct repairs. This version adds
line-preserving *textual* candidate generators that edit only the offending
line(s) of the original source, keeping patches genuinely minimal. The old
AST-based rules and the generic 1-edit / 2-edit mutation searches are kept as
fallbacks. Every candidate is still validated by first_passing (test suite +
rps cap), so speculative candidates are harmless.
"""

import ast
import copy
import difflib
import re

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


# ------------------------------------------- textual (format-preserving) layer
# These rules edit individual lines of the ORIGINAL source, never reformatting
# untouched lines, so the resulting patch size stays minimal.

def _lines(src):
    return src.split("\n")


def _join(ls):
    return "\n".join(ls)


def _variant_line(src, i, new_line):
    ls = _lines(src)
    if not (0 <= i < len(ls)):
        return None
    if ls[i] == new_line:
        return None
    ls2 = list(ls)
    ls2[i] = new_line
    v = _join(ls2)
    if _parse(v) is None:
        return None
    return v


def _diff_score(a, b):
    try:
        return 1.0 - difflib.SequenceMatcher(None, a, b).ratio()
    except Exception:
        return 1.0


_SUB_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\[\s*-?\d+\s*\]")


def txt_strip_subscript_cmp(src):
    """`if i[1] > big[1]:` (comparison copied from a pairs exercise) -> `if i > big:`.
    Edits only the comparison line, preserving its original indentation."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        st = line.strip()
        if not st.startswith(("if ", "elif ", "while ")):
            continue
        if not any(op in st for op in (">", "<", "==", "!=")):
            continue
        new = _SUB_RE.sub(r"\1", line)
        if new != line:
            v = _variant_line(src, i, new)
            if v:
                out.append(v)
    return out


_APREM_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\.append\(\s*([A-Za-z_]\w*)\.remove\((.*)\)\s*\)(\s*)$")


def txt_append_remove(src):
    """`new.append(lst.remove(X))` appends None. Same-line fixes first:
    pop-by-index (no extra line), then a semicolon pair, then a 2-line split."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        m = _APREM_RE.match(line)
        if not m:
            continue
        ind, X, Y, Z, tail = m.groups()
        try:
            ast.parse(Z, mode="eval")
        except Exception:
            continue
        same_line = [
            "%s%s.append(%s.pop(%s.index(%s)))%s" % (ind, X, Y, Y, Z, tail),
            "%s%s.append(%s); %s.remove(%s)%s" % (ind, X, Z, Y, Z, tail),
        ]
        for c in same_line:
            v = _variant_line(src, i, c)
            if v:
                out.append(v)
        ls2 = list(ls)
        ls2[i] = "%s%s.append(%s)" % (ind, X, Z)
        ls2.insert(i + 1, "%s%s.remove(%s)" % (ind, Y, Z))
        v = _join(ls2)
        if _parse(v) is not None:
            out.append(v)
    return out


_MUT_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\s*=\s*"
    r"([A-Za-z_]\w*\.(?:sort|remove|reverse|append|insert|extend)\(.*\))(\s*)$")


def txt_drop_assign(src):
    """`x = lst.sort()` / `x = lst.remove(...)` (None) -> bare mutation call."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        m = _MUT_RE.match(line)
        if not m:
            continue
        v = _variant_line(src, i, m.group(1) + m.group(3) + m.group(4))
        if v:
            out.append(v)
    return out


def txt_insert_remove(src):
    """Loop appends max(lst)/min(lst) but never shrinks lst -> insert a
    matching `lst.remove(max(lst))` line right after the append."""
    tree = _parse(src)
    if tree is None:
        return []
    out = []
    ls = _lines(src)
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr in ("remove", "pop") for n in ast.walk(loop)):
            continue
        for st in loop.body:
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
            if getattr(st, "end_lineno", st.lineno) != st.lineno:
                continue
            i = st.lineno - 1
            if not (0 <= i < len(ls)):
                continue
            ind = re.match(r"^(\s*)", ls[i]).group(1)
            ls2 = list(ls)
            ls2.insert(i + 1, "%s%s.remove(%s(%s))"
                       % (ind, a.args[0].id, a.func.id, a.args[0].id))
            v = _join(ls2)
            if _parse(v) is not None:
                out.append(v)
    return out


_OFF1_RE = re.compile(r"\[\s*:\s*([A-Za-z_]\w*)\s*-\s*1\s*\]")
_OFF2_RE = re.compile(r"\[\s*:\s*([A-Za-z_]\w*)\s*\+\s*1\s*\]")


def txt_slice_offbyone(src):
    """Boundary fix per line: X[:k-1] -> X[:k], X[:k+1] -> X[:k]."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        for rx in (_OFF1_RE, _OFF2_RE):
            new = rx.sub(lambda m: "[:%s]" % m.group(1), line)
            if new != line:
                v = _variant_line(src, i, new)
                if v:
                    out.append(v)
    return out


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


def txt_swap_append_check(src):
    """`out.append(x)` followed by `if len(out) == k: break` returns the whole
    list when k == 0. Move the append line to AFTER the break block (check
    before appending), preserving every line's text."""
    tree = _parse(src)
    if tree is None:
        return []
    out = []
    ls = _lines(src)
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        body = loop.body
        for i in range(len(body) - 1):
            L = _append_target(body[i])
            if L is None or not _is_len_break(body[i + 1], L):
                continue
            a, b = body[i], body[i + 1]
            if getattr(a, "end_lineno", a.lineno) != a.lineno:
                continue
            al = a.lineno - 1
            bend = getattr(b, "end_lineno", b.lineno) - 1
            if not (0 <= al < bend < len(ls)):
                continue
            ls2 = list(ls)
            moved = ls2.pop(al)
            ls2.insert(bend, moved)
            v = _join(ls2)
            if _parse(v) is not None:
                out.append(v)
    return out


def txt_while_progress(src):
    """Rewrite a broken while condition (single line) as `len(out) < k` for
    each list the loop appends to; only for loops that also shrink a list."""
    tree = _parse(src)
    if tree is None:
        return []
    k = _kname(tree)
    out = []
    ls = _lines(src)
    for w in [n for n in ast.walk(tree) if isinstance(n, ast.While)]:
        shrinks = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr in ("remove", "pop")
                      for n in ast.walk(w)) or \
            any(isinstance(n, ast.Delete) for n in ast.walk(w))
        if not shrinks:
            continue
        i = w.lineno - 1
        if not (0 <= i < len(ls)):
            continue
        m = re.match(r"^(\s*)while\s+.*:(\s*)$", ls[i])
        if m is None:
            continue
        for L in sorted(_appended_names(w)):
            for cond in ("len(%s) < %s" % (L, k),
                         "%s > len(%s)" % (k, L),
                         "len(%s) != %s" % (L, k)):
                v = _variant_line(src, i, "%swhile %s:%s"
                                  % (m.group(1), cond, m.group(2)))
                if v:
                    out.append(v)
    return out


_SUM3_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\+\s*([A-Za-z_]\w*)"
    r"\s*\+\s*([A-Za-z_]\w*)(\s*)$")
_SUM2_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\+\s*([A-Za-z_]\w*)(\s*)$")


def txt_partition_recurse(src):
    """One-pass pivot partition is not a sort: recurse on the partitions.
    `sort_list = lower + plist + higher` becomes
    `sort_list = top_k(lower, len(lower))[::-1] + plist + top_k(higher, len(higher))[::-1]`
    (only that one line changes)."""
    tree = _parse(src)
    if tree is None:
        return []
    f = _entry_func(tree)
    if f is None:
        return []
    appended = _appended_names(f)
    out = []
    ls = _lines(src)

    def wrap(p):
        return "%s(%s, len(%s))[::-1]" % (ENTRY, p, p)

    for i, line in enumerate(ls):
        m3 = _SUM3_RE.match(line)
        m2 = None if m3 else _SUM2_RE.match(line)
        if m3:
            ind, tgt, tail = m3.group(1), m3.group(2), m3.group(6)
            parts = [m3.group(3), m3.group(4), m3.group(5)]
            idxsets = [(0, 2), (0, 1, 2)]
        elif m2:
            ind, tgt, tail = m2.group(1), m2.group(2), m2.group(5)
            parts = [m2.group(3), m2.group(4)]
            idxsets = [(0, 1), (0,), (1,)]
        else:
            continue
        for idxs in idxsets:
            if not all(parts[j] in appended for j in idxs):
                continue
            np = [wrap(p) if j in idxs else p for j, p in enumerate(parts)]
            v = _variant_line(src, i, "%s%s = %s%s"
                              % (ind, tgt, " + ".join(np), tail))
            if v:
                out.append(v)
    return out


_RET_RE = re.compile(r"^(\s*)return\s+(.+?)(\s*)$")


def txt_return_variants(src):
    """Forgot to slice / built ascending: `return X` -> `X[:k]`, `X[::-1][:k]`,
    `X[::-1]`; `return f(...)` -> sliced forms; `return X[a:b]` -> reversed base."""
    tree = _parse(src)
    if tree is None:
        return []
    k = _kname(tree)
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        m = _RET_RE.match(line)
        if not m:
            continue
        ind, expr, tail = m.groups()
        if "#" in expr:
            continue
        try:
            e = ast.parse(expr, mode="eval").body
        except Exception:
            continue
        news = []
        if isinstance(e, ast.Name):
            if e.id == k:
                continue
            news = ["%s[:%s]" % (expr, k),
                    "%s[::-1][:%s]" % (expr, k),
                    "%s[::-1]" % expr]
        elif isinstance(e, ast.Call):
            news = ["%s[:%s]" % (expr, k), "%s[::-1][:%s]" % (expr, k)]
        elif isinstance(e, ast.Subscript):
            m2 = re.match(r"^([A-Za-z_]\w*)\[", expr)
            if m2:
                news = [m2.group(1) + "[::-1]" + expr[len(m2.group(1)):]]
        for ne in news:
            v = _variant_line(src, i, ind + "return " + ne + tail)
            if v:
                out.append(v)
    return out


def txt_minmax(src):
    """Swap min <-> max (bottom-k misconception), whole file and per line."""
    out = []
    for a, b in (("max(", "min("), ("min(", "max(")):
        if a in src:
            v = src.replace(a, b)
            if _parse(v) is not None and v != src:
                out.append(v)
    ls = _lines(src)
    for i, line in enumerate(ls):
        for a, b in (("max(", "min("), ("min(", "max(")):
            if a in line:
                v = _variant_line(src, i, line.replace(a, b))
                if v:
                    out.append(v)
    return out


def txt_sort_reverse(src):
    """Add reverse=True to sort()/sorted() calls, one line at a time."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        news = []
        if ".sort()" in line:
            news.append(line.replace(".sort()", ".sort(reverse=True)"))
        for mm in re.finditer(r"sorted\(([^()]+)\)", line):
            news.append(line[:mm.start()]
                        + "sorted(%s, reverse=True)" % mm.group(1)
                        + line[mm.end():])
        for n2 in news:
            v = _variant_line(src, i, n2)
            if v:
                out.append(v)
    return out


_NEG_RE = re.compile(r"\b([A-Za-z_]\w*)\[\s*-\s*([A-Za-z_]\w*)\s*:\s*\]")


def txt_neg_slice(src):
    """Ascending list sliced X[-k:] (wrong order, breaks k=0) ->
    X[::-1][:k] (also offer X[-k:][::-1])."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        m = _NEG_RE.search(line)
        if not m:
            continue
        X, K = m.groups()
        for rep in ("%s[::-1][:%s]" % (X, K), "%s[-%s:][::-1]" % (X, K)):
            v = _variant_line(src, i, line[:m.start()] + rep + line[m.end():])
            if v:
                out.append(v)
    return out


def txt_range_k(src):
    """Selection loop iterating over the wrong thing -> for ... in range(k)."""
    tree = _parse(src)
    if tree is None:
        return []
    k = _kname(tree)
    out = []
    ls = _lines(src)
    for fr in [n for n in ast.walk(tree) if isinstance(n, ast.For)]:
        if not _appended_names(fr):
            continue
        i = fr.lineno - 1
        if not (0 <= i < len(ls)):
            continue
        m = re.match(r"^(\s*)for\s+(.+?)\s+in\s+(.+?):(\s*)$", ls[i])
        if not m:
            continue
        if m.group(3).strip() == "range(%s)" % k:
            continue
        v = _variant_line(src, i, "%sfor %s in range(%s):%s"
                          % (m.group(1), m.group(2), k, m.group(4)))
        if v:
            out.append(v)
    return out


def txt_for_slice_k(src):
    """Copy loop takes too many items: `for j in sort:` -> `for j in sort[:k]:`."""
    tree = _parse(src)
    if tree is None:
        return []
    k = _kname(tree)
    out = []
    ls = _lines(src)
    for fr in [n for n in ast.walk(tree) if isinstance(n, ast.For)]:
        i = fr.lineno - 1
        if not (0 <= i < len(ls)):
            continue
        m = re.match(r"^(\s*)for\s+(\w+)\s+in\s+([A-Za-z_]\w*):(\s*)$", ls[i])
        if not m:
            continue
        v = _variant_line(src, i, "%sfor %s in %s[:%s]:%s"
                          % (m.group(1), m.group(2), m.group(3), k, m.group(4)))
        if v:
            out.append(v)
    return out


def txt_cmp_flip(src):
    """Flip a comparison on a single if/elif/while line."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        st = line.strip()
        if not st.startswith(("if ", "elif ", "while ")):
            continue
        cands = []
        if ">=" in line:
            cands.append(line.replace(">=", "<=", 1))
        elif "<=" in line:
            cands.append(line.replace("<=", ">=", 1))
        elif ">" in line and "->" not in line and "<" not in line:
            cands.append(line.replace(">", "<", 1))
        elif "<" in line and ">" not in line:
            cands.append(line.replace("<", ">", 1))
        for c in cands:
            v = _variant_line(src, i, c)
            if v:
                out.append(v)
    return out


def txt_eq_cmp(src):
    """Loosen equality guards: `== k` -> `>=` / `<=` on if/while lines."""
    out = []
    ls = _lines(src)
    for i, line in enumerate(ls):
        st = line.strip()
        if not st.startswith(("if ", "elif ", "while ")):
            continue
        if "==" in line:
            for rep in (">=", "<="):
                v = _variant_line(src, i, line.replace("==", rep, 1))
                if v:
                    out.append(v)
    return out


def txt_k0_guard(src):
    """Insert an early `if k <= 0: return []` at the top of the entry body."""
    tree = _parse(src)
    if tree is None:
        return []
    f = _entry_func(tree)
    if f is None or not f.body:
        return []
    k = _kname(tree)
    first = f.body[0]
    if first.lineno == f.lineno:
        return []
    i = first.lineno - 1
    ls = _lines(src)
    if not (0 <= i < len(ls)):
        return []
    ind = re.match(r"^(\s*)", ls[i]).group(1)
    ls2 = list(ls)
    ls2.insert(i, "%sif %s <= 0:" % (ind, k))
    ls2.insert(i + 1, "%s    return []" % ind)
    v = _join(ls2)
    return [v] if _parse(v) is not None else []


# Textual rules whose fixes must compose (e.g. append-remove split + while
# condition for real_070-style bugs; slice off-by-one + partition recursion
# for real_016-style bugs). Order matters: prerequisites come first.
TXT_COMBO = [
    txt_strip_subscript_cmp,
    txt_append_remove,
    txt_drop_assign,
    txt_insert_remove,
    txt_slice_offbyone,
    txt_swap_append_check,
    txt_while_progress,
    txt_partition_recurse,
]

# Textual rules applied only to the original source.
TXT_SINGLE = [
    txt_return_variants,
    txt_minmax,
    txt_sort_reverse,
    txt_neg_slice,
    txt_range_k,
    txt_for_slice_k,
    txt_cmp_flip,
    txt_eq_cmp,
    txt_k0_guard,
]


def _txt_variants(source):
    seen = {source, _norm(source)}
    pool = [source]

    def add(lst, v):
        if not v or not isinstance(v, str):
            return
        if v in seen:
            return
        key = _norm(v)
        if key in seen:
            return
        seen.add(v)
        seen.add(key)
        lst.append(v)

    for rule in TXT_COMBO:
        additions = []
        for s in list(pool):
            if len(additions) >= 24:
                break
            try:
                vs = rule(s)
            except Exception:
                vs = []
            for v in vs:
                add(additions, v)
                if len(additions) >= 24:
                    break
        pool.extend(additions)
        if len(pool) > 90:
            pool = pool[:90]

    singles = []
    for rule in TXT_SINGLE:
        try:
            vs = rule(source)
        except Exception:
            vs = []
        for v in vs:
            add(singles, v)

    variants = pool[1:] + singles
    try:
        variants.sort(key=lambda v: _diff_score(source, v))
    except Exception:
        pass
    return variants[:110]


# ---------------------------------------------------------------- AST rules
# Kept from round 1 as a lower-priority tier (their unparse output loses the
# original formatting, but they still catch cases the textual layer misses).

def rule_strip_subscript_compare(src):
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


def rule_swap_append_check(src):
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


# ---------------------------------------------------------------- driver

def _repair(source):
    if not isinstance(source, str):
        return None
    tree0 = _parse(source)
    if tree0 is None:
        return None

    # Tier 1: format-preserving textual candidates (minimal patch size).
    try:
        txt = _txt_variants(source)
    except Exception:
        txt = []

    # If the entry point is misnamed, alias it and rerun the textual layer on
    # the aliased source so name + logic bugs can be fixed together.
    if _entry_func(tree0) is None:
        extra = []
        try:
            for al in rule_alias_entry(source)[:3]:
                extra.append(al)
                try:
                    extra.extend(_txt_variants(al)[:25])
                except Exception:
                    pass
        except Exception:
            pass
        txt = extra + txt

    # Tier 2: round-1 AST rules (unparse-based) as a fallback.
    try:
        ast_variants = _rule_variants(source)
    except Exception:
        ast_variants = []

    seen = set()
    ordered = []
    for v in txt + ast_variants:
        if isinstance(v, str) and v and v != source and v not in seen:
            seen.add(v)
            ordered.append(v)

    # Phase 1: original, textual+rule variants, 1-edit generic search, then
    # 1-edit generic search chained on the most promising variants.
    gens = [iter([source])]
    if ordered:
        gens.append(iter(ordered))
    try:
        gens.append(_safe_iter(candidates_generic(source, max_edits=1, budget=1500)))
    except Exception:
        pass
    seeds = []
    for v in txt[:6] + ast_variants[:8]:
        if isinstance(v, str) and v and v not in seeds:
            seeds.append(v)
    for v in seeds:
        try:
            gens.append(_safe_iter(candidates_generic(v, max_edits=1, budget=250)))
        except Exception:
            pass
    cand = None
    try:
        cand = first_passing(chain(*gens), ENTRY, TESTS, source,
                             max_rps=MAX_RPS, max_checks=1500)
    except Exception:
        cand = None
    if cand is not None:
        return cand

    # Phase 2: 2-edit generic search on the original as a last resort.
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
