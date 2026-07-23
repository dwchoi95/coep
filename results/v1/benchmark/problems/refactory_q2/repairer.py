"""Local, LLM-free automatic repairer for the "Unique dates and months" assignment.

Post-mortem of the previous round (0/5 repaired): every problem-specific rewrite
was produced with ast.unparse, which reformats the WHOLE file (drops blank lines,
trailing spaces, `range (len(...))` spacing, normalises indentation).  For real
student files that reformatting alone pushed the relative patch size far past the
0.35 cap, so every semantically-correct candidate was filtered out, and the
generic 1/2-edit search cannot fix the multi-line, multi-function bugs these
submissions contain.

This revision therefore never unparses a candidate.  Every rule detects its
structural pattern with the AST but applies the fix as *surgical line edits* on
the original text (all untouched lines stay byte-identical), keeping the patch
tiny.  The targeted rules, derived by hand-tracing the five failing samples:

  R1 _fix_threshold   (real_359, real_386, real_431): `count >= 2 / > 1` ->
     `!= 1` and `count < 2 / <= 1` -> `== 1` inside unique_day/unique_month,
     so zero occurrences are no longer "unique" (visible tests 7 and 8).
  R2 _fix_tail_true   (real_293): counting loop early-returns False on a
     duplicate but falls through to a blanket `return True`; replace that line
     with `return <counter> == 1`.
  R3 _fix_counter_trio (real_007): inconsistent counter trio (init `days = 0`,
     increment `day = day + 1`, test `days == 1`, or the init shadowing the
     `month` parameter) is unified onto one canonical counter name, and an
     element compared against the counter (`pb[i][1] == days`) is re-pointed at
     the function's first parameter.
  R4 _fix_typos: undefined names renamed to the closest defined name.
  R5 _contains_restructure (real_431): loop that collects the month's entries
     but decides inside the loop with a trailing `if len(x) > 1 ... else return
     unique_day(...)`; the decision block is replaced by a post-loop scan
     `for v in x: if unique_day(v[1], pb): return True / return False`.
  R6 _contains_rebuild (real_386): empty / hopeless contains_unique_day body is
     replaced by a single `return any(p[0] == month and unique_day(p[1], pb)
     for p in pb)` line reusing the student's own (already repaired) unique_day.

Candidates = single rules, one composition round, contains-variants layered on
the fixed bases, then the generic 1/2-edit search as a last resort.  Everything
is validated through first_passing (multi-function suite driven via a tiny
appended dispatcher); a local test-runner is kept as a safety net so a
first_passing API hiccup can never zero out the whole assignment again.
"""

import ast
import builtins
import copy
import difflib
import re
import threading
import time

try:
    from coep.repairlib import first_passing
except Exception:  # pragma: no cover
    first_passing = None
try:
    from coep.repairlib import candidates_generic
except Exception:  # pragma: no cover
    candidates_generic = None
try:
    from coep.evaluate import rps as _rps_real
except Exception:  # pragma: no cover
    _rps_real = None

