```python
import ast
from coep.repairlib import candidates_generic, first_passing, failing_tests

TESTS = [
    {"args": [0], "expected": 0},
    {"args": [5], "expected": 5},
    {"args": [9], "expected": 9},
    {"args": [10], "expected": 1},
    {"args": [99], "expected": 18},
    {"args": [100], "expected": 1},
    {"args": [123], "expected": 6},
    {"args": [1000], "expected": 1},
    {"args": [4444], "expected": 16},
    {"args": [7], "expected": 7},
    {"args": [10001], "expected": 2},
    {"args": [55555], "expected": 25},
    {"args": [987654321], "expected": 45},
    {"args": [999999999], "expected": 81},
]

def repair(source: str) -> str | None:
    try:
        # Parse to check syntax
        ast.parse(source)
    except SyntaxError:
        return None
    
    try:
        entry = "sum_digits"
        
        # Check which tests fail
        result = failing_tests(source, entry, TESTS)
        
        if result.compiled and result.passed == result.total:
            # Already passing
            return source
        
        # Generate candidates with small edits
        candidates = candidates_generic(source, max_edits=1, budget=2000)
        
        # Find the first candidate that passes all tests
        fixed = first_passing(candidates, entry, TESTS, source, max_rps=0.35, max_checks=800)
        
        return fixed
    except Exception:
        return None
```
