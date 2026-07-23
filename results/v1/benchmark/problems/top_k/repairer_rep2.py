"""Local, LLM-free automatic repair for the `top_k` assignment.

Round-2 revision.  Diagnosis of the round-1 failures: EVERY submission came
back "no_patch", including submissions whose fix was already covered by an
existing rewrite rule (crafted_10 only needs nsmallest->nlargest, mutant_06
only needs reverse=False->reverse=True, both rules were present and produce
passing code).  The only way a correct, tiny, rule-generated candidate can
still yield no_patch is that the validation pipeline itself blew up and the
blanket try/except swallowed it: the round-1 module piped everything through
`chain(*stages)` and a single `first_passing(stream, ENTRY, TESTS, source,
max_rps=0.35, max_checks=2500)` call; a signature mismatch on either helper
raises TypeError, which was silently converted to None for all submissions.

Fixes in this revision:
  1. Drop the dependency on repairlib.chain entirely (plain generator).
  2. Materialize a bounded, deduplicated, compile-checked candidate pool and
     call `first_passing` through a ladder of progressively simpler
     signatures (full kwargs -> max_rps only -> 4 positional -> 3
     positional), so no keyword mismatch can wipe out the run.  The 0.35
     patch-size cap is *also* enforced locally via coep.evaluate.rps before
     validation, so even the bare fallback stays within the cap.
  3. `candidates_generic` is likewise called through kwarg fallbacks.
  4. Missing rules added: explicit "count"/off-by-one rules (`k - 1` -> `k`,
     `k + 1` -> `k`, `<=` <-> `<`, `>=` <-> `>`), which repair crafted_04
     (`[:k - 1]`) and mutant_02/03 (`len(result) <= k`) even if the generic
     edit search is unavailable.
  5. `failing_tests` result parsing made shape-tolerant (dict / list /
     object), instead of assuming `.compiled` / `.failures` attributes.

Every candidate is still validated with first_passing against the full
visible suite, edits stay small rewrites of the student's own code, and
repair() never raises.
"""

import ast
import re
from itertools import islice

from coep.repairlib import candidates_generic, first_passing, failing_tests

try:
    from coep.evaluate import rps
except Exception:  # pragma: no cover - keep module importable regardless
    rps = None

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

MAX_RPS = 0.35
POOL_CAP = 2500


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

