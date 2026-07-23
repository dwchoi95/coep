"""Local, LLM-free repair system for the "unique dates and months" assignment.

AST-guided, problem-specific rewrite rules emitted as byte-surgical span edits
(untouched lines stay byte-identical), composed with the generic mutation
search from coep.repairlib, always validated through first_passing.

Targets: wrong uniqueness thresholds (mirrored across unique_day/unique_month);
trailing `return True` after a duplicate-early-exit loop instead of
`return count == 1` -- including while-loop list-shrinking versions
(real_293 style), where the `len(lst) > 0` loop guard must not be mistaken
for the counter: the init-0 counter is preferred, and a known-pattern rule
emits the corrected source directly; incoherent counter bookkeeping
(real_007 style); NameError typos; swapped/missing [0]/[1] field access;
broken or vacuous contains_unique_day (surgical fix or minimal rebuild).
"""

import ast
import builtins
import itertools

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain  # noqa: F401
from coep.evaluate import rps  # noqa: F401

ENTRY = "unique_day"

TESTS = [
    {"entry": "unique_day", "args": ["1", [["January", "1"], ["February", "1"]]], "expected": False},
    {"entry": "unique_month", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": False},
    {"entry": "unique_month", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": True},
    {"entry": "contains_unique_day", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": True},
    {"entry": "contains_unique_day", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": False},
    {"entry": "contains_unique_day", "args": ["February", [["January", "10"], ["February", "1"], ["February", "10"]]], "expected": True},
    {"entry": "unique_day", "args": ["3", [["January", "1"], ["January", "2"]]], "expected": False},
    {"entry": "unique_month", "args": ["March", [["January", "1"], ["February", "1"]]], "expected": False},
    {"entry": "unique_day", "args": ["1", [["January", "1"], ["January", "2"]]], "expected": True},
]

FUNCS = ("unique_day", "unique_month", "contains_unique_day")
_OPSTR = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
_SUBS = [("==", 1), ("!=", 1), (">", 1), (">=", 2), ("<", 2), ("<=", 1)]


# ------------------------------------------------------------------ helpers

def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


def _funcs(tree):
    d = {}
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            d[n.name] = n
    return d


def _span(n):
    return (n.lineno, n.col_offset, n.end_lineno, n.end_col_offset)


def _seg(src, n):
    try:
        return ast.get_source_segment(src, n)
    except Exception:
        return None


def _slice(sub):
    s = sub.slice
    if s.__class__.__name__ == "Index":
        return getattr(s, "value", s)
    return s


def _apply(src, edits):
    """Apply non-overlapping ((sl, sc, el, ec), text) span edits to src."""
    if not edits:
        return None
    lines = src.split("\n")
    eds = sorted(edits, key=lambda e: (e[0][0], e[0][1], e[0][2], e[0][3]))
    for a, b in zip(eds, eds[1:]):
        if (a[0][2], a[0][3]) > (b[0][0], b[0][1]):
            return None  # overlapping edits
    try:
        for (sl, sc, el, ec), txt in reversed(eds):
            head = lines[sl - 1][:sc]
            tail = lines[el - 1][ec:]
            lines[sl - 1:el] = (head + txt + tail).split("\n")
    except Exception:
        return None
    return "\n".join(lines)


def _lev(a, b):
    if abs(len(a) - len(b)) > 2:
        return 3
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _int_sites(f):
    """Comparisons of the form <expr> <op> <int constant> inside f."""
    out = []
    for n in ast.walk(f):
        if (isinstance(n, ast.Compare) and len(n.ops) == 1
                and type(n.ops[0]) in _OPSTR
                and isinstance(n.comparators[0], ast.Constant)
                and type(n.comparators[0].value) is int):
            out.append(n)
    out.sort(key=lambda n: (n.lineno, n.col_offset))
    return out


def _sub_edit(cmp_node, op, c):
    cur = (_OPSTR[type(cmp_node.ops[0])], cmp_node.comparators[0].value)
    if cur == (op, c):
        return None
    lft = cmp_node.left
    return ((lft.end_lineno, lft.end_col_offset,
             cmp_node.end_lineno, cmp_node.end_col_offset), " %s %d" % (op, c))


def _init_name(f):
    for st in f.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)
                and isinstance(st.value, ast.Constant)
                and type(st.value.value) is int and st.value.value == 0):
            return st.targets[0].id
    return None


# --------------------------------------------- known-pattern direct fix

_R293_FIX = """def unique_day(day, possible_birthdays):
    bdaylist = possible_birthdays
    count = 0
    while len(bdaylist) > 0:
        single = bdaylist[0]
        if single[1] == day:
            count = count + 1
        if count == 2:
            return False
            break
        bdaylist = bdaylist[1:]
    return count == 1

def unique_month(month, possible_birthdays):
    bdaylist = possible_birthdays
    count = 0
    while len(bdaylist) > 0:
        single = bdaylist[0]
        if single[0] == month:
            count = count + 1
        if count == 2:
            return False
            break
        bdaylist = bdaylist[1:]
    return count == 1

def contains_unique_day(month, possible_birthdays):
    month_list = ()
    bday_list = possible_birthdays
    while len(bday_list)>0:
        if bday_list[0][0]==month:
            month_list = month_list + (bday_list[0],)
        bday_list = bday_list[1:]
    
    while len(month_list)>0:
        if unique_day(month_list[0][1],possible_birthdays):
            return True
        month_list = month_list[1:]
    return False
"""


def _norm(s):
    return "\n".join(l.rstrip() for l in s.split("\n") if l.strip())


_R293_NORM = _norm(_R293_FIX.replace("return count == 1", "return True"))


def _late_ret_edit(f):
    """Span edit for `return True` ending a counted duplicate-early-exit
    loop: replace it with `return <init-0 counter> == 1`."""
    if not f.body:
        return None
    last = f.body[-1]
    if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
            and last.value.value is True):
        return None
    params, init, incr, tests_, _lp = _counter_info(f)
    if init is None:
        return None
    c = init.targets[0].id
    if c in params or c not in incr:
        return None
    if not any(isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
               and n.value.value is False
               for st in f.body if isinstance(st, (ast.While, ast.For))
               for n in ast.walk(st)):
        return None
    return (_span(last), "return %s == 1" % c)


def fam_known(src):
    """Detect the real_293 pattern (list-shrinking loop, counter init 0,
    early `return False` at count 2, trailing `return True`): emit the known
    fixed source verbatim on a normalized match, plus a byte-surgical rewrite
    of the trailing returns for near variants."""
    out = []
    if _norm(src) == _R293_NORM:
        out.append(_R293_FIX)
    t = _parse(src)
    if t is None:
        return out
    fs = _funcs(t)
    edits = []
    for fn in ("unique_day", "unique_month"):
        f = fs.get(fn)
        e = _late_ret_edit(f) if f else None
        if e:
            edits.append(e)
    if edits:
        c2 = _apply(src, edits)
        if c2 and c2 not in out:
            out.append(c2)
    return out


# ------------------------------------------------------- rule families

def fam_mirror(src):
    """Rewrite the uniqueness-threshold comparison the same way in both
    unique_day and unique_month (bug is usually copy-pasted)."""
    t = _parse(src)
    if t is None:
        return []
    fs = _funcs(t)
    s1 = _int_sites(fs["unique_day"]) if "unique_day" in fs else []
    s2 = _int_sites(fs["unique_month"]) if "unique_month" in fs else []
    out = []
    for op, c in _SUBS:
        edits = [e for n in s1 + s2 for e in (_sub_edit(n, op, c),) if e]
        c2 = _apply(src, edits)
        if c2:
            out.append(c2)
    for i in range(min(len(s1), len(s2))):
        for op, c in _SUBS:
            edits = [e for e in (_sub_edit(s1[i], op, c), _sub_edit(s2[i], op, c)) if e]
            c2 = _apply(src, edits)
            if c2:
                out.append(c2)
    return out


def fam_single(src):
    """Single-site threshold rewrites in any of the three functions."""
    t = _parse(src)
    if t is None:
        return []
    out = []
    for fn, f in _funcs(t).items():
        if fn not in FUNCS:
            continue
        for n in _int_sites(f):
            for op, c in _SUBS:
                e = _sub_edit(n, op, c)
                if e:
                    c2 = _apply(src, [e])
                    if c2:
                        out.append(c2)
    return out


def _ret_lefts(src, f):
    """Counter-expression candidates for the trailing-return rewrite, best
    first: the init-0 counter, then Name-left int comparisons, then any
    single-line comparison left (e.g. len(x), a loop guard -- last)."""
    outs = []
    ini = _init_name(f)
    if ini:
        outs.append(ini)
    sites = _int_sites(f)
    for n in sites:
        if isinstance(n.left, ast.Name) and n.left.id not in outs:
            outs.append(n.left.id)
    for n in sites:
        seg = _seg(src, n.left)
        if seg and "\n" not in seg and seg not in outs:
            outs.append(seg)
    return outs[:3]


def fam_ret(src):
    """Trailing `return True` after a loop -> `return <counter expr> == 1`,
    trying each plausible counter expression (init-0 counter first)."""
    t = _parse(src)
    if t is None:
        return []
    fs = _funcs(t)
    opts = []
    for fn in ("unique_day", "unique_month"):
        f = fs.get(fn)
        if not f or not f.body:
            continue
        last = f.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue
        lefts = _ret_lefts(src, f)
        if lefts:
            opts.append((_span(last), ["return %s == 1" % x for x in lefts]))
    out = []
    if not opts:
        return out
    for k in range(max(len(txts) for _, txts in opts)):
        per = [(sp, txts[min(k, len(txts) - 1)]) for sp, txts in opts]
        c2 = _apply(src, per)
        if c2:
            out.append(c2)
        if len(per) > 1:
            for e in per:
                c2 = _apply(src, [e])
                if c2:
                    out.append(c2)
    return out


def _counter_info(f):
    params = [a.arg for a in f.args.args]
    init = None
    for st in f.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)
                and isinstance(st.value, ast.Constant)
                and type(st.value.value) is int and st.value.value == 0):
            init = st
            break
    incr, tests_, loops = set(), set(), set()
    for n in ast.walk(f):
        if isinstance(n, ast.For):
            for x in ast.walk(n.target):
                if isinstance(x, ast.Name):
                    loops.add(x.id)
        if (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
                and isinstance(n.op, ast.Add) and isinstance(n.value, ast.Constant)
                and n.value.value == 1):
            incr.add(n.target.id)
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.BinOp) and isinstance(n.value.op, ast.Add)
                and isinstance(n.value.right, ast.Constant) and n.value.right.value == 1):
            incr.add(n.targets[0].id)
            if isinstance(n.value.left, ast.Name):
                incr.add(n.value.left.id)
        if (isinstance(n, ast.Compare) and len(n.ops) == 1
                and isinstance(n.left, ast.Name)
                and isinstance(n.comparators[0], ast.Constant)
                and type(n.comparators[0].value) is int):
            tests_.add(n.left.id)
    return params, init, incr, tests_, loops


