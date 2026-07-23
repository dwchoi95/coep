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
