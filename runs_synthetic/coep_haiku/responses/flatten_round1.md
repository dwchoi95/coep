```python
from coep.repairlib import candidates_generic, first_passing
import ast

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, [2, 3]]], "expected": [1, 2, 3]},
    {"args": [[[1, 2], [3, 4]]], "expected": [1, 2, 3, 4]},
    {"args": [[[[[[1]]]]]]], "expected": [1]},
    {"args": [[1, [2, [3, [4, [5]]]]]], "expected": [1, 2, 3, 4, 5]},
    {"args": [[[], [], []]], "expected": []},
    {"args": [[0]], "expected": [0]},
    {"args": [[1, [], 2]], "expected": [1, 2]},
    {"args": [[[1], [2], 3, [4, [5, 6]]]], "expected": [1, 2, 3, 4, 5, 6]},
    {"args": [[-1, [-2, [-3]]]], "expected": [-1, -2, -3]},
    {"args": [[[[]], [[[]]], 5]], "expected": [5]},
    {"args": [[10, [20], [30, [40]], 50]], "expected": [10, 20, 30, 40, 50]},
    {"args": [[[1, [2]], 3]], "expected": [1, 2, 3]},
]

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Try single edit candidates first
    candidates = candidates_generic(source, max_edits=1, budget=2000)
    result = first_passing(candidates, 'flatten', TESTS, source, max_rps=0.35)
    if result:
        return result
    
    # Try double edit candidates if single edit didn't work
    candidates = candidates_generic(source, max_edits=2, budget=2000)
    result = first_passing(candidates, 'flatten', TESTS, source, max_rps=0.35)
    if result:
        return result
    
    return None
```
