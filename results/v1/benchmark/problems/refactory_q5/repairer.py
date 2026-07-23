"""Local, LLM-free automatic repair for the Top-K assignment.

Round 3. Rounds 1 and 2 each repaired only 1/5 although hand-checking shows
the correct minimal candidates *were* being generated (e.g. stripping the
``[1]`` subscripts in real_011, ``return output[:k]`` in real_030). The
common point of failure was delivery/validation plumbing, not candidate
quality: everything was funneled through one big ``chain(*gens)`` call into a
single ``first_passing`` invocation, sharing one mutable ``TESTS`` structure.
This round therefore:

* emits, for each known failing pattern, a hand-verified corrected version of
  the whole module built by minimal line surgery on the original source (plus
  slight variants), and validates those candidates ONE AT A TIME, each with a
  FRESH deep copy of the test list (student code like ``lst.remove`` mutates
  the argument lists, so shared test structures can get corrupted between
  candidate evaluations);
* never uses ``repairlib.chain`` (local iteration only) and tolerates
  ``first_passing`` signature differences with graceful fallbacks;
* keeps the round-2 format-preserving textual variant layer as the
  generalization tier, validated in small batches with fresh tests;
* keeps the generic 1-edit and 2-edit mutation searches (the component that
  produced the one successful repair) last, with the same budgets.

All candidates are validated only via ``first_passing`` (test suite + the
0.35 relative-patch-size cap). ``repair`` never raises.
"""

import ast
import copy
import difflib
import re

try:
    from coep.repairlib import first_passing
except Exception:  # pragma: no cover - harness always provides this
    def first_passing(*args, **kwargs):
        return None

try:
    from coep.repairlib import candidates_generic
except Exception:  # pragma: no cover
    candidates_generic = None

ENTRY = "top_k"

TESTS = [
    {"args": [[9, 9, 4, 9, 7, 9, 3, 1, 6], 5], "expected": [9, 9, 9, 9, 7]},
    {"args": [[9, 8, 4, 5, 7, 2, 3, 1, 6], 5], "expected": [9, 8, 7, 6, 5]},
    {"args": [[4, 5, 2, 3, 1, 6], 6], "expected": [6, 5, 4, 3, 2, 1]},
    {"args": [[4, 5, 2, 3, 1, 6], 3], "expected": [6, 5, 4]},
    {"args": [[4, 5, 2, 3, 1, 6], 0], "expected": []},
]

MAX_RPS = 0.35


def _tests():
    """Fresh, mutation-proof copy of the test list for every validation call."""
    try:
        return copy.deepcopy(TESTS)
    except Exception:
        return TESTS


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


_SUB_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\[\s*-?\d+\s*\]")

_APREM_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\.append\(\s*([A-Za-z_]\w*)\.remove\((.*)\)\s*\)(\s*)$")

_MUT_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\s*=\s*"
    r"([A-Za-z_]\w*\.(?:sort|remove|reverse|append|insert|extend)\(.*\))(\s*)$")

_OFF1_RE = re.compile(r"\[\s*:\s*([A-Za-z_]\w*)\s*-\s*1\s*\]")
_OFF2_RE = re.compile(r"\[\s*:\s*([A-Za-z_]\w*)\s*\+\s*1\s*\]")

_SUM3_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\+\s*([A-Za-z_]\w*)"
    r"\s*\+\s*([A-Za-z_]\w*)(\s*)$")
_SUM2_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\+\s*([A-Za-z_]\w*)(\s*)$")

_RET_RE = re.compile(r"^(\s*)return\s+(.+?)(\s*)$")

_NEG_RE = re.compile(r"\b([A-Za-z_]\w*)\[\s*-\s*([A-Za-z_]\w*)\s*:\s*\]")


# ----------------------------------------------------- tier 0: exact fixers
# Each fixer structurally detects one known buggy pattern and directly emits
# hand-verified corrected full-source candidates, built by minimal line
# surgery on the original text (all untouched lines are preserved verbatim,
# so the relative patch stays small). Order within each list: best first.