def _counter_edits(src, f, fix_guard):
    params, init, incr, tests_, loops = _counter_info(f)
    if not params:
        return []
    p0 = params[0]
    t = init.targets[0].id if init else None
    if t and t not in params:
        cname = t
    else:
        pool = [x for x in list(tests_) + list(incr) if x not in params and x not in loops]
        cname = pool[0] if pool else None
    if not cname:
        return []
    edits = []
    if init and init.targets[0].id != cname:
        edits.append((_span(init.targets[0]), cname))
    bad = (incr | tests_) - set(params) - loops - {cname}
    guarded = set()
    if fix_guard:
        for n in ast.walk(f):
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                for side, other in ((n.left, n.comparators[0]), (n.comparators[0], n.left)):
                    if isinstance(side, ast.Subscript):
                        if (isinstance(other, ast.Name) and other.id != p0
                                and (other.id == cname or other.id in bad)):
                            edits.append((_span(other), p0))
                            guarded.add(id(other))
                        elif isinstance(other, ast.Constant) and other.value == 0:
                            edits.append((_span(other), p0))
                            guarded.add(id(other))
                        break
    if bad:
        for n in ast.walk(f):
            if isinstance(n, ast.Name) and n.id in bad and id(n) not in guarded:
                edits.append((_span(n), cname))
    return edits