# The visible test suite (with the function each test calls).
TESTS = [
    {"func": "unique_day", "args": ["1", [["January", "1"], ["February", "1"]]], "expected": False},
    {"func": "unique_month", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": False},
    {"func": "unique_month", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": True},
    {"func": "contains_unique_day", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": True},
    {"func": "contains_unique_day", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": False},
    {"func": "contains_unique_day", "args": ["February", [["January", "10"], ["February", "1"], ["February", "10"]]], "expected": True},
    {"func": "unique_day", "args": ["3", [["January", "1"], ["January", "2"]]], "expected": False},
    {"func": "unique_month", "args": ["March", [["January", "1"], ["February", "1"]]], "expected": False},
    {"func": "unique_day", "args": ["1", [["January", "1"], ["January", "2"]]], "expected": True},
]

# The suite exercises three functions; first_passing drives one entry point, so
# every candidate (and the original, for a fair patch-size baseline) gets the
# same tiny dispatcher appended, which is stripped again before returning.
ENTRY = "_coep_dispatch"
_SUFFIX = (
    "\n\ndef _coep_dispatch(_coep_fname, *_coep_args):\n"
    "    return globals()[_coep_fname](*_coep_args)\n"
)
DTESTS = [{"args": [t["func"]] + list(t["args"]), "expected": t["expected"]} for t in TESTS]

_CAP = 0.35
_BUDGET = 6.0
_COUNT_FNS = ("unique_day", "unique_month")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def _compiles(s):
    try:
        compile(s, "<cand>", "exec")
        return True
    except Exception:
        return False


def _fns(src):
    """[(FunctionDef node, [param names])] for top-level defs, or None."""
    try:
        tree = ast.parse(src)
    except Exception:
        return None
    return [(n, [a.arg for a in n.args.args])
            for n in tree.body if isinstance(n, ast.FunctionDef)]


def _int1(c):
    return (isinstance(c, ast.Constant) and c.value == 1
            and isinstance(c.value, int) and not isinstance(c.value, bool))


def _indent_of(line):
    return line[:len(line) - len(line.lstrip())]


def _local_rps(a, b):
    """Conservative local proxy for the harness's relative patch size."""
    try:
        la, lb = a.split("\n"), b.split("\n")
        sm = difflib.SequenceMatcher(None, la, lb)
        ch = sum(max(i2 - i1, j2 - j1)
                 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")
        line_r = ch / max(1, len(la))
        char_r = 1.0 - difflib.SequenceMatcher(None, a, b).ratio()
        return max(line_r, char_r)
    except Exception:
        return 1.0


def _rps(a, b):
    if _rps_real is not None:
        try:
            return _rps_real(a, b)
        except Exception:
            pass
    return _local_rps(a, b)


# --------------------------------------------------------------------------- #
# rules: AST-guided detection, text-preserving line edits
# --------------------------------------------------------------------------- #

_THRESH = [
    (ast.GtE, 2, r">=\s*2", "!= 1"),
    (ast.Gt, 1, r">\s*1", "!= 1"),
    (ast.Lt, 2, r"<\s*2", "== 1"),
    (ast.LtE, 1, r"<=\s*1", "== 1"),
]


def _fix_threshold(src):
    """R1: 'at most one occurrence' misconception in the counting functions."""
    fns = _fns(src)
    if not fns:
        return None
    lines = src.split("\n")
    hit = False
    for fn, _ in fns:
        if fn.name not in _COUNT_FNS:
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            if not any(isinstance(x, ast.Return) for x in node.body):
                continue
            t = node.test
            if not (isinstance(t, ast.Compare) and len(t.ops) == 1
                    and len(t.comparators) == 1):
                continue
            c = t.comparators[0]
            if not (isinstance(c, ast.Constant) and isinstance(c.value, int)
                    and not isinstance(c.value, bool) and c.value in (1, 2)):
                continue
            for opc, v, pat, rep in _THRESH:
                if isinstance(t.ops[0], opc) and c.value == v:
                    i = t.lineno - 1
                    if 0 <= i < len(lines):
                        new = re.sub(pat, rep, lines[i], count=1)
                        if new != lines[i]:
                            lines[i] = new
                            hit = True
                    break
    return "\n".join(lines) if hit else None


def _counter_of(fn):
    """Name of a numeric counter incremented by 1 inside fn, if any."""
    for node in ast.walk(fn):
        if (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
                and isinstance(node.op, ast.Add) and _int1(node.value)):
            return node.target.id
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            v = node.value
            if (isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add)
                    and isinstance(v.left, ast.Name) and _int1(v.right)):
                return node.targets[0].id
    return None


def _fix_tail_true(src):
    """R2: counting loop ends in a blanket `return True` -> `return c == 1`."""
    fns = _fns(src)
    if not fns:
        return None
    lines = src.split("\n")
    hit = False
    for fn, _ in fns:
        if fn.name not in _COUNT_FNS or not fn.body:
            continue
        last = fn.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue
        cnt = _counter_of(fn)
        if not cnt:
            continue
        i = last.lineno - 1
        if 0 <= i < len(lines):
            lines[i] = _indent_of(lines[i]) + "return " + cnt + " == 1"
            hit = True
    return "\n".join(lines) if hit else None


def _fix_counter_trio(src):
    """R3: unify inconsistent init/increment/test counter names (including a
    parameter-shadowing init) and re-point element-vs-counter comparisons at
    the function's first parameter."""
    fns = _fns(src)
    if not fns:
        return None
    lines = src.split("\n")
    hit = False
    for fn, params in fns:
        if fn.name not in _COUNT_FNS or not params:
            continue
        p0, pset = params[0], set(params)
        inits, incs, conds, match = [], [], [], []
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                v = node.value
                if (isinstance(v, ast.Constant) and v.value == 0
                        and isinstance(v.value, int) and not isinstance(v.value, bool)):
                    inits.append((node.lineno - 1, node.targets[0].id))
                    continue
                if (isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add)
                        and isinstance(v.left, ast.Name) and _int1(v.right)):
                    incs.append((node.lineno - 1, node.targets[0].id, v.left.id))
                    continue
            if (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
                    and isinstance(node.op, ast.Add) and _int1(node.value)):
                incs.append((node.lineno - 1, node.target.id, node.target.id))
                continue
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.Eq) and len(node.comparators) == 1):
                l, r = node.left, node.comparators[0]
                if (isinstance(l, ast.Name) and isinstance(r, ast.Constant)
                        and r.value == 1 and isinstance(r.value, int)
                        and not isinstance(r.value, bool)):
                    conds.append((node.lineno - 1, l.id))
                    continue
                if isinstance(l, ast.Subscript) and isinstance(r, ast.Name):
                    match.append((node.lineno - 1, r.id, "r"))
                elif isinstance(r, ast.Subscript) and isinstance(l, ast.Name):
                    match.append((node.lineno - 1, l.id, "l"))
        if not incs:
            continue
        names = ({n for _, n in inits} | {t for _, t, _ in incs}
                 | {u for _, _, u in incs} | {n for _, n in conds})
        broken = len(names) > 1 or any(n in pset for _, n in inits)
        if broken:
            cands = ([n for _, n in conds if n not in pset]
                     + [n for _, n in inits if n not in pset]
                     + [t for _, t, _ in incs if t not in pset] + ["count"])
            canon = cands[0]
            for i, n in inits:
                if n != canon and 0 <= i < len(lines):
                    new = re.sub(r"^(\s*)" + re.escape(n) + r"\b",
                                 r"\g<1>" + canon, lines[i], count=1)
                    if new != lines[i]:
                        lines[i] = new
                        hit = True
            for i, t, u in incs:
                if 0 <= i < len(lines) and (t != canon or u != canon):
                    new = re.sub(r"^(\s*)(\w+)(\s*=\s*)(\w+)(\s*\+\s*1)",
                                 r"\g<1>" + canon + r"\g<3>" + canon + r"\g<5>",
                                 lines[i], count=1)
                    if new == lines[i]:
                        new = re.sub(r"^(\s*)(\w+)(\s*\+=)",
                                     r"\g<1>" + canon + r"\g<3>", lines[i], count=1)
                    if new != lines[i]:
                        lines[i] = new
                        hit = True
            for i, n in conds:
                if n != canon and 0 <= i < len(lines):
                    new = re.sub(r"\b" + re.escape(n) + r"\b(?=\s*==\s*1\b)",
                                 canon, lines[i], count=1)
                    if new != lines[i]:
                        lines[i] = new
                        hit = True
        # element compared against the counter instead of the parameter
        for i, n, side in match:
            if n in pset or n not in names or not (0 <= i < len(lines)):
                continue
            if side == "r":
                new = re.sub(r"(==\s*)" + re.escape(n) + r"\b",
                             r"\g<1>" + p0, lines[i], count=1)
            else:
                new = re.sub(r"\b" + re.escape(n) + r"\b(?=\s*==)",
                             p0, lines[i], count=1)
            if new != lines[i]:
                lines[i] = new
                hit = True
    return "\n".join(lines) if hit else None


def _fix_typos(src):
    """R4: rename undefined names to the closest defined name (line-scoped)."""
    fns = _fns(src)
    if not fns:
        return None
    lines = src.split("\n")
    hit = False
    fnnames = {f.name for f, _ in fns}
    bset = set(dir(builtins))
    for fn, params in fns:
        stored = {n.id for n in ast.walk(fn)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
        known = set(params) | stored | fnnames
        pool = sorted(known)
        done = set()
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)):
                continue
            nid = node.id
            if nid in known or nid in bset or nid in done:
                continue
            done.add(nid)
            m = difflib.get_close_matches(nid, pool, n=1, cutoff=0.6)
            if not m or m[0] == nid:
                continue
            i = node.lineno - 1
            if 0 <= i < len(lines):
                new = re.sub(r"\b" + re.escape(nid) + r"\b", m[0], lines[i])
                if new != lines[i]:
                    lines[i] = new
                    hit = True
    return "\n".join(lines) if hit else None


