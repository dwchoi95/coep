"""Local, LLM-free automatic repair for the `unique_in_order` assignment (round 2).

Root-cause analysis of the round-1 failures: EVERY sample came back
no_patch, including one-token mutants (``i != 0`` -> ``i == 0``,
``result[-2]`` -> ``result[-1]``, ``i == 1`` -> ``i == 0``) that any
1-edit mutation search must find, and crafted_09, for which the
seed-init rule (`result = []` -> `result = lst[:1]`) demonstrably
produces a correct, tiny candidate by hand-trace.  When even those fail,
the failure is systemic, not per-rule: the helper-library calls were
raising (keyword arguments such as ``max_checks``/``budget`` not
matching the real `first_passing`/`candidates_generic` signatures) and
the broad ``try/except`` + ``_safe`` wrappers silently swallowed the
errors, so no candidate was ever actually validated.

Round-2 fixes, keeping everything that was right about round 1:
  * All repairlib calls go through adaptive wrappers that inspect the
    real signatures and progressively drop unsupported keyword
    arguments, so a signature mismatch can no longer silently disable
    the whole search.
  * A self-contained AST mutation engine (comparison-operator flips,
    integer-constant +/-1, Add<->Sub, And<->Or, test negation) generates
    1- and 2-edit candidates independently of `candidates_generic`.
  * Candidates are pre-screened locally by actually running the visible
    tests (with a trace-based step limit to kill runaway loops), so only
    genuinely passing programs reach `first_passing`, ordered by textual
    similarity to the student's code (smallest patch first).
  * A canonical-rewrite fallback (function name and parameter preserved)
    handles approach-level failures such as ``list(set(lst))``.
`first_passing` remains the final authority: every returned patch is
validated by it against the full visible suite and the rps <= 0.35
patch-size cap relative to the ORIGINAL student source.
"""

import ast
import copy
import difflib
import inspect
import re
import sys

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain

ENTRY = "unique_in_order"

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1]], "expected": [1]},
    {"args": [[1, 1]], "expected": [1]},
    {"args": [[1, 1, 2, 1]], "expected": [1, 2, 1]},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 1, 1, 1]], "expected": [1]},
    {"args": [["a", "a", "b", "b", "a"]], "expected": ["a", "b", "a"]},
    {"args": [[1, "1", 1]], "expected": [1, "1", 1]},
    {"args": [[2, 2, 2, 3, 3, 1, 1, 2]], "expected": [2, 3, 1, 2]},
    {"args": [["A", "a", "A"]], "expected": ["A", "a", "A"]},
    {"args": [[0, 0, 0]], "expected": [0]},
    {"args": [[5, 4, 4, 5, 5, 4]], "expected": [5, 4, 5, 4]},
    {"args": [["x"]], "expected": ["x"]},
    {"args": [[1, 2, 2, 3, 3, 3, 4]], "expected": [1, 2, 3, 4]},
]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _parses(src):
    try:
        ast.parse(src)
        return True
    except Exception:
        return False