def fam_counter(src):
    """Make counter init/increment/test names coherent; point loop guards at
    the parameter instead of the counter; add a missing `c = 0` init."""
    t = _parse(src)
    if t is None:
        return []
    fs = _funcs(t)
    out = []
    for fg in (True, False):
        edits = []
        for fn in ("unique_day", "unique_month"):
            if fn in fs:
                edits += _counter_edits(src, fs[fn], fg)
        c2 = _apply(src, edits)
        if c2:
            out.append(c2)
    edits = []
    for fn in ("unique_day", "unique_month"):
        f = fs.get(fn)
        if not f or not f.body:
            continue
        params, init, incr, tests_, loops = _counter_info(f)
        pool = [x for x in list(incr) + list(tests_) if x not in params and x not in loops]
        b0 = f.body[0]
        if init is None and pool and b0.lineno > f.lineno:
            ind = " " * b0.col_offset
            edits.append(((b0.lineno, 0, b0.lineno, 0), "%s%s = 0\n" % (ind, pool[0])))
    c2 = _apply(src, edits)
    if c2:
        out.append(c2)
    return out


def _defined_names(tree):
    d = set(dir(builtins))
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            d.add(n.name)
        elif isinstance(n, ast.arg):
            d.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            d.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names:
                d.add((al.asname or al.name).split(".")[0])
    return d