def _contains_restructure(src):
    """R5: contains_unique_day decides inside its collecting loop via a trailing
    `if len(x) > 1: ... else: return ...` block; move the decision after the
    loop as a scan over the collected month entries."""
    fns = _fns(src)
    if not fns:
        return None
    lines = src.split("\n")
    for fn, params in fns:
        if fn.name != "contains_unique_day" or len(params) < 2:
            continue
        pb = params[1]
        for node in ast.walk(fn):
            if not isinstance(node, ast.For):
                continue
            body = node.body
            if not body or not isinstance(body[-1], ast.If) or not body[-1].orelse:
                continue
            misp = body[-1]
            t = misp.test
            coll = None
            if (isinstance(t, ast.Compare) and isinstance(t.left, ast.Call)
                    and isinstance(t.left.func, ast.Name) and t.left.func.id == "len"
                    and t.left.args and isinstance(t.left.args[0], ast.Name)):
                coll = t.left.args[0].id
            if not coll:
                continue
            if not any(isinstance(x, ast.Return) for x in misp.body + misp.orelse):
                continue
            lv = node.target.id if isinstance(node.target, ast.Name) else "_bd"
            s = misp.lineno - 1
            e = getattr(misp, "end_lineno", None)
            if e is None or not (0 <= s < e <= len(lines)):
                continue
            ind = _indent_of(lines[node.lineno - 1])
            repl = [ind + "for " + lv + " in " + coll + ":",
                    ind + "    if unique_day(" + lv + "[1], " + pb + "):",
                    ind + "        return True",
                    ind + "return False"]
            return "\n".join(lines[:s] + repl + lines[e:])
    return None