def _param_name(tree):
    """First parameter of the entry function (fallback: any function, then 'lst')."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY and node.args.args:
            return node.args.args[0].arg
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.args.args:
            return node.args.args[0].arg
    return "lst"


def _dedupe(cands, source=None):
    out, seen = [], set()
    for c in cands:
        if not isinstance(c, str) or c in seen or c == source:
            continue
        seen.add(c)
        out.append(c)
    return out


def _rank(cands, source):
    """Most-similar-to-original first, so the smallest patch wins."""
    try:
        return sorted(
            cands,
            key=lambda c: -difflib.SequenceMatcher(None, source, c).ratio(),
        )
    except Exception:
        return list(cands)


# --------------------------------------------------------------------------
# local (pre-)validation: actually run the visible tests on a candidate
# --------------------------------------------------------------------------

def _limited(thunk, limit=150000):
    """Run thunk() under a trace-event budget so runaway loops cannot hang us."""
    state = {"n": 0}

    def tracer(frame, event, arg):
        state["n"] += 1
        if state["n"] > limit:
            raise RuntimeError("step budget exceeded")
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        return thunk()
    finally:
        sys.settrace(old)


def _passes_locally(src):
    """True iff src defines ENTRY and passes every visible test locally."""
    try:
        code = compile(src, "<candidate>", "exec")
    except Exception:
        return False
    glb = {}
    try:
        _limited(lambda: exec(code, glb))
    except Exception:
        return False
    fn = glb.get(ENTRY)
    if not callable(fn):
        return False
    for t in TESTS:
        try:
            args = copy.deepcopy(t["args"])
            got = _limited(lambda: fn(*args))
        except Exception:
            return False
        if got != t["expected"]:
            return False
    return True


def _locally_good(cands, source):
    out, seen = [], set()
    for c in cands:
        if not isinstance(c, str) or c == source or c in seen:
            continue
        seen.add(c)
        if _passes_locally(c):
            out.append(c)
    return out


# --------------------------------------------------------------------------
# adaptive wrappers around the helper library (the round-1 killer)
# --------------------------------------------------------------------------

def _validate(cands, original):
    """Official validation via first_passing, robust to signature drift.

    Tries the signature discovered by introspection first, then a ladder of
    progressively smaller keyword sets.  Candidates are materialised so each
    retry sees the full list.  Returns the accepted patch or None.
    """
    cands = [c for c in cands if isinstance(c, str) and c.strip()]
    if not cands:
        return None
    kwlist = []
    try:
        params = inspect.signature(first_passing).parameters
        varkw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        kw = {}
        if varkw or "max_rps" in params:
            kw["max_rps"] = 0.35
        if varkw or "max_checks" in params:
            kw["max_checks"] = 2000
        kwlist.append(kw)
    except Exception:
        pass
    for kw in ({"max_rps": 0.35, "max_checks": 2000}, {"max_rps": 0.35}, {}):
        if kw not in kwlist:
            kwlist.append(kw)
    for kw in kwlist:
        try:
            res = first_passing(iter(cands), ENTRY, TESTS, original, **kw)
        except TypeError:
            continue  # signature mismatch -> try the next keyword set
        except Exception:
            continue
        if isinstance(res, str):
            return res
        return None  # the call itself worked; nothing passed
    return None


def _generic_candidates(source, max_edits, budget):
    """Materialise candidates_generic output, robust to signature drift."""
    kwlist = []
    try:
        params = inspect.signature(candidates_generic).parameters
        varkw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        kw = {}
        if varkw or "max_edits" in params:
            kw["max_edits"] = max_edits
        if varkw or "budget" in params:
            kw["budget"] = budget
        kwlist.append(kw)
    except Exception:
        pass
    for kw in ({"max_edits": max_edits, "budget": budget},
               {"max_edits": max_edits}, {}):
        if kw not in kwlist:
            kwlist.append(kw)
    for kw in kwlist:
        try:
            gen = candidates_generic(source, **kw)
        except TypeError:
            continue
        except Exception:
            continue
        out = []
        try:
            for c in gen:
                if isinstance(c, str):
                    out.append(c)
                if len(out) >= budget:
                    break
        except Exception:
            pass
        if out:
            return out
    return []


# --------------------------------------------------------------------------
# self-contained AST mutation engine (independent of candidates_generic)
# --------------------------------------------------------------------------

_CMP_ALTS = {
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
    ast.Lt: (ast.Le, ast.Gt),
    ast.Le: (ast.Lt, ast.Ge),
    ast.Gt: (ast.Ge, ast.Lt),
    ast.Ge: (ast.Gt, ast.Le),
    ast.Is: (ast.Eq,),
    ast.IsNot: (ast.NotEq,),
}


def _site_variants(node):
    """All single mutations applicable at this node, in a fixed order."""
    vs = []
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        for alt in _CMP_ALTS.get(type(node.ops[0]), ()):
            vs.append(("cmp", alt))
    if (isinstance(node, ast.Constant) and isinstance(node.value, int)
            and not isinstance(node.value, bool)):
        vs.append(("const", node.value + 1))
        vs.append(("const", node.value - 1))
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Add):
            vs.append(("binop", ast.Sub))
        elif isinstance(node.op, ast.Sub):
            vs.append(("binop", ast.Add))
    if isinstance(node, ast.BoolOp):
        vs.append(("boolop", ast.Or if isinstance(node.op, ast.And) else ast.And))
    if isinstance(node, (ast.If, ast.While, ast.IfExp)):
        vs.append(("negate", None))
    return vs


def _apply_variant(node, kind, payload):
    if kind == "cmp":
        node.ops[0] = payload()
    elif kind == "const":
        node.value = payload
    elif kind in ("binop", "boolop"):
        node.op = payload()
    elif kind == "negate":
        node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)


def _one_edit_mutants(source, cap=400):
    """Every single-site mutation of source (ast.walk order is deterministic)."""
    outs = []
    try:
        total = sum(len(_site_variants(n)) for n in ast.walk(ast.parse(source)))
    except Exception:
        return outs
    for k in range(min(total, cap)):
        try:
            tree = ast.parse(source)
            i = 0
            for node in ast.walk(tree):
                vs = _site_variants(node)
                if k < i + len(vs):
                    kind, payload = vs[k - i]
                    _apply_variant(node, kind, payload)
                    break
                i += len(vs)
            ast.fix_missing_locations(tree)
            outs.append(ast.unparse(tree))
        except Exception:
            continue
    return outs


def _two_edit_mutants(source, first_cap=80, limit=3000):
    outs = []
    try:
        for m1 in _one_edit_mutants(source)[:first_cap]:
            for m2 in _one_edit_mutants(m1):
                outs.append(m2)
                if len(outs) >= limit:
                    return outs
    except Exception:
        pass
    return outs


# --------------------------------------------------------------------------
# problem-specific rewrite rules (kept from round 1)
# --------------------------------------------------------------------------

def _rename_candidates(source):
    """If the (single) function has the wrong name, rename it to the entry name."""
    outs = []
    try:
        tree = ast.parse(source)
    except Exception:
        return outs
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if fns and not any(f.name == ENTRY for f in fns):
        fns[0].name = ENTRY
        try:
            ast.fix_missing_locations(tree)
            outs.append(ast.unparse(tree))
        except Exception:
            pass
    return outs


def _seed_init_candidates(source, param):
    """`result = []` -> `result = lst[:1]`.

    Fixes the classic bug where the loop starts at index 1 (or otherwise
    skips the first element) so the first element is never appended.
    """
    outs = []
    pat = re.compile(r"(?<![=!<>])(=\s*)\[\]")
    for m in pat.finditer(source):
        outs.append(source[: m.start()] + m.group(1) + param + "[:1]" + source[m.end():])
    return outs


def _idx_patterns(cond):
    """Detect boundary-sensitive index accesses inside a condition."""
    found = []
    for sub in ast.walk(cond):
        if not isinstance(sub, ast.Subscript):
            continue
        s = sub.slice
        if (
            isinstance(s, ast.BinOp)
            and isinstance(s.right, ast.Constant)
            and s.right.value == 1
            and isinstance(s.left, ast.Name)
        ):
            if isinstance(s.op, ast.Sub):
                found.append((s.left.id, "prev"))
            elif isinstance(s.op, ast.Add):
                found.append((s.left.id, "next"))
        elif (
            isinstance(s, ast.UnaryOp)
            and isinstance(s.op, ast.USub)
            and isinstance(s.operand, ast.Constant)
            and isinstance(sub.value, ast.Name)
        ):
            found.append((sub.value.id, "neg"))
        elif (
            isinstance(s, ast.Constant)
            and isinstance(s.value, int)
            and s.value < 0
            and isinstance(sub.value, ast.Name)
        ):
            found.append((sub.value.id, "neg"))
    return found


def _cond_sites(tree):
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.IfExp)):
            sites.append((node, "test", -1))
        elif isinstance(node, ast.comprehension):
            for j in range(len(node.ifs)):
                sites.append((node, "ifs", j))
    return sites


def _get_cond(site):
    node, attr, j = site
    return node.test if attr == "test" else node.ifs[j]


def _set_cond(site, new):
    node, attr, j = site
    if attr == "test":
        node.test = new
    else:
        node.ifs[j] = new


def _guard_candidates(source):
    """Wrap bare conditions with the missing boundary guard."""
    outs = []
    try:
        base = ast.parse(source)
    except Exception:
        return outs
    param = _param_name(base)
    n_sites = len(_cond_sites(base))
    for k in range(n_sites):
        try:
            probe = ast.parse(source)
            cond = _get_cond(_cond_sites(probe)[k])
        except Exception:
            continue
        if isinstance(cond, ast.BoolOp):
            continue  # compound conditions are handled by the mutation engine
        guards = []
        for nm, kind in _idx_patterns(cond):
            if kind == "prev":
                guards.append(("%s == 0" % nm, "or"))
                guards.append(("%s != 0" % nm, "and"))
            elif kind == "next":
                guards.append(("%s == len(%s) - 1" % (nm, param), "or"))
                guards.append(("%s != len(%s) - 1" % (nm, param), "and"))
            else:  # neg
                guards.append(("not %s" % nm, "or"))
                guards.append(("%s" % nm, "and"))
        seen = set()
        for gsrc, mode in guards:
            if (gsrc, mode) in seen:
                continue
            seen.add((gsrc, mode))
            try:
                t2 = ast.parse(source)
                site2 = _cond_sites(t2)[k]
                c2 = _get_cond(site2)
                gexpr = ast.parse(gsrc, mode="eval").body
                new = ast.BoolOp(
                    op=ast.Or() if mode == "or" else ast.And(),
                    values=[gexpr, c2],
                )
                _set_cond(site2, new)
                ast.fix_missing_locations(t2)
                outs.append(ast.unparse(t2))
            except Exception:
                continue
    return outs


def _dedent_return_candidates(source):
    """Move a `return` that sits at the end of a loop body out of the loop."""
    outs = []
    try:
        base = ast.parse(source)
    except Exception:
        return outs

    def loops_with_trailing_return(tree):
        return [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.For, ast.While))
            and n.body
            and isinstance(n.body[-1], ast.Return)
        ]

    n = len(loops_with_trailing_return(base))
    for k in range(n):
        try:
            t2 = ast.parse(source)
            loop = loops_with_trailing_return(t2)[k]
            ret = loop.body.pop()
            if not loop.body:
                loop.body.append(ast.Pass())
            placed = False
            for node in ast.walk(t2):
                for field in ("body", "orelse", "finalbody"):
                    seq = getattr(node, field, None)
                    if isinstance(seq, list) and loop in seq:
                        seq.insert(seq.index(loop) + 1, ret)
                        placed = True
                        break
                if placed:
                    break
            if placed:
                ast.fix_missing_locations(t2)
                outs.append(ast.unparse(t2))
        except Exception:
            continue
    return outs


def _sentinel_candidates(source):
    """`prev = 0` / `prev = ''` / etc. -> `prev = object()`."""
    outs = []
    try:
        base = ast.parse(source)
    except Exception:
        return outs

    def const_assigns(tree):
        return [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
        ]

    n = len(const_assigns(base))
    for k in range(n):
        try:
            t2 = ast.parse(source)
            node = const_assigns(t2)[k]
            node.value = ast.parse("object()", mode="eval").body
            ast.fix_missing_locations(t2)
            outs.append(ast.unparse(t2))
        except Exception:
            continue
    return outs


class _StripCall(ast.NodeTransformer):
    """Replace the k-th sorted(X)/set(X)/reversed(X) call with plain X."""

    def __init__(self, k):
        self.k = k
        self.count = -1

    def visit_Call(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in ("sorted", "set", "reversed")
            and len(node.args) == 1
            and not node.keywords
        ):
            self.count += 1
            if self.count == self.k:
                return node.args[0]
        return node


def _strip_call_candidates(source):
    outs = []
    if not re.search(r"\b(sorted|set|reversed)\s*\(", source):
        return outs
    for k in range(6):
        try:
            t2 = ast.parse(source)
            tr = _StripCall(k)
            t2 = tr.visit(t2)
            if tr.count < k:
                break
            ast.fix_missing_locations(t2)
            outs.append(ast.unparse(t2))
        except Exception:
            break
    return outs


def _is_to_eq_candidates(source):
    """Replace identity comparisons with value comparisons."""
    outs = []
    try:
        if re.search(r"\bis\s+not\b", source):
            outs.append(re.sub(r"\bis\s+not\b", "!=", source))
        if re.search(r"\bis\b", source):
            outs.append(
                re.sub(r"\bis\b(?!\s+not\b)", "==",
                       re.sub(r"\bis\s+not\b", "!=", source))
            )
    except Exception:
        pass
    return outs


def _insert_copy_candidates(source):
    """Insert `lst = list(lst)` at the top of the function (aliasing bugs)."""
    outs = []
    try:
        tree = ast.parse(source)
    except Exception:
        return outs
    param = _param_name(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            try:
                stmt = ast.parse("%s = list(%s)" % (param, param)).body[0]
                node.body.insert(0, stmt)
                ast.fix_missing_locations(tree)
                outs.append(ast.unparse(tree))
            except Exception:
                pass
            break
    return outs


def _specific_candidates(source):
    """All problem-specific rewrites, deduplicated, in priority order."""
    try:
        tree = ast.parse(source)
        param = _param_name(tree)
    except Exception:
        return []
    cands = []
    for rule in (
        lambda s: _rename_candidates(s),
        lambda s: _seed_init_candidates(s, param),
        lambda s: _guard_candidates(s),
        lambda s: _dedent_return_candidates(s),
        lambda s: _sentinel_candidates(s),
        lambda s: _strip_call_candidates(s),
        lambda s: _is_to_eq_candidates(s),
        lambda s: _insert_copy_candidates(s),
    ):
        try:
            cands.extend(rule(source))
        except Exception:
            continue
    seen = set()
    out = []
    for c in cands:
        if not isinstance(c, str) or c == source or c in seen:
            continue
        if not _parses(c):
            continue
        seen.add(c)
        out.append(c)
    return out


def _canonical_candidates(source):
    """Last-resort full-body rewrites preserving the name and parameter.

    Needed when the approach itself is wrong (e.g. `list(set(lst))`, which
    destroys order and non-consecutive duplicates); the rps cap enforced by
    `first_passing` still decides whether any of these is acceptable.
    """
    try:
        p = _param_name(ast.parse(source))
    except Exception:
        p = "lst"
    tpls = [
        "def {E}({p}):\n"
        "    return [x for i, x in enumerate({p}) if not i or x != {p}[i - 1]]\n",
        "def {E}({p}):\n"
        "    return [x for i, x in enumerate({p}) if i == 0 or x != {p}[i - 1]]\n",
        "def {E}({p}):\n"
        "    return list(x for i, x in enumerate({p}) if not i or x != {p}[i - 1])\n",
        "def {E}({p}):\n"
        "    result = []\n"
        "    for x in {p}:\n"
        "        if not result or result[-1] != x:\n"
        "            result.append(x)\n"
        "    return result\n",
    ]
    return [t.format(E=ENTRY, p=p) for t in tpls]


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def repair(source):
    try:
        if not isinstance(source, str) or not _parses(source):
            return None

        # Stage 0: maybe the submission already passes (rps == 0).
        ok = _validate([source], source)
        if ok is not None:
            return ok

        # (failing pattern available for inspection; validation decides.)
        try:
            failing_tests(source, ENTRY, TESTS)
        except Exception:
            pass

        specific = _specific_candidates(source)

        # Stage 1: specific rules + own 1-edit mutants, locally screened.
        batch = _locally_good(specific + _one_edit_mutants(source), source)
        fixed = _validate(_rank(batch, source), source)
        if fixed is not None:
            return fixed

        # Stage 2: deeper search — own 2-edit mutants, specific rewrites
        # combined with one mutation, and the library's generic search.
        deep = _two_edit_mutants(source)
        for cand in specific[:6]:
            deep.extend(_one_edit_mutants(cand))
        deep.extend(_generic_candidates(source, 1, 800))
        deep.extend(_generic_candidates(source, 2, 1200))
        batch = _locally_good(deep, source)
        fixed = _validate(_rank(batch, source), source)
        if fixed is not None:
            return fixed

        # Stage 3: canonical rewrites (approach-level bugs); rps cap decides.
        batch = _locally_good(_canonical_candidates(source), source)
        fixed = _validate(_rank(batch, source), source)
        if fixed is not None:
            return fixed

        # Stage 4: safety net — in case the local runner misjudged the
        # environment, let first_passing judge unscreened candidates.
        tail = _dedupe(
            specific
            + _generic_candidates(source, 1, 300)
            + _canonical_candidates(source),
            source,
        )[:300]
        return _validate(_rank(tail, source), source)
    except Exception:
        return None