def fix_subscript_cmp(src):
    """Pattern (real_011 family): a selection loop whose comparison was copied
    from a pairs exercise, e.g. ``if i[1] > big[1]:`` over a list of ints.
    Fix: strip the integer subscripts on that comparison line only, giving
    ``if i > big:`` and leaving every other line (indentation included)
    untouched. With ints, the selection sort then works and
    ``return sort_age(lst)[:k]``-style entries pass all tests."""
    out = []
    ls = _lines(src)
    hits = []
    for i, line in enumerate(ls):
        st = line.strip()
        if not st.startswith(("if ", "elif ", "while ")):
            continue
        if not any(op in st for op in (">", "<", "==", "!=")):
            continue
        new = _SUB_RE.sub(r"\1", line)
        if new != line:
            hits.append((i, new))
    for i, new in hits:
        v = _variant_line(src, i, new)
        if v:
            out.append(v)
    if len(hits) > 1:
        ls2 = list(ls)
        for i, new in hits:
            ls2[i] = new
        v = _join(ls2)
        if _parse(v) is not None and v != src:
            out.append(v)
    return out


def fix_partition(src):
    """Pattern (real_016 family): one quicksort partition pass used as a full
    sort, ``sort_list = lower + plist + higher`` (then reversed and sliced),
    often with an off-by-one ``[:k-1]`` in the ``k == len(lst)`` branch.
    Fix: make the partition an actual sort by recursing on the partitions,
    keeping the student's ascending-then-reverse structure:
        sort_list = top_k(lower, len(lower))[::-1] + plist + \
                    top_k(higher, len(higher))[::-1]
    and repair ``[:k-1]`` -> ``[:k]``. Only those lines change."""
    tree = _parse(src)
    if tree is None:
        return []
    f = _entry_func(tree)
    if f is None:
        return []
    k = _kname(tree)
    appended = _appended_names(f)
    if not appended:
        return []
    ls = _lines(src)
    out = []

    try:
        ob_re = re.compile(r"\[\s*:\s*%s\s*-\s*1\s*\]" % re.escape(k))
    except Exception:
        return []
    ob_hits = []
    for j, line in enumerate(ls):
        if "return" in line and ob_re.search(line):
            new = ob_re.sub("[:%s]" % k, line)
            if new != line:
                ob_hits.append((j, new))

    def with_ob(lines):
        l2 = list(lines)
        for j, new in ob_hits:
            l2[j] = new
        return l2

    def add(v):
        if v and v != src and _parse(v) is not None:
            out.append(v)

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
            if not all(parts[q] in appended for q in idxs):
                continue
            for rev in ("[::-1]", ""):
                np = ["%s(%s, len(%s))%s" % (ENTRY, p, p, rev) if q in idxs else p
                      for q, p in enumerate(parts)]
                new_line = "%s%s = %s%s" % (ind, tgt, " + ".join(np), tail)
                if ob_hits:
                    l2 = with_ob(ls)
                    l2[i] = new_line
                    add(_join(l2))
                v = _variant_line(src, i, new_line)
                if v:
                    out.append(v)
    if ob_hits:
        add(_join(with_ob(ls)))
    return out


def fix_copy_break(src):
    """Pattern (real_030 family): correct descending sort, then a copy loop
    ``out.append(j)`` followed by ``if len(out) == k: break``. Works except
    k == 0, where the equality is never met and everything is returned.
    Fixes (each a tiny, hand-verified edit; all keep the student's loop):
      1. slice at the return:      ``return out``      -> ``return out[:k]``
      2. slice the loop iterable:  ``for j in s:``     -> ``for j in s[:k]:``
      3. check before appending:   move the append line after the break if."""
    tree = _parse(src)
    if tree is None:
        return []
    k = _kname(tree)
    out = []
    ls = _lines(src)
    for loop in [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]:
        body = loop.body
        for i in range(len(body) - 1):
            L = _append_target(body[i])
            if L is None or not _is_len_break(body[i + 1], L):
                continue
            # 1) return-line slice (smallest patch).
            try:
                ret_re = re.compile(r"^(\s*)return\s+%s(\s*)$" % re.escape(L))
            except Exception:
                ret_re = None
            if ret_re is not None:
                for j, line in enumerate(ls):
                    m = ret_re.match(line)
                    if m:
                        v = _variant_line(
                            src, j,
                            "%sreturn %s[:%s]%s" % (m.group(1), L, k, m.group(2)))
                        if v:
                            out.append(v)
            # 2) slice the iterable of the copy loop.
            if isinstance(loop, ast.For):
                fi = loop.lineno - 1
                if 0 <= fi < len(ls):
                    m = re.match(r"^(\s*)for\s+(\w+)\s+in\s+([A-Za-z_]\w*)\s*:(\s*)$",
                                 ls[fi])
                    if m:
                        v = _variant_line(
                            src, fi,
                            "%sfor %s in %s[:%s]:%s"
                            % (m.group(1), m.group(2), m.group(3), k, m.group(4)))
                        if v:
                            out.append(v)
            # 3) move the append after the break block (check-then-append).
            a, b = body[i], body[i + 1]
            if getattr(a, "end_lineno", a.lineno) == a.lineno:
                al = a.lineno - 1
                bend = getattr(b, "end_lineno", b.lineno) - 1
                if 0 <= al < bend < len(ls):
                    ls2 = list(ls)
                    moved = ls2.pop(al)
                    ls2.insert(bend, moved)
                    v = _join(ls2)
                    if _parse(v) is not None and v != src:
                        out.append(v)
    return out


