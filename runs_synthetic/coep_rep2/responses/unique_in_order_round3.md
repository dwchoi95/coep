```python
"""Local, LLM-free automatic repair for the `unique_in_order` assignment (round 3).

Root cause of the round-2 wipeout: every sample failed with
``AttributeError: module 'ast' has no attribute 'Le'``.  The module built a
comparison-operator table (``_CMP_ALTS``) at import time from ``ast.Le``,
``ast.Ge`` etc., and in the evaluation environment the ``ast`` module does
not expose those node classes, so the module crashed *on import* -- before
`repair` could even run.  Nothing was ever generated or validated; the
elaborate AST machinery, adaptive signature probing and keyword ladders were
all dead weight sitting on top of a hard import-time crash.

Round-3 fix: remove the dependency entirely and simplify aggressively.
The whole pipeline is now small, self-contained and text-based:

  1. parse-check the submission (via ``compile``, no ``ast`` needed);
  2. targeted rules for this assignment (seed the accumulator with the
     first element, replace order-destroying ``list(set(x))``, strip
     ``sorted``/``reversed``, ``is``->``==``, rename a mis-named function);
  3. a generic 1- and 2-edit textual mutation search (comparison-operator
     flips, integer-constant +/-1, ``and``<->``or``, ``+``<->``-``,
     ``not`` removal, ``[0]``<->``[-1]``);
  4. candidates are pre-screened by actually running the visible tests
     locally (with a step budget so runaway loops cannot hang us), ranked
     smallest-patch-first, and finally validated by
     ``first_passing(candidates, entry, tests, original)`` called with
     positional arguments only -- `first_passing` remains the sole
     authority on correctness and the rps <= 0.35 patch-size cap.

`repair` never raises: a single top-level try/except returns None on any
internal failure.
"""

import copy
import difflib
import re
import sys

from coep.repairlib import first_passing

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
# small helpers (no `ast` anywhere)
# --------------------------------------------------------------------------

def _compiles(src):
    try:
        compile(src, "<candidate>", "exec")
        return True
    except Exception:
        return False


def _param(source):
    """Name of the entry function's first parameter (fallback 'lst')."""
    m = re.search(r"\bdef\s+%s\s*\(\s*(\w+)" % re.escape(ENTRY), source)
    if m:
        return m.group(1)
    m = re.search(r"\bdef\s+\w+\s*\(\s*(\w+)", source)
    return m.group(1) if m else "lst"


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
# local pre-screening: actually run the visible tests on a candidate
# --------------------------------------------------------------------------

def _limited(thunk, limit=200000):
    """Run thunk() under a trace-event budget so runaway loops cannot hang."""
    state = [0]

    def tracer(frame, event, arg):
        state[0] += 1
        if state[0] > limit:
            raise RuntimeError("step budget exceeded")
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        return thunk()
    finally:
        sys.settrace(old)


def _passes(src):
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
            got = _limited(lambda a=args: fn(*a))
        except Exception:
            return False
        if got != t["expected"]:
            return False
    return True


# --------------------------------------------------------------------------
# official validation: first_passing, positional arguments only
# --------------------------------------------------------------------------

def _validate(cands, original):
    cands = [c for c in cands if isinstance(c, str) and c.strip()]
    if not cands:
        return None
    try:
        res = first_passing(cands, ENTRY, TESTS, original)
    except Exception:
        return None
    return res if isinstance(res, str) else None


# --------------------------------------------------------------------------
# generic 1- and 2-edit textual mutation search
# --------------------------------------------------------------------------

_CMP_ALTS = {
    "==": ("!=",),
    "!=": ("==",),
    "<": ("<=", ">"),
    "<=": ("<", ">="),
    ">": (">=", "<"),
    ">=": (">", "<="),
}


def _edits(source):
    """All single (start, end, replacement) edits, in a deterministic order."""
    edits = []
    # comparison-operator flips
    for m in re.finditer(r"==|!=|<=|>=|(?<!<)<(?![=<])|(?<![->])>(?![=>])",
                         source):
        for alt in _CMP_ALTS.get(m.group(), ()):
            edits.append((m.start(), m.end(), alt))
    # integer constants +/- 1
    for m in re.finditer(r"(?<![\w.])\d+(?![\w.])", source):
        try:
            n = int(m.group())
        except Exception:
            continue
        for v in (n + 1, n - 1):
            edits.append((m.start(), m.end(), str(v)))
    # boolean-operator swaps
    for m in re.finditer(r"\band\b", source):
        edits.append((m.start(), m.end(), "or"))
    for m in re.finditer(r"\bor\b", source):
        edits.append((m.start(), m.end(), "and"))
    # arithmetic sign flips
    for m in re.finditer(r"(?<![+\-*/%=<>!])\+(?![+=])", source):
        edits.append((m.start(), m.end(), "-"))
    for m in re.finditer(r"(?<![+\-*/%=<>!])-(?![-=>])", source):
        edits.append((m.start(), m.end(), "+"))
    # drop a negation
    for m in re.finditer(r"\bnot\s+", source):
        edits.append((m.start(), m.end(), ""))
    # first/last index confusions
    for m in re.finditer(r"\[0\]", source):
        edits.append((m.start(), m.end(), "[-1]"))
    for m in re.finditer(r"\[-1\]", source):
        edits.append((m.start(), m.end(), "[0]"))
    return edits


def _one_edit(source):
    outs = []
    for s, e, r in _edits(source):
        outs.append(source[:s] + r + source[e:])
    return outs


def _two_edit(source, first_cap=60, limit=1500):
    outs = []
    for m1 in _one_edit(source)[:first_cap]:
        for m2 in _one_edit(m1):
            outs.append(m2)
            if len(outs) >= limit:
                return outs
    return outs


# --------------------------------------------------------------------------
# targeted, assignment-specific rewrite rules
# --------------------------------------------------------------------------

def _targeted(source):
    p = _param(source)
    outs = []
    # mis-named function: rename the first def to the entry name
    if not re.search(r"\bdef\s+%s\s*\(" % re.escape(ENTRY), source):
        outs.append(
            re.sub(r"\bdef\s+\w+\s*\(", "def %s(" % ENTRY, source, count=1)
        )
    # seed the accumulator with the first element (loop starts at index 1)
    for m in re.finditer(r"(?<![=!<>])=\s*\[\]", source):
        outs.append(source[:m.start()] + "= " + p + "[:1]" + source[m.end():])
    # list(set(x)) / set(x) destroy order and non-consecutive duplicates
    dedupe = ("[{x}[i] for i in range(len({x})) "
              "if i == 0 or {x}[i] != {x}[i - 1]]")
    for pat in (r"\blist\s*\(\s*set\s*\(\s*(\w+)\s*\)\s*\)",
                r"\bset\s*\(\s*(\w+)\s*\)"):
        for m in re.finditer(pat, source):
            repl = dedupe.format(x=m.group(1))
            outs.append(source[:m.start()] + repl + source[m.end():])
    # sorted()/reversed() wrappers change the order: strip them
    for m in re.finditer(r"\b(?:sorted|reversed)\s*\(\s*(\w+)\s*\)", source):
        outs.append(source[:m.start()] + m.group(1) + source[m.end():])
    # identity comparison instead of value comparison
    if re.search(r"\bis\s+not\b", source):
        outs.append(re.sub(r"\bis\s+not\b", "!=", source))
    if re.search(r"\bis\b", source):
        outs.append(
            re.sub(r"\bis\b(?!\s+not\b)", "==",
                   re.sub(r"\bis\s+not\b", "!=", source))
        )
    return outs


def _canonical(source):
    """Last-resort full-body rewrites preserving the name and parameter.

    Only reachable when everything smaller failed; the rps <= 0.35 cap
    enforced by `first_passing` still decides whether any is acceptable.
    """
    p = _param(source)
    tpls = [
        "def {E}({p}):\n"
        "    return [{p}[i] for i in range(len({p}))"
        " if i == 0 or {p}[i] != {p}[i - 1]]\n",
        "def {E}({p}):\n"
        "    return [x for i, x in enumerate({p})"
        " if not i or x != {p}[i - 1]]\n",
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
        if not isinstance(source, str) or not _compiles(source):
            return None

        # Stage 0: the submission may already pass (rps == 0).
        if _passes(source):
            ok = _validate([source], source)
            if ok is not None:
                return ok

        seen = {source}

        def fresh(cands):
            out = []
            for c in cands:
                if isinstance(c, str) and c not in seen and _compiles(c):
                    seen.add(c)
                    out.append(c)
            return out

        targeted = fresh(_targeted(source))

        # Stage 1: targeted rules + 1-edit mutants, locally screened.
        batch = [c for c in targeted + fresh(_one_edit(source)) if _passes(c)]
        ok = _validate(_rank(batch, source), source)
        if ok is not None:
            return ok

        # Stage 2: 2-edit mutants and targeted rewrites + one mutation.
        deep = fresh(_two_edit(source))
        for t in targeted[:8]:
            deep.extend(fresh(_one_edit(t)))
        batch = [c for c in deep if _passes(c)]
        ok = _validate(_rank(batch, source), source)
        if ok is not None:
            return ok

        # Stage 3: canonical rewrites (approach-level bugs); rps cap decides.
        batch = [c for c in fresh(_canonical(source)) if _passes(c)]
        ok = _validate(_rank(batch, source), source)
        if ok is not None:
            return ok

        # Stage 4: safety net -- if the local runner misjudged anything,
        # let first_passing judge the closest unscreened candidates.
        leftovers = _rank([c for c in seen if c != source], source)[:200]
        return _validate(leftovers, source)
    except Exception:
        return None
```