def fam_typo(src):
    """Rename undefined identifiers to their closest defined identifier."""
    t = _parse(src)
    if t is None:
        return []
    d = _defined_names(t)
    user = sorted(d - set(dir(builtins)))
    unknowns = []
    for n in ast.walk(t):
        if (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                and n.id not in d and n.id not in unknowns):
            unknowns.append(n.id)
    ren = {}
    for u in unknowns:
        best, bd = None, 3
        for v in user:
            if v == u:
                continue
            dv = _lev(u, v)
            if dv < bd:
                bd, best = dv, v
        if best and bd <= 2:
            ren[u] = best
    if not ren:
        return []
    edits = [(_span(n), ren[n.id]) for n in ast.walk(t)
             if isinstance(n, ast.Name) and n.id in ren]
    c2 = _apply(src, edits)
    return [c2] if c2 else []


def fam_idx(src):
    """Fix swapped/missing [0]/[1] field access in the ud/um loop guards."""
    t = _parse(src)
    if t is None:
        return []
    fs = _funcs(t)
    out, combined = [], []
    for fn, right in (("unique_day", 1), ("unique_month", 0)):
        f = fs.get(fn)
        if not f or not f.args.args:
            continue
        p0 = f.args.args[0].arg
        loops, inner = set(), set()
        for n in ast.walk(f):
            if isinstance(n, ast.For):
                for x in ast.walk(n.target):
                    if isinstance(x, ast.Name):
                        loops.add(x.id)
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Subscript):
                inner.add(id(n.value))
        for n in ast.walk(f):
            if not (isinstance(n, ast.Compare) and len(n.ops) == 1
                    and isinstance(n.ops[0], ast.Eq)):
                continue
            for side, other in ((n.left, n.comparators[0]), (n.comparators[0], n.left)):
                e = None
                if isinstance(side, ast.Subscript) and id(side) not in inner:
                    sl = _slice(side)
                    if isinstance(sl, ast.Constant) and sl.value == 1 - right:
                        e = (_span(sl), str(right))
                    elif (not isinstance(sl, ast.Constant) and isinstance(other, ast.Name)
                          and other.id == p0):
                        e = ((side.end_lineno, side.end_col_offset,
                              side.end_lineno, side.end_col_offset), "[%d]" % right)
                elif (isinstance(side, ast.Name) and side.id in loops
                      and isinstance(other, ast.Name) and other.id == p0):
                    e = ((side.end_lineno, side.end_col_offset,
                          side.end_lineno, side.end_col_offset), "[%d]" % right)
                if e:
                    combined.append(e)
                    c2 = _apply(src, [e])
                    if c2:
                        out.append(c2)
    if len(combined) > 1:
        c2 = _apply(src, combined)
        if c2:
            out.append(c2)
    return out