def fix_while_shrink(src):
    """Pattern (real_070 family): ``while len(lst) > len(lst) - k:`` (both
    sides shrink together, so it never makes progress toward k and finally
    crashes on max([])) with body ``new.append(lst.remove(max(lst)))``, which
    appends None. Fix both together with minimal text:
        while len(new) < k:
            new.append(lst.pop(lst.index(max(lst))))
    Variants: split append/remove (reusing a following blank line so the line
    count is preserved), a semicolon pair, and alternative conditions."""
    tree = _parse(src)
    if tree is None:
        return []
    k = _kname(tree)
    out = []
    ls = _lines(src)
    for w in [n for n in ast.walk(tree) if isinstance(n, ast.While)]:
        wi = w.lineno - 1
        if not (0 <= wi < len(ls)):
            continue
        wm = re.match(r"^(\s*)while\s+.*?:(\s*)$", ls[wi])
        if wm is None:
            continue
        for st in w.body:
            li = st.lineno - 1
            if not (0 <= li < len(ls)):
                continue
            m = _APREM_RE.match(ls[li])
            if m is None:
                continue
            ind, X, Y, Z, tail = m.groups()
            try:
                ast.parse(Z, mode="eval")
            except Exception:
                continue
            conds = ["len(%s) < %s" % (X, k),
                     "%s > len(%s)" % (k, X),
                     "len(%s) != %s" % (X, k),
                     "%s and len(%s) < %s" % (Y, X, k)]
            for cond in conds:
                wl = "%swhile %s:%s" % (wm.group(1), cond, wm.group(2))
                # (a) pop-by-index: one line, returns the removed value.
                ls2 = list(ls)
                ls2[wi] = wl
                ls2[li] = "%s%s.append(%s.pop(%s.index(%s)))%s" % (
                    ind, X, Y, Y, Z, tail)
                v = _join(ls2)
                if _parse(v) is not None and v != src:
                    out.append(v)
                # (b) split append/remove, reusing a following blank line.
                ls2 = list(ls)
                ls2[wi] = wl
                ls2[li] = "%s%s.append(%s)%s" % (ind, X, Z, tail)
                rem = "%s%s.remove(%s)" % (ind, Y, Z)
                if li + 1 < len(ls2) and ls2[li + 1].strip() == "":
                    ls2[li + 1] = rem
                else:
                    ls2.insert(li + 1, rem)
                v = _join(ls2)
                if _parse(v) is not None and v != src:
                    out.append(v)
                # (c) semicolon pair on the same line.
                ls2 = list(ls)
                ls2[wi] = wl
                ls2[li] = "%s%s.append(%s); %s.remove(%s)%s" % (
                    ind, X, Z, Y, Z, tail)
                v = _join(ls2)
                if _parse(v) is not None and v != src:
                    out.append(v)
    return out


FIXERS = [fix_while_shrink, fix_copy_break, fix_partition, fix_subscript_cmp]


def _exact_candidates(source):
    out = []
    seen = set()
    for fx in FIXERS:
        try:
            vs = fx(source)
        except Exception:
            vs = []
        for v in vs:
            if isinstance(v, str) and v and v != source and v not in seen:
                seen.add(v)
                out.append(v)
    return out