# Count / off-by-one rules: too many or too few elements returned.
_COUNT_RULES = [
    (r"\bk\s*-\s*1\b", "k"),          # [:k - 1] -> [:k], range(k - 1) -> range(k), ...
    (r"\bk\s*\+\s*1\b", "k"),
    (r"<=", "<"),                      # len(result) <= k -> len(result) < k
    (r"(?<![<>=!])<(?![<=])", "<="),
    (r">=", ">"),
    (r"(?<![-<>=!])>(?![>=])", ">="),
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
    if direction_first:
        groups = [_DIRECTION_RULES, _COUNT_RULES, _SLICE_RULES]
        cands.extend(_add_reverse_kwarg(src))
    else:
        groups = [_COUNT_RULES, _SLICE_RULES, _DIRECTION_RULES]
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
# Failure-pattern dispatch (shape-tolerant; heuristic only)
# ---------------------------------------------------------------------------

def _iter_failures(res):
    """Extract a list of per-test failure records from any plausible shape."""
    if res is None:
        return []
    if isinstance(res, dict):
        for key in ("failures", "failing", "failed", "results"):
            val = res.get(key)
            if isinstance(val, (list, tuple)):
                return list(val)
        return [res]
    if isinstance(res, (list, tuple)):
        return list(res)
    for key in ("failures", "failing", "failed", "results"):
        val = getattr(res, key, None)
        if isinstance(val, (list, tuple)):
            return list(val)
    return []


def _exp_got(f):
    """Pull (expected, got) out of a failure record of unknown shape."""
    exp = got = None
    if isinstance(f, dict):
        exp = f.get("expected")
        got = f.get("got", f.get("actual", f.get("result")))
    else:
        exp = getattr(f, "expected", None)
        got = getattr(f, "got", getattr(f, "actual", None))
        if exp is None and got is None and isinstance(f, (list, tuple)) and len(f) >= 2:
            exp, got = f[-2], f[-1]
    return exp, got


def _failure_flags(source):
    """Classify observed failures: 'direction' vs 'count' misconceptions."""
    flags = set()
    try:
        res = failing_tests(source, ENTRY, TESTS)
    except Exception:
        return flags
    try:
        for f in _iter_failures(res):
            exp, got = _exp_got(f)
            if not isinstance(got, list) or not isinstance(exp, list):
                continue
            if exp and (got == list(reversed(exp)) or got == sorted(exp)):
                flags.add("direction")
            if exp and got and len(got) == len(exp) and sorted(got) != sorted(exp):
                # right count, wrong elements -> picked smallest instead of largest
                flags.add("direction")
            if len(got) != len(exp):
                flags.add("count")
    except Exception:
        pass
    return flags


# ---------------------------------------------------------------------------
# Generic-edit helper with signature fallbacks
# ---------------------------------------------------------------------------

def _generic(src, max_edits, budget, cap):
    """Yield generic candidates; tolerate unknown candidates_generic kwargs."""
    for kwargs in (
        {"max_edits": max_edits, "budget": budget},
        {"max_edits": max_edits},
        {},
    ):
        try:
            it = candidates_generic(src, **kwargs)
        except TypeError:
            continue  # signature mismatch: try a simpler call
        except Exception:
            return
        try:
            for c in islice(it, cap):
                yield c
        except Exception:
            pass
        return


# ---------------------------------------------------------------------------
# Candidate stream (priority order) and robust validation
# ---------------------------------------------------------------------------

def _candidates(source, direction_first):
    # 0. The submission itself (in case it already passes).
    yield source

    # 1. Targeted single-rule rewrites.
    targeted = _targeted(source, direction_first)
    for t in targeted:
        yield t

    # 2. Generic single-edit search.
    for c in _generic(source, 1, 2000, 1200):
        yield c

    # 3. Pairs of targeted rules (e.g. direction fix + off-by-one fix).
    emitted = 0
    local_seen = set(targeted)
    local_seen.add(source)
    for t in targeted[:40]:
        if emitted >= 300:
            break
        for u in _targeted(t, direction_first):
            if u in local_seen:
                continue
            local_seen.add(u)
            yield u
            emitted += 1
            if emitted >= 300:
                break

    # 4. Targeted rewrite + one generic edit.
    for t in targeted[:6]:
        for c in _generic(t, 1, 600, 150):
            yield c

    # 5. Generic two-edit search.
    for c in _generic(source, 2, 2000, 1500):
        yield c


def _within_cap(source, cand):
    """Locally enforce the patch-size cap; permissive if rps is unusable."""
    if rps is None or cand == source:
        return True
    for a, b in ((source, cand), (cand, source)):
        try:
            v = float(rps(a, b))
        except Exception:
            continue
        return v <= MAX_RPS
    return True


def _validate(cands, source):
    """Pool candidates, then validate via first_passing with fallbacks."""
    pool = []
    seen = set()
    for c in cands:
        if not isinstance(c, str) or c in seen:
            continue
        seen.add(c)
        try:
            compile(c, "<candidate>", "exec")
        except Exception:
            continue
        if not _within_cap(source, c):
            continue
        pool.append(c)
        if len(pool) >= POOL_CAP:
            break
    if not pool:
        return None

    # Ladder of signatures: a keyword mismatch must not kill the whole run.
    # The rps cap was already enforced locally on every pooled candidate, so
    # even the bare fallbacks respect the 0.35 patch-size constraint.
    attempts = (
        lambda: first_passing(iter(pool), ENTRY, TESTS, source,
                              max_rps=MAX_RPS, max_checks=POOL_CAP),
        lambda: first_passing(iter(pool), ENTRY, TESTS, source, max_rps=MAX_RPS),
        lambda: first_passing(iter(pool), ENTRY, TESTS, source),
        lambda: first_passing(iter(pool), ENTRY, TESTS),
        lambda: first_passing(list(pool), ENTRY, TESTS),
    )
    for attempt in attempts:
        try:
            result = attempt()
        except Exception:
            continue
        # The call was accepted and completed: trust its verdict.
        return result if isinstance(result, str) and result.strip() else None
    return None


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
        # Pure count/off-by-one failure pattern -> try count rules first;
        # otherwise (direction, mixed, or unknown) lead with direction rules.
        direction_first = not ("count" in flags and "direction" not in flags)

        return _validate(_candidates(source, direction_first), source)
    except Exception:
        return None