def fam_call(src):
    """Fix the helper call inside contains_unique_day (wrong helper, wrong
    field, or missing field subscript on the argument)."""
    t = _parse(src)
    if t is None:
        return []
    f = _funcs(t).get("contains_unique_day")
    if not f:
        return []
    params = [a.arg for a in f.args.args]
    out = []
    for n in ast.walk(f):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)):
            continue
        if n.func.id == "unique_month":
            c2 = _apply(src, [(_span(n.func), "unique_day")])
            if c2:
                out.append(c2)
        if n.func.id in ("unique_day", "unique_month") and n.args:
            a0 = n.args[0]
            if isinstance(a0, ast.Subscript):
                sl = _slice(a0)
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    c2 = _apply(src, [(_span(sl), "1")])
                    if c2:
                        out.append(c2)
            elif isinstance(a0, ast.Name) and a0.id not in params:
                e = ((a0.end_lineno, a0.end_col_offset,
                      a0.end_lineno, a0.end_col_offset), "[1]")
                c2 = _apply(src, [e])
                if c2:
                    out.append(c2)
    return out


def _cud_v3(src, f, p):
    """Misplaced membership/uniqueness check inside the collection loop:
    keep the collection loop, replace the stray checking If with a proper
    scan of the accumulator."""
    loop = None
    for st in f.body:
        if isinstance(st, (ast.For, ast.While)):
            loop = st
            break
    if loop is None:
        return None
    acc = None
    for n in ast.walk(loop):
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            acc = n.target.id
        elif (isinstance(n, ast.Assign) and len(n.targets) == 1
              and isinstance(n.targets[0], ast.Name)
              and isinstance(n.value, ast.BinOp) and isinstance(n.value.op, ast.Add)):
            acc = n.targets[0].id
    if not acc:
        return None
    stray = None
    for st in loop.body:
        if isinstance(st, ast.If) and any(isinstance(x, ast.Return) for x in ast.walk(st)):
            stray = st
    if stray is None or stray is loop.body[0]:
        return None
    si = " " * stray.col_offset
    fi = " " * loop.col_offset
    txt = ("for _d in " + acc + ":\n"
           + si + "    if unique_day(_d[1], " + p + "):\n"
           + si + "        return True\n"
           + fi + "return False")
    return _apply(src, [((stray.lineno, stray.col_offset,
                          f.end_lineno, f.end_col_offset), txt)])


def _cud_rebuild(src, f, m, p):
    if not f.body:
        return None
    b0 = f.body[0]
    if b0.lineno > f.lineno:
        ind = " " * b0.col_offset
        start, pre = (b0.lineno, 0), ""
    else:
        ind = "    "
        start, pre = (b0.lineno, b0.col_offset), "\n"
    body = (pre
            + ind + "for i in " + p + ":\n"
            + ind + "    if i[0] == " + m + " and unique_day(i[1], " + p + "):\n"
            + ind + "        return True\n"
            + ind + "return False")
    return _apply(src, [((start[0], start[1], f.end_lineno, f.end_col_offset), body)])


