You previously wrote the following per-assignment repair module for the assignment "is_palindrome":

```python
from coep.repairlib import candidates_generic, first_passing
import ast

TESTS = [
    {"args": [""], "expected": True},
    {"args": ["a"], "expected": True},
    {"args": ["abba"], "expected": True},
    {"args": ["abc"], "expected": False},
    {"args": ["A man, a plan, a canal: Panama"], "expected": True},
    {"args": ["race a car"], "expected": False},
    {"args": ["No 'x' in Nixon"], "expected": True},
    {"args": ["12321"], "expected": True},
    {"args": ["1231"], "expected": False},
    {"args": ["!!!"], "expected": True},
    {"args": ["Aa"], "expected": True},
    {"args": ["0P"], "expected": False},
    {"args": ["Was it a car or a cat I saw?"], "expected": True},
    {"args": ["ab"], "expected": False},
]

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    try:
        # Try with max_edits=1 first (catches single operator/constant/index flips)
        # This handles: != vs ==, i += 0 vs i += 1, off-by-one indices, etc.
        candidates = candidates_generic(source, max_edits=1, budget=2000)
        result = first_passing(candidates, "is_palindrome", TESTS, source, max_rps=0.35, max_checks=800)
        
        if result:
            return result
        
        # Try with max_edits=2 for compound bugs (e.g., multiple index adjustments)
        candidates = candidates_generic(source, max_edits=2, budget=1000)
        result = first_passing(candidates, "is_palindrome", TESTS, source, max_rps=0.35, max_checks=500)
        
        return result
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_03.py: NOT REPAIRED — no_patch
- crafted_10.py: NOT REPAIRED — no_patch
- mutant_01.py: REPAIRED
- mutant_06.py: REPAIRED
- mutant_08.py: REPAIRED

For reference, the submissions the module failed on:

### Failed submission crafted_03.py
```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalpha())
    return t == t[::-1]

```

### Failed submission crafted_10.py
```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    half = len(t) // 2
    return t[:half] == t[half:]

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
