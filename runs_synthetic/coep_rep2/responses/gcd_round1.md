```python
"""Local, LLM-free automatic repair for the gcd assignment.

Strategy:
  1. Parse defensively (syntax errors -> None, never raise).
  2. Build a prioritized stream of candidate programs:
       a. The original itself (in case it already passes).
       b. Problem-specific rewrites that fix the common gcd misconception:
          a botched base case of the form `if b <cmp> <const>: return a`
          (students write `b != 1`, `b != -1`, `b == 1`, ... instead of
          `b == 0`).  We rewrite every integer-constant comparison to the
          small set {==,!=} x {0,1} in a single shot, so no reliance on
          2-edit combinatorics is needed for these.
       c. Generic single-edit search (operator swaps, off-by-one, boolean
          flips, argument swaps at every AST site).
       d. Generic two-edit search (with a budget) for mutations that need
          two simultaneous changes (e.g. `b != 1` -> `b == 0`).
  3. Validate EVERY candidate through `first_passing`, which enforces the
     full visible test suite AND the relative-patch-size cap (rps <= 0.35),
     guaranteeing repairs stay close to the student's own approach.
"""

import ast

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401  (available per spec)

ENTRY = "gcd"

TESTS = [
    {"args": [48, 18], "expected": 6},
    {"args": [18, 48], "expected": 6},
    {"args": [0, 5], "expected": 5},
    {"args": [5, 0], "expected": 5},
    {"args": [0, 0], "expected": 0},
    {"args": [7, 7], "expected": 7},
    {"args": [1, 999], "expected": 1},
    {"args": [12, 8], "expected": 4},
    {"args": [100, 75], "expected": 25},
    {"args": [13, 17], "expected": 1},
    {"args": [270, 192], "expected": 6},
    {"args": [1000000, 999999], "expected": 1},
    {"args": [36, 60], "expected": 12},
    {"args": [2, 4], "expected": 2},
]

MAX_RPS = 0.35


def _int_const_compares(tree):
    """Single-op comparisons whose right operand is a plain int constant."""
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and len(node.comparators) == 1
        ):
            comp = node.comparators[0]
            if (
                isinstance(comp, ast.Constant)
                and isinstance(comp.value, int)
                and not isinstance(comp.value, bool)
            ):
                out.append(node)
    return out


def _yield_original(source):
    yield source


def _problem_specific(source):
    """Rewrite botched base-case comparisons `b <cmp> <int>` -> {==,!=}x{0,1}."""
    try:
        base = ast.parse(source)
    except Exception:
        return
    count = len(_int_const_compares(base))
    for i in range(count):
        for op_cls in (ast.Eq, ast.NotEq):
            for cval in (0, 1):
                try:
                    tree = ast.parse(source)
                    node = _int_const_compares(tree)[i]
                    node.ops[0] = op_cls()
                    node.comparators[0] = ast.Constant(cval)
                    ast.fix_missing_locations(tree)
                    yield ast.unparse(tree)
                except Exception:
                    continue


def repair(source):
    # ---- defensive input handling -------------------------------------
    if not isinstance(source, str):
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    # ---- fast path: already correct -----------------------------------
    try:
        res = failing_tests(source, ENTRY, TESTS)
        if getattr(res, "compiled", False) and res.passed == res.total:
            return source
    except Exception:
        pass

    # ---- build prioritized candidate stream ---------------------------
    generators = [_yield_original(source)]
    try:
        generators.append(_problem_specific(source))
    except Exception:
        pass
    try:
        generators.append(candidates_generic(source, max_edits=1, budget=2000))
    except Exception:
        pass
    try:
        generators.append(candidates_generic(source, max_edits=2, budget=4000))
    except Exception:
        pass

    # ---- validate everything through first_passing --------------------
    try:
        candidate = first_passing(
            chain(*generators),
            ENTRY,
            TESTS,
            source,
            max_rps=MAX_RPS,
            max_checks=800,
        )
    except Exception:
        return None

    return candidate
```