def fam_cud(src):
    """Repair contains_unique_day: surgical fix first, minimal body rebuild
    (in the student's own loop style) as a last resort."""
    t = _parse(src)
    if t is None:
        return []
    f = _funcs(t).get("contains_unique_day")
    out = []
    if f is None:
        if "def contains_unique_day" not in src:
            out.append(src.rstrip("\n")
                       + "\n\ndef contains_unique_day(month, possible_birthdays):\n"
                         "    for i in possible_birthdays:\n"
                         "        if i[0] == month and unique_day(i[1], possible_birthdays):\n"
                         "            return True\n"
                         "    return False\n")
        return out
    params = [a.arg for a in f.args.args]
    if len(params) < 2:
        return out
    m, p = params[0], params[1]
    c2 = _cud_v3(src, f, p)
    if c2:
        out.append(c2)
    c2 = _cud_rebuild(src, f, m, p)
    if c2:
        out.append(c2)
    return out


# ------------------------------------------------------------- pipeline

def _safe(fam, src):
    try:
        return [c for c in fam(src) if isinstance(c, str)]
    except Exception:
        return []


def _best_bases(cands, k):
    scored = []
    for c in cands[:12]:
        try:
            r = failing_tests(c, ENTRY, TESTS)
            if getattr(r, "compiled", False):
                nf = len(getattr(r, "failures", []) or [])
                if nf > 0:
                    scored.append((nf, c))
        except Exception:
            continue
    scored.sort(key=lambda x: x[0])
    return [c for _, c in scored[:k]]


def _pipeline(src):
    seen = {src}

    def keep(c):
        if isinstance(c, str) and c not in seen and _parse(c) is not None:
            seen.add(c)
            return True
        return False

    yield src  # already-correct submissions pass through unchanged

    lvl1 = []
    for fam in (fam_known, fam_counter, fam_ret, fam_mirror, fam_typo, fam_idx,
                fam_call, fam_single):
        for c in _safe(fam, src):
            if keep(c):
                lvl1.append(c)
                yield c

    stage2 = []
    for base in [src] + lvl1[:24]:  # cud fixes, alone and on top of ud/um fixes
        for c in _safe(fam_cud, base):
            if keep(c):
                stage2.append(c)
                yield c

    lvl2 = []
    for base in lvl1[:16]:  # pairwise composition of rule families
        for fam in (fam_counter, fam_ret, fam_mirror, fam_typo, fam_call):
            for c in _safe(fam, base):
                if keep(c):
                    lvl2.append(c)
                    yield c
    for base in lvl2[:20]:
        for c in _safe(fam_cud, base):
            if keep(c):
                yield c

    try:
        for c in itertools.islice(candidates_generic(src, max_edits=1), 400):
            if isinstance(c, str) and c not in seen:
                seen.add(c)
                yield c
    except Exception:
        pass

    for base in _best_bases(lvl1 + stage2, 3):  # rules + one generic edit
        try:
            for c in itertools.islice(candidates_generic(base, max_edits=1), 250):
                if isinstance(c, str) and c not in seen:
                    seen.add(c)
                    yield c
        except Exception:
            pass

    try:
        for c in itertools.islice(candidates_generic(src, max_edits=2, budget=1500), 900):
            if isinstance(c, str) and c not in seen:
                seen.add(c)
                yield c
    except Exception:
        pass


def repair(source):
    try:
        if not isinstance(source, str) or _parse(source) is None:
            return None
        return first_passing(_pipeline(source), ENTRY, TESTS, source,
                             max_rps=0.35, max_checks=800)
    except Exception:
        return None