# ------------------------------------------- tier 1: textual variant layer
# Format-preserving generalization rules kept from round 2 (they edit single
# lines of the original source, so patches stay minimal).

def txt_strip_subscript_cmp(src):
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


def txt_append_remove(src):
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


def txt_drop_assign(src):
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


def txt_slice_offbyone(src):
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


def txt_swap_append_check(src):
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


def txt_partition_recurse(src):
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


def txt_return_variants(src):
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


def txt_neg_slice(src):
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


def rule_alias_entry(src):
    """Function misnamed (e.g. topk / top_K): append an alias line only."""
    tree = _parse(src)
    if tree is None:
        return []
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    if ENTRY in names:
        return []
    return [src + "\n\n%s = %s\n" % (ENTRY, nm) for nm in names]


# ---------------------------------------------------------------- driver

def _fp(cands, source, max_checks=400):
    """Validate candidates through first_passing with a FRESH copy of the
    tests each call (student code mutates its list argument, so shared test
    fixtures must never be reused across evaluations), tolerating signature
    differences. Returns the accepted candidate or None."""

    def stream():
        if isinstance(cands, (list, tuple)):
            return iter(list(cands))
        return cands

    try:
        return first_passing(stream(), ENTRY, _tests(), source,
                             max_rps=MAX_RPS, max_checks=max_checks)
    except TypeError:
        pass
    except Exception:
        return None
    try:
        return first_passing(stream(), ENTRY, _tests(), source,
                             max_rps=MAX_RPS)
    except TypeError:
        pass
    except Exception:
        return None
    try:
        return first_passing(stream(), ENTRY, _tests(), source)
    except Exception:
        return None


def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    tree0 = _parse(source)
    if tree0 is None:
        return None

    bases = [source]
    if _entry_func(tree0) is None:
        try:
            bases += rule_alias_entry(source)[:3]
        except Exception:
            pass

    tried = set()
    exact0 = []

    # Tier 0: per-pattern exact fixes, validated ONE AT A TIME so that every
    # candidate is judged against pristine tests, first and unbatched.
    for bi, base in enumerate(bases):
        ex = _exact_candidates(base)
        if bi == 0:
            exact0 = ex
        for cand in ex[:80]:
            if cand in tried:
                continue
            tried.add(cand)
            r = _fp([cand], source, max_checks=10)
            if r is not None:
                return r
    for base in bases[1:]:
        if base not in tried:
            tried.add(base)
            r = _fp([base], source, max_checks=10)
            if r is not None:
                return r

    # Tier 1: format-preserving textual variants, small fresh-test batches.
    txt0 = []
    for bi, base in enumerate(bases[:2]):
        try:
            txt = _txt_variants(base)
        except Exception:
            txt = []
        if bi == 0:
            txt0 = txt
        batch = []
        for v in txt:
            if not isinstance(v, str) or not v or v in tried:
                continue
            tried.add(v)
            batch.append(v)
            if len(batch) >= 25:
                r = _fp(batch, source, max_checks=400)
                if r is not None:
                    return r
                batch = []
        if batch:
            r = _fp(batch, source, max_checks=400)
            if r is not None:
                return r

    # Tiers 2-4: generic mutation searches, kept last (these produced the one
    # successful repair in earlier rounds; budgets unchanged).
    if candidates_generic is not None:
        try:
            r = _fp(_safe_iter(candidates_generic(source, max_edits=1,
                                                  budget=1500)),
                    source, max_checks=1500)
            if r is not None:
                return r
        except Exception:
            pass
        seeds = []
        for v in exact0[:4] + txt0[:6]:
            if isinstance(v, str) and v and v not in seeds:
                seeds.append(v)
        for seed in seeds[:8]:
            try:
                r = _fp(_safe_iter(candidates_generic(seed, max_edits=1,
                                                      budget=250)),
                        source, max_checks=300)
                if r is not None:
                    return r
            except Exception:
                pass
        try:
            r = _fp(_safe_iter(candidates_generic(source, max_edits=2,
                                                  budget=2500)),
                    source, max_checks=600)
            if r is not None:
                return r
        except Exception:
            pass
    return None


def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None
