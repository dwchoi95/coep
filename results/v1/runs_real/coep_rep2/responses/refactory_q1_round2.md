```python
"""Automatic repair for the "Sequential Search" assignment (local, LLM-free).

`search(x, seq)` must return the leftmost insertion point of `x` in the
sorted sequence `seq`: the first index i with x <= seq[i], len(seq) when x
is greater than every element, and 0 for an empty sequence.

Round-2 diagnosis of the unrepaired submissions (hand-traced):
  * real_099 -- correct on non-empty input, but the trailing `return i + 1`
    raises NameError on [] because the loop never binds `i`.  Replacing
    that single line with `return len(seq)` passes every visible test.
  * real_219 -- correct on non-empty input, but falls off the end (returns
    None) on [].  Appending the single line `return len(seq)` fixes it.
  * real_384 -- returns the right index whenever the loop reaches an
    element >= x, but when x exceeds every element (and on []) it runs past
    the loop into a no-op trailing string and returns None.  Appending the
    single line `return len(seq)` after that string fixes it.
Why round 1 missed them: the rules built exactly these repairs, but emitted
`ast.unparse(...)` of the whole tree, which reformats untouched lines
(`range (len(seq))` -> `range(len(seq))`, `x ==seq[i]` -> `x == seq[i]`,
parenthesised for-targets, the two-line trailing string collapsed onto one
line).  Those cosmetic diffs inflate the measured patch size, so
functionally correct candidates were rejected by the rps <= 0.35 cap (and
unparse-built candidates are fragile on older interpreters anyway).  Fix:
the problem-specific rules now patch the ORIGINAL TEXT line by line --
every untouched line stays byte-identical, so the measured patch is
exactly the one-line repair.  The unparse-based rules are kept as
fallbacks, then the generic mutation search (single edits, rule+edit
combinations, then two-edit search); every candidate is validated through
`first_passing`, which enforces the full visible test suite and the
rps <= 0.35 patch-size cap measured against the ORIGINAL submission.
"""

import ast
import time

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401  (patch-size metric; enforced via first_passing)

ENTRY = "search"

TESTS = [
    {"args": [42, [-5, 1, 3, 5, 7, 10]], "expected": 6},
    {"args": [42, [1, 5, 10]], "expected": 3},
    {"args": [5, [1, 5, 10]], "expected": 1},
    {"args": [7, [1, 5, 10]], "expected": 2},
    {"args": [3, [1, 5, 10]], "expected": 1},
    {"args": [-5, [1, 5, 10]], "expected": 0},
    {"args": [10, [-5, -1, 3, 5, 7, 10]], "expected": 5},
    {"args": [-100, [-5, -1, 3, 5, 7, 10]], "expected": 0},
    {"args": [0, [-5, -1, 3, 5, 7, 10]], "expected": 2},
    {"args": [100, []], "expected": 0},
    {"args": [-100, []], "expected": 0},
]

MAX_RPS = 0.35
_TIME_BUDGET = 8.5  # seconds; stay safely under the ~10 s limit


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _find_func(tree, name=ENTRY):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _len_call(sname):
    return ast.Call(
        func=ast.Name(id="len", ctx=ast.Load()),
        args=[ast.Name(id=sname, ctx=ast.Load())],
        keywords=[],
    )


def _is_len_call(node, sname):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == sname
    )


def _slice_expr(sub):
    s = sub.slice
    if s.__class__.__name__ == "Index":  # pre-3.9 compatibility
        s = getattr(s, "value", s)
    return s


def _is_last_index(e, sname):
    # -1  (parsed as USub(1)), a folded Constant(-1), or len(seq) - 1
    if (isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub)
            and isinstance(e.operand, ast.Constant)
            and e.operand.value == 1):
        return True
    if isinstance(e, ast.Constant) and e.value == -1:
        return True
    if (isinstance(e, ast.BinOp) and isinstance(e.op, ast.Sub)
            and _is_len_call(e.left, sname)
            and isinstance(e.right, ast.Constant) and e.right.value == 1):
        return True
    return False


def _is_last_elem(node, sname):
    # seq[-1] or seq[len(seq) - 1]
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == sname
        and _is_last_index(_slice_expr(node), sname)
    )


def _guard(sname):
    # if not seq: return 0
    return ast.If(
        test=ast.UnaryOp(op=ast.Not(),
                         operand=ast.Name(id=sname, ctx=ast.Load())),
        body=[ast.Return(value=ast.Constant(value=0))],
        orelse=[],
    )


def _boundary_ifs(fn, xname, sname):
    """If/elif nodes testing `x >= seq[-1]` (or `seq[-1] <= x`)."""
    out = []
    for node in ast.walk(fn):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)):
            continue
        t = node.test
        if len(t.ops) != 1 or len(t.comparators) != 1:
            continue
        op, left, right = t.ops[0], t.left, t.comparators[0]
        a = (isinstance(op, ast.GtE) and isinstance(left, ast.Name)
             and left.id == xname and _is_last_elem(right, sname))
        b = (isinstance(op, ast.LtE) and _is_last_elem(left, sname)
             and isinstance(right, ast.Name) and right.id == xname)
        if a or b:
            out.append(node)
    return out


def _lenm1_returns(fn, sname):
    """Return nodes of the form `return len(seq) - 1`."""
    out = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Return)
                and isinstance(node.value, ast.BinOp)
                and isinstance(node.value.op, ast.Sub)
                and _is_len_call(node.value.left, sname)
                and isinstance(node.value.right, ast.Constant)
                and node.value.right.value == 1):
            out.append(node)
    return out


def _name_returns(fn):
    """Return nodes of the form `return <name>`."""
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Name)]


def _nameplus1_returns(fn):
    """Return nodes of the form `return <name> + 1`."""
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.BinOp):
            v = n.value
            if (isinstance(v.op, ast.Add) and isinstance(v.left, ast.Name)
                    and isinstance(v.right, ast.Constant)
                    and v.right.value == 1):
                out.append(n)
    return out


def _break_loops(fn):
    """For/While loops containing a break and having no else clause."""
    out = []
    for node in ast.walk(fn):
        if isinstance(node, (ast.For, ast.While)) and not node.orelse:
            if any(isinstance(n, ast.Break) for n in ast.walk(node)):
                out.append(node)
    return out


# ---------------------------------------------------------------------------
# Byte-minimal text-level rewrite rules
#
# Each rule re-parses its input, locates the target statement via the AST,
# then edits `source.split("\n")` directly: one line replaced or inserted,
# every other line byte-identical.  This keeps the measured patch size of
# a candidate as small as the conceptual fix itself, whereas unparse-based
# candidates reformat the whole file and can blow the 0.35 rps cap.
# ---------------------------------------------------------------------------

def _parse_fn(source):
    """(fn, xname, sname, lines) for the `search` def, or None."""
    try:
        tree = ast.parse(source)
    except Exception:
        return None
    fn = _find_func(tree)
    if fn is None or len(fn.args.args) < 2:
        return None
    return fn, fn.args.args[0].arg, fn.args.args[1].arg, source.split("\n")


def _indent_of(line):
    return line[:len(line) - len(line.lstrip())]


def _replace_return_line(lines, ret, expr_text):
    """Rewrite the single source line holding `ret` as `return <expr_text>`."""
    if getattr(ret, "end_lineno", ret.lineno) != ret.lineno:
        return None  # multi-line return; out of scope for line surgery
    idx = ret.lineno - 1
    if not 0 <= idx < len(lines):
        return None
    line = lines[idx]
    if not line.strip().startswith("return"):
        return None  # shares its line with other code (e.g. `else: return i`)
    new = _indent_of(line) + "return " + expr_text
    if new == line:
        return None
    out = list(lines)
    out[idx] = new
    return "\n".join(out)


def _txt_fix_trailing_return(source):
    """Wrong final return (`return i + 1`, bare `return`, `return -1`, ...)
    -> `return len(seq)`, touching only that line.  (Fixes real_099: the
    loop never binds `i` on [], so `return i + 1` raised NameError.)"""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, _x, sname, lines = parsed
        last = fn.body[-1]
        if not isinstance(last, ast.Return):
            return None
        if last.value is not None and _is_len_call(last.value, sname):
            return None  # already the canonical trailing return
        return _replace_return_line(lines, last, "len(%s)" % sname)
    except Exception:
        return None


def _txt_append_return(source):
    """Function can run off its end -> append one line `return len(seq)`
    after the last body statement.  (Fixes real_219 and real_384, whose
    loops fall through -- past a no-op trailing string in real_384 --
    and return None for [] or for x greater than every element.)"""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, _x, sname, lines = parsed
        last = fn.body[-1]
        if isinstance(last, (ast.Return, ast.Raise)):
            return None
        if fn.body[0].lineno <= fn.lineno:
            return None  # one-line def; line surgery not applicable
        end = getattr(last, "end_lineno", None)
        if end is None or not 0 < end <= len(lines):
            return None
        if fn.body[0].lineno - 1 >= len(lines):
            return None
        ind = _indent_of(lines[fn.body[0].lineno - 1])
        out = lines[:end] + [ind + "return len(%s)" % sname] + lines[end:]
        return "\n".join(out)
    except Exception:
        return None


def _txt_insert_guard(source):
    """Missing empty-sequence handling -> insert one line
    `if not seq: return 0` before the first body statement."""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, _x, sname, lines = parsed
        first = fn.body[0]
        if first.lineno <= fn.lineno or first.lineno - 1 >= len(lines):
            return None
        ind = _indent_of(lines[first.lineno - 1])
        out = (lines[:first.lineno - 1]
               + [ind + "if not %s: return 0" % sname]
               + lines[first.lineno - 1:])
        return "\n".join(out)
    except Exception:
        return None


def _txt_lenm1_fix(source, k):
    """k-th `return len(seq) - 1` -> `return len(seq)` (that line only)."""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, _x, sname, lines = parsed
        rets = _lenm1_returns(fn, sname)
        if k >= len(rets):
            return None
        return _replace_return_line(lines, rets[k], "len(%s)" % sname)
    except Exception:
        return None


def _txt_minus_one(source, k):
    """k-th `return <name> + 1` -> `return <name>` (that line only)."""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, _x, _s, lines = parsed
        rets = _nameplus1_returns(fn)
        if k >= len(rets):
            return None
        return _replace_return_line(lines, rets[k], rets[k].value.left.id)
    except Exception:
        return None


def _txt_plus_one(source, k):
    """k-th `return <name>` -> `return <name> + 1` (that line only)."""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, _x, _s, lines = parsed
        rets = _name_returns(fn)
        if k >= len(rets):
            return None
        return _replace_return_line(lines, rets[k], rets[k].value.id + " + 1")
    except Exception:
        return None


def _txt_for_else(source, k):
    """k-th break-loop without else -> add `else: return len(seq)` lines
    right after the loop body; all existing lines untouched."""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, _x, sname, lines = parsed
        loops = _break_loops(fn)
        if k >= len(loops):
            return None
        node = loops[k]
        end = getattr(node, "end_lineno", None)
        if end is None or not 0 < end <= len(lines) or not node.body:
            return None
        head_ind = _indent_of(lines[node.lineno - 1])
        b0 = node.body[0]
        if b0.lineno > node.lineno and b0.lineno - 1 < len(lines):
            body_ind = _indent_of(lines[b0.lineno - 1])
        else:
            body_ind = head_ind + "    "
        out = (lines[:end]
               + [head_ind + "else:", body_ind + "return len(%s)" % sname]
               + lines[end:])
        return "\n".join(out)
    except Exception:
        return None


def _txt_boundary_fix(source, k, mode):
    """k-th boundary if `x >= seq[-1]: ... return len(seq) - 1`: strictify
    the comparison and/or return len(seq), editing only those lines."""
    try:
        parsed = _parse_fn(source)
        if parsed is None:
            return None
        fn, xname, sname, lines = parsed
        ifs = _boundary_ifs(fn, xname, sname)
        if k >= len(ifs):
            return None
        node = ifs[k]
        out = list(lines)
        if mode in ("both", "op"):
            idx = node.lineno - 1
            if not 0 <= idx < len(out):
                return None
            tok = ">=" if isinstance(node.test.ops[0], ast.GtE) else "<="
            if out[idx].count(tok) != 1:
                return None
            out[idx] = out[idx].replace(tok, tok[0], 1)  # >= -> > , <= -> <
        if mode in ("both", "ret"):
            hit = False
            for stmt in node.body:
                for r in ast.walk(stmt):
                    if isinstance(r, ast.Return):
                        if (r.lineno == node.lineno
                                or getattr(r, "end_lineno", r.lineno) != r.lineno):
                            return None  # shares the if-line / multi-line
                        j = r.lineno - 1
                        if not (0 <= j < len(out)
                                and out[j].strip().startswith("return")):
                            return None
                        out[j] = _indent_of(out[j]) + "return len(%s)" % sname
                        hit = True
            if not hit:
                return None
        res = "\n".join(out)
        return None if res == source else res
    except Exception:
        return None


def _text_candidates(source):
    """Byte-minimal candidate patches, most specific first; parseable and
    deduplicated.  These are tried before the unparse-based rules."""
    out, seen = [], set()

    def add(cand):
        if not cand or not isinstance(cand, str) or cand == source or cand in seen:
            return
        try:
            ast.parse(cand)
        except Exception:
            return
        seen.add(cand)
        out.append(cand)

    try:
        fix_ret = _txt_fix_trailing_return(source)
        app_ret = _txt_append_return(source)
        guard = _txt_insert_guard(source)
        add(fix_ret)
        add(app_ret)
        add(guard)
        # two-fault combos: empty-seq guard plus a trailing-return repair
        if guard:
            add(_txt_fix_trailing_return(guard))
            add(_txt_append_return(guard))
        for k in range(3):
            add(_txt_lenm1_fix(source, k))
        for k in range(3):
            for mode in ("both", "op", "ret"):
                add(_txt_boundary_fix(source, k, mode))
        for k in range(4):
            add(_txt_minus_one(source, k))
            add(_txt_plus_one(source, k))
        for k in range(2):
            add(_txt_for_else(source, k))
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules (unparse-based; kept as fallbacks)
# ---------------------------------------------------------------------------

def _rule_candidates(source):
    """Targeted candidate patches for this assignment, most specific first."""
    out, seen = [], set()

    def emit(tree):
        try:
            ast.fix_missing_locations(tree)
            s = ast.unparse(tree)
        except Exception:
            return
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    try:
        probe = ast.parse(source)
    except Exception:
        return out
    fn0 = _find_func(probe)
    if fn0 is None or len(fn0.args.args) < 2:
        return out
    xname = fn0.args.args[0].arg
    sname = fn0.args.args[1].arg

    def fresh():
        t = ast.parse(source)
        return t, _find_func(t)

    # R4: wrong last-element boundary, e.g.
    #     elif x >= seq[-1]: return len(seq) - 1
    # -> elif x >  seq[-1]: return len(seq)
    n_b = len(_boundary_ifs(fn0, xname, sname))
    for k in range(n_b):
        for mode in ("both", "op", "ret"):
            try:
                t, f = fresh()
                node = _boundary_ifs(f, xname, sname)[k]
                if mode in ("both", "op"):
                    old = node.test.ops[0]
                    node.test.ops[0] = ast.Gt() if isinstance(old, ast.GtE) else ast.Lt()
                if mode in ("both", "ret"):
                    for stmt in node.body:
                        for r in ast.walk(stmt):
                            if isinstance(r, ast.Return):
                                r.value = _len_call(sname)
                emit(t)
            except Exception:
                pass

    # R5: `return len(seq) - 1`  ->  `return len(seq)`  (anywhere)
    n_l = len(_lenm1_returns(fn0, sname))
    for k in range(n_l):
        try:
            t, f = fresh()
            _lenm1_returns(f, sname)[k].value = _len_call(sname)
            emit(t)
        except Exception:
            pass

    # R2: wrong trailing return (e.g. `return i + 1`, `return i`,
    #     bare `return`)  ->  `return len(seq)`
    try:
        t, f = fresh()
        last = f.body[-1]
        if isinstance(last, ast.Return) and (
                last.value is None or not _is_len_call(last.value, sname)):
            last.value = _len_call(sname)
            emit(t)
    except Exception:
        pass

    # R1: function can fall off the end -> append `return len(seq)`
    try:
        t, f = fresh()
        if not isinstance(f.body[-1], ast.Return):
            f.body.append(ast.Return(value=_len_call(sname)))
            emit(t)
    except Exception:
        pass

    # R10: off-by-one on returned loop indices: `return j` <-> `return j + 1`
    n_r = len(_name_returns(fn0))
    for k in range(n_r):
        try:
            t, f = fresh()
            r = _name_returns(f)[k]
            r.value = ast.BinOp(left=r.value, op=ast.Add(),
                                right=ast.Constant(value=1))
            emit(t)
        except Exception:
            pass
    n_p = len(_nameplus1_returns(fn0))
    for k in range(n_p):
        try:
            t, f = fresh()
            r = _nameplus1_returns(f)[k]
            r.value = r.value.left
            emit(t)
        except Exception:
            pass

    # R9: loop with break but no else -> add `else: return len(seq)`
    n_bl = len(_break_loops(fn0))
    for k in range(n_bl):
        try:
            t, f = fresh()
            _break_loops(f)[k].orelse = [ast.Return(value=_len_call(sname))]
            emit(t)
        except Exception:
            pass

    # R3: missing empty-sequence handling -> insert `if not seq: return 0`
    try:
        t, f = fresh()
        f.body.insert(0, _guard(sname))
        emit(t)
    except Exception:
        pass

    # R3 + R1/R2 combo: guard AND fix/append the trailing return
    try:
        t, f = fresh()
        f.body.insert(0, _guard(sname))
        last = f.body[-1]
        if isinstance(last, ast.Return):
            if last.value is None or not _is_len_call(last.value, sname):
                last.value = _len_call(sname)
        else:
            f.body.append(ast.Return(value=_len_call(sname)))
        emit(t)
    except Exception:
        pass

    return out


def _with_guard(src):
    """Insert `if not seq: return 0` at the top of `search` in src."""
    try:
        t = ast.parse(src)
        f = _find_func(t)
        if f is None or len(f.args.args) < 2:
            return None
        f.body.insert(0, _guard(f.args.args[1].arg))
        ast.fix_missing_locations(t)
        return ast.unparse(t)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Search driver
# ---------------------------------------------------------------------------

def _safe_iter(gen):
    """Yield from gen, swallowing any exception it may raise."""
    try:
        it = iter(gen)
    except Exception:
        return
    while True:
        try:
            item = next(it)
        except StopIteration:
            return
        except Exception:
            return
        yield item


def _stage(cands, source, max_checks):
    try:
        return first_passing(_safe_iter(cands), ENTRY, TESTS, source,
                             max_rps=MAX_RPS, max_checks=max_checks)
    except Exception:
        return None


def _repair(source):
    t0 = time.time()
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None  # syntax errors are out of scope

    # Already correct? Validate the untouched submission (rps == 0).
    ok = _stage(iter([source]), source, max_checks=4)
    if ok is not None:
        return ok

    # Dispatch on observed behaviour: if the module cannot even be executed,
    # only a small generic search is plausibly useful.
    try:
        res = failing_tests(source, ENTRY, TESTS)
        if not getattr(res, "compiled", True):
            return _stage(candidates_generic(source, max_edits=1, budget=800),
                          source, max_checks=300)
    except Exception:
        pass

    # Byte-minimal text rules first (untouched lines stay byte-identical,
    # so their rps is tiny), then the unparse-based rules as fallback.
    text_rules = _text_candidates(source)
    tset = set(text_rules)
    rules = text_rules + [r for r in _rule_candidates(source) if r not in tset]
    ruleset = set(rules)

    # Stage A: targeted rules first, then every single generic edit.
    cand = _stage(chain(iter(rules),
                        candidates_generic(source, max_edits=1, budget=2000)),
                  source, max_checks=800)
    if cand is not None:
        return cand

    # Stage B: rule outputs combined with an empty-seq guard and with one
    # extra generic edit on top (covers two-fault submissions).
    if time.time() - t0 < _TIME_BUDGET - 3.0:
        gens = []
        extra = []
        for r in rules[:12]:
            g = _txt_insert_guard(r) or _with_guard(r)
            if g and g not in ruleset and g not in extra:
                extra.append(g)
        if extra:
            gens.append(iter(extra))
        for r in rules[:12]:
            gens.append(candidates_generic(r, max_edits=1, budget=300))
        if gens:
            cand = _stage(chain(*gens), source, max_checks=700)
            if cand is not None:
                return cand

    # Stage C: broad generic two-edit search.
    if time.time() - t0 < _TIME_BUDGET - 2.0:
        cand = _stage(candidates_generic(source, max_edits=2, budget=4000),
                      source, max_checks=800)
        if cand is not None:
            return cand

    return None


def repair(source: str):
    """Repair a buggy `search` submission; return fixed source or None."""
    try:
        return _repair(source)
    except Exception:
        return None
```
