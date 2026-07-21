You previously wrote the following per-assignment repair module for the assignment "top_k":

```python
"""Local, LLM-free automatic repair for the `top_k` assignment.

Strategy:
  1. Reject syntactically invalid submissions (return None).
  2. Inspect the failing-test pattern (failing_tests) to prioritize rule
     families: "direction" failures (ascending instead of descending, or
     smallest-instead-of-largest selection) vs. "count" failures (wrong
     number of elements, i.e. off-by-one boundaries).
  3. Generate candidates from problem-specific textual/AST rewrite rules
     (nsmallest<->nlargest, reverse kwarg flips/insertion, min<->max,
     append<->insert(0, ...), slice fixes, reversing the returned list),
     then from the generic single-edit search, then rule pairs, then
     rule+generic combinations, then the generic two-edit search.
  4. Every candidate is validated by first_passing, which enforces the
     full visible test suite and the rps <= 0.35 patch-size cap, so the
     result is always a small edit of the student's own code.
"""

import ast
import re
from itertools import islice

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401  (patch-size metric; enforced via first_passing)

ENTRY = "top_k"

TESTS = [
    {"args": [[5, 5, 1], 2], "expected": [5, 5]},
    {"args": [[3, 1, 2], 2], "expected": [3, 2]},
    {"args": [[1, 2, 3, 4, 5], 3], "expected": [5, 4, 3]},
    {"args": [[], 0], "expected": []},
    {"args": [[], 3], "expected": []},
    {"args": [[7], 1], "expected": [7]},
    {"args": [[4, 2], 0], "expected": []},
    {"args": [[1, 2], 5], "expected": [2, 1]},
    {"args": [[-1, -5, -3], 2], "expected": [-1, -3]},
    {"args": [[10, 10, 10], 2], "expected": [10, 10]},
    {"args": [[0, -1, 1], 3], "expected": [1, 0, -1]},
    {"args": [[2, 8, 6, 4, 9, 1], 4], "expected": [9, 8, 6, 4]},
    {"args": [[5, 3, 5, 3, 5], 3], "expected": [5, 5, 5]},
    {"args": [[100], 0], "expected": []},
]


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules
# ---------------------------------------------------------------------------

# Direction-related rules: student computed smallest instead of largest, or
# ascending instead of descending order.
_DIRECTION_RULES = [
    (r"\bnsmallest\b", "nlargest"),
    (r"\bnlargest\b", "nsmallest"),
    (r"\breverse\s*=\s*False\b", "reverse=True"),
    (r"\breverse\s*=\s*True\b", "reverse=False"),
    (r"\bmin\b", "max"),
    (r"\bmax\b", "min"),
    (r"\.sort\s*\(\s*\)", ".sort(reverse=True)"),
    (r"\.append\(", ".insert(0, "),
    (r"\.insert\(\s*0\s*,\s*", ".append("),
    (r"(?m)^(\s*)return\s+([^\n#]+?)\s*$", r"\1return (\2)[::-1]"),
]

# Boundary / slice rules: wrong slice side or sign.
_SLICE_RULES = [
    (r"\[\s*k\s*:\s*\]", "[:k]"),
    (r"\[\s*:\s*k\s*\]", "[k:]"),
    (r"\[\s*-\s*k\s*:\s*\]", "[:k]"),
    (r"\[\s*:\s*-\s*k\s*\]", "[-k:]"),
]


def _regex_variants(src, pattern, repl):
    """Apply a regex rule at each individual site, plus at all sites."""
    out = []
    try:
        matches = list(re.finditer(pattern, src))
    except Exception:
        return out
    for m in matches:
        try:
            rep = m.expand(repl)
        except Exception:
            continue
        cand = src[: m.start()] + rep + src[m.end() :]
        if cand != src:
            out.append(cand)
    if len(matches) > 1:
        try:
            cand = re.sub(pattern, repl, src)
            if cand != src:
                out.append(cand)
        except Exception:
            pass
    return out


def _add_reverse_kwarg(src):
    """Insert reverse=True into sorted(...) / .sort(...) calls lacking it."""
    out = []
    for pat in (r"\bsorted\s*\(", r"\.sort\s*\("):
        for m in re.finditer(pat, src):
            i = m.end()
            depth = 1
            j = i
            while j < len(src) and depth:
                if src[j] == "(":
                    depth += 1
                elif src[j] == ")":
                    depth -= 1
                j += 1
            if depth:
                continue
            args = src[i : j - 1]
            if "reverse" in args:
                continue
            insert = ", reverse=True" if args.strip() else "reverse=True"
            out.append(src[: j - 1] + insert + src[j - 1 :])
    return out


def _raw_targeted(src, direction_first=True):
    cands = []
    groups = [_DIRECTION_RULES, _SLICE_RULES] if direction_first else [_SLICE_RULES, _DIRECTION_RULES]
    if direction_first:
        cands.extend(_add_reverse_kwarg(src))
    for group in groups:
        for pat, repl in group:
            cands.extend(_regex_variants(src, pat, repl))
    if not direction_first:
        cands.extend(_add_reverse_kwarg(src))
    return cands


def _targeted(src, direction_first=True):
    """Compile-filtered, deduplicated targeted candidates."""
    out = []
    seen = {src}
    for cand in _raw_targeted(src, direction_first):
        if cand in seen:
            continue
        seen.add(cand)
        try:
            compile(cand, "<candidate>", "exec")
        except Exception:
            continue
        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# Failure-pattern dispatch
# ---------------------------------------------------------------------------

def _failure_flags(source):
    """Classify observed failures: 'direction' vs 'count' misconceptions."""
    flags = set()
    try:
        res = failing_tests(source, ENTRY, TESTS)
    except Exception:
        return flags
    try:
        if not getattr(res, "compiled", False):
            return flags
        failures = getattr(res, "failures", None) or []
        for f in failures:
            try:
                exp = f.get("expected")
                got = f.get("got")
            except Exception:
                continue
            if not isinstance(got, list) or not isinstance(exp, list):
                continue
            if exp and (got == list(reversed(exp)) or got == sorted(exp)):
                flags.add("direction")
            if exp and got and sorted(got) != sorted(exp) and len(got) == len(exp):
                # right count, wrong elements -> picked smallest instead of largest
                flags.add("direction")
            if len(got) != len(exp):
                flags.add("count")
    except Exception:
        pass
    return flags


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def repair(source):
    try:
        if not isinstance(source, str) or not source.strip():
            return None
        try:
            ast.parse(source)
        except Exception:
            return None

        flags = _failure_flags(source)
        direction_first = not ("count" in flags and "direction" not in flags)

        targeted = _targeted(source, direction_first)

        def stage_original():
            yield source

        def stage_targeted():
            for t in targeted:
                yield t

        def stage_generic1():
            try:
                for c in candidates_generic(source, max_edits=1, budget=2000):
                    yield c
            except Exception:
                return

        def stage_targeted_pairs():
            local_seen = set(targeted)
            local_seen.add(source)
            count = 0
            for t in targeted[:40]:
                for u in _targeted(t, direction_first):
                    if u in local_seen:
                        continue
                    local_seen.add(u)
                    count += 1
                    yield u
                    if count >= 300:
                        return

        def stage_targeted_plus_generic():
            for t in targeted[:6]:
                try:
                    for c in islice(candidates_generic(t, max_edits=1, budget=600), 250):
                        yield c
                except Exception:
                    continue

        def stage_generic2():
            try:
                for c in candidates_generic(source, max_edits=2, budget=2000):
                    yield c
            except Exception:
                return

        if direction_first:
            stages = [
                stage_original(),
                stage_targeted(),
                stage_generic1(),
                stage_targeted_pairs(),
                stage_targeted_plus_generic(),
                stage_generic2(),
            ]
        else:
            # Count/off-by-one pattern observed: generic edits (off-by-one,
            # comparison swaps) are the most likely fix, try them first.
            stages = [
                stage_original(),
                stage_generic1(),
                stage_targeted(),
                stage_targeted_pairs(),
                stage_targeted_plus_generic(),
                stage_generic2(),
            ]

        stream = chain(*stages)

        seen = set()

        def dedup(it):
            for c in it:
                if not isinstance(c, str) or c in seen:
                    continue
                seen.add(c)
                yield c

        try:
            result = first_passing(
                dedup(stream), ENTRY, TESTS, source, max_rps=0.35, max_checks=2500
            )
        except Exception:
            result = None
        return result if isinstance(result, str) else None
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_04.py: NOT REPAIRED — no_patch
- crafted_10.py: NOT REPAIRED — no_patch
- mutant_02.py: NOT REPAIRED — no_patch
- mutant_03.py: NOT REPAIRED — no_patch
- mutant_06.py: NOT REPAIRED — no_patch

For reference, the submissions the module failed on:

### Failed submission crafted_04.py
```python
def top_k(lst, k):
    return sorted(lst, reverse=True)[:k - 1]

```

### Failed submission crafted_10.py
```python
import heapq

def top_k(lst, k):
    return heapq.nsmallest(k, lst)

```

### Failed submission mutant_02.py
```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) <= k:
        m = temp[0]
        for v in temp:
            if v > m:
                m = v
        temp.remove(m)
        result.append(m)
    return result

```

### Failed submission mutant_03.py
```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) <= k:
        m = temp[-1]
        for v in temp:
            if v > m:
                m = v
        temp.remove(m)
        result.append(m)
    return result

```

### Failed submission mutant_06.py
```python
def top_k(lst, k):
    return sorted(lst, reverse=False)[:k]

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