def _contains_rebuild(src):
    """R6: replace the whole contains_unique_day body with one `any(...)` line
    that reuses the student's own unique_day."""
    fns = _fns(src)
    if not fns:
        return None
    lines = src.split("\n")
    for fn, params in fns:
        if fn.name != "contains_unique_day" or len(params) < 2 or not fn.body:
            continue
        m, pb = params[0], params[1]
        v = "_bd"
        while v in (m, pb):
            v = "_" + v
        s = fn.body[0].lineno - 1
        e = getattr(fn.body[-1], "end_lineno", None)
        if e is None or not (0 <= s < e <= len(lines)):
            continue
        ind = _indent_of(lines[s]) or "    "
        rep = (ind + "return any(" + v + "[0] == " + m + " and unique_day("
               + v + "[1], " + pb + ") for " + v + " in " + pb + ")")
        return "\n".join(lines[:s] + [rep] + lines[e:])
    return None


# --------------------------------------------------------------------------- #
# candidate assembly and validation
# --------------------------------------------------------------------------- #

_RULES = (_fix_threshold, _fix_tail_true, _fix_counter_trio, _fix_typos)


def _targeted(src):
    out, seen = [], {src}

    def add(c):
        if isinstance(c, str) and c and c not in seen and _compiles(c):
            seen.add(c)
            out.append(c)
            return True
        return False

    singles = []
    for r in _RULES:
        try:
            v = r(src)
        except Exception:
            v = None
        if v and add(v):
            singles.append((r, v))
    # one composition round: copy-pasted bugs often need two different rules
    for r1, v in list(singles):
        for r2 in _RULES:
            if r2 is r1:
                continue
            try:
                w = r2(v)
            except Exception:
                w = None
            add(w)
    # contains_unique_day variants layered on the fixed bases (and on src)
    for b in out[:8] + [src]:
        for r in (_contains_restructure, _contains_rebuild):
            try:
                w = r(b)
            except Exception:
                w = None
            add(w)
    return out[:40]


