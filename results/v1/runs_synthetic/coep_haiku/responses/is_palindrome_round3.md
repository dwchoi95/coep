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
        # Try with max_edits=1 first (catches single operator/constant/method name changes)
        # Increased budget to explore method name changes like isalpha→isalnum
        candidates = candidates_generic(source, max_edits=1, budget=6000)
        result = first_passing(candidates, "is_palindrome", TESTS, source, max_rps=0.35, max_checks=2500)
        
        if result:
            return result
        
        # Try with max_edits=2 for compound bugs (e.g., slice adjustments + comparison changes)
        # Increased budget to explore more complex two-edit combinations
        candidates = candidates_generic(source, max_edits=2, budget=5000)
        result = first_passing(candidates, "is_palindrome", TESTS, source, max_rps=0.35, max_checks=2200)
        
        if result:
            return result
        
        # Try with max_edits=3 for structural logic changes (e.g., slice/comparison rewrites)
        # Handles cases where multiple expressions need simultaneous correction
        candidates = candidates_generic(source, max_edits=3, budget=4000)
        result = first_passing(candidates, "is_palindrome", TESTS, source, max_rps=0.35, max_checks=1800)
        
        if result:
            return result
        
        # Final aggressive pass with max_edits=4 for heavily broken logic
        # May catch edge cases where slice logic or filtering needs major restructuring
        candidates = candidates_generic(source, max_edits=4, budget=3000)
        result = first_passing(candidates, "is_palindrome", TESTS, source, max_rps=0.35, max_checks=1500)
        
        return result
    except Exception:
        return None
```
