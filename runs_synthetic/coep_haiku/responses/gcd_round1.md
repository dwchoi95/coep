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
        # Try single-edit candidates first
        candidates = candidates_generic(source, max_edits=1, budget=2000)
        result = first_passing(candidates, entry, TESTS, source, max_rps=0.35, max_checks=800)
        if result is not None:
            return result
        
        # Try up to 2-edit candidates if single edits don't work
        candidates = candidates_generic(source, max_edits=2, budget=2000)
        result = first_passing(candidates, entry, TESTS, source, max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    except Exception:
        return None
    
    return None
```
