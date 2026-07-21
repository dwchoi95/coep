You previously wrote the following per-assignment repair module for the assignment "gcd":

```python
import ast
from coep.repairlib import candidates_generic, first_passing

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

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except Exception:
        return None
    
    entry = "gcd"
    
    try:
        # Try increasingly complex edits with higher search budgets
        for max_edits in [1, 2, 3]:
            candidates = candidates_generic(source, max_edits=max_edits, budget=8000)
            result = first_passing(candidates, entry, TESTS, source, max_rps=0.35, max_checks=1600)
            if result is not None:
                return result
    except Exception:
        return None
    
    return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_03.py: NOT REPAIRED — no_patch
- crafted_07.py: NOT REPAIRED — no_patch
- mutant_01.py: REPAIRED
- mutant_06.py: REPAIRED
- mutant_07.py: REPAIRED

For reference, the submissions the module failed on:

### Failed submission crafted_03.py
```python
def gcd(a, b):
    while b != 0:
        temp = b % a
        a = b
        b = temp
    return a

```

### Failed submission crafted_07.py
```python
def gcd(a, b):
    if b == 0:
        return a
    remainder = a % b
    return remainder

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
