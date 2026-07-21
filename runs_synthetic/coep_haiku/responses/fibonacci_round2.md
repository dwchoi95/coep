```python
from coep.repairlib import candidates_generic, first_passing, chain
import ast

TESTS = [
    {"args": [0], "expected": 0},
    {"args": [1], "expected": 1},
    {"args": [2], "expected": 1},
    {"args": [3], "expected": 2},
    {"args": [4], "expected": 3},
    {"args": [5], "expected": 5},
    {"args": [6], "expected": 8},
    {"args": [7], "expected": 13},
    {"args": [8], "expected": 21},
    {"args": [10], "expected": 55},
    {"args": [12], "expected": 144},
    {"args": [15], "expected": 610},
    {"args": [20], "expected": 6765},
    {"args": [24], "expected": 46368},
]

def repair(source: str) -> str | None:
    # Check for syntax errors
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Generate candidate repairs: first try single edits, then pairs of edits
    # candidates_generic returns a generator function, so call with () to activate it
    candidates = chain(
        candidates_generic(source, max_edits=1, budget=2000)(),
        candidates_generic(source, max_edits=2, budget=2000)()
    )
    
    # Find the first candidate that passes all tests within patch size limit
    result = first_passing(candidates, "fibonacci", TESTS, source, max_rps=0.35, max_checks=800)
    
    return result
```