def _passes_locally(cand):
    """Safety-net validator: run the visible suite in a fresh namespace."""
    res = {}

    def work():
        try:
            ns = {}
            exec(compile(cand, "<cand>", "exec"), ns)
            for t in TESTS:
                f = ns.get(t["func"])
                if not callable(f):
                    res["ok"] = False
                    return
                if f(*copy.deepcopy(t["args"])) != t["expected"]:
                    res["ok"] = False
                    return
            res["ok"] = True
        except Exception:
            res["ok"] = False

    try:
        th = threading.Thread(target=work, daemon=True)
        th.start()
        th.join(2.0)
    except Exception:
        return False
    return res.get("ok") is True


def _repair(src):
    if not isinstance(src, str) or not _compiles(src):
        return None
    deadline = time.monotonic() + _BUDGET
    targeted = [c for c in _targeted(src) if _rps(src, c) <= _CAP]
    aug = src + _SUFFIX

    def gen():
        seen = set()
        for c in [src] + targeted:
            if c not in seen:
                seen.add(c)
                yield c + _SUFFIX
        if candidates_generic is None:
            return
        for seed in [src] + targeted[:2]:
            if time.monotonic() > deadline:
                return
            try:
                for c in candidates_generic(seed, max_edits=1):
                    if time.monotonic() > deadline:
                        return
                    if isinstance(c, str) and c not in seen and _rps(src, c) <= _CAP:
                        seen.add(c)
                        yield c + _SUFFIX
            except Exception:
                pass
        try:
            for c in candidates_generic(src, max_edits=2):
                if time.monotonic() > deadline:
                    return
                if isinstance(c, str) and c not in seen and _rps(src, c) <= _CAP:
                    seen.add(c)
                    yield c + _SUFFIX
        except Exception:
            pass

    winner = None
    if first_passing is not None:
        for call in (
            lambda: first_passing(gen(), ENTRY, DTESTS, aug, max_rps=_CAP, max_checks=400),
            lambda: first_passing(gen(), ENTRY, DTESTS, aug, max_rps=_CAP),
            lambda: first_passing(gen(), ENTRY, DTESTS, aug),
            lambda: first_passing(gen(), ENTRY, DTESTS),
        ):
            try:
                w = call()
            except Exception:
                continue
            if isinstance(w, str) and w:
                winner = w
                break
    if winner:
        plain = winner[:-len(_SUFFIX)] if winner.endswith(_SUFFIX) else winner
        if _compiles(plain) and _rps(src, plain) <= _CAP:
            return plain
    # Safety net: if first_passing was unusable or found nothing, locally
    # verify the hand-built targeted candidates (already under the rps cap).
    for c in targeted:
        if time.monotonic() > deadline + 4:
            break
        if _passes_locally(c):
            return c
    return None


def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None
