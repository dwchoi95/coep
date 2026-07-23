```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
import ast

TESTS = [
    {"function": "unique_day", "args": ["1", [["January", "1"], ["February", "1"]]], "expected": False},
    {"function": "unique_month", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": False},
    {"function": "unique_month", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": True},
    {"function": "contains_unique_day", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": True},
    {"function": "contains_unique_day", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": False},
    {"function": "contains_unique_day", "args": ["February", [["January", "10"], ["February", "1"], ["February", "10"]]], "expected": True},
    {"function": "unique_day", "args": ["3", [["January", "1"], ["January", "2"]]], "expected": False},
    {"function": "unique_month", "args": ["March", [["January", "1"], ["February", "1"]]], "expected": False},
    {"function": "unique_day", "args": ["1", [["January", "1"], ["January", "2"]]], "expected": True},
]

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Try candidates: first the original, then generated candidates
    def original_candidate():
        yield source
    
    candidates = chain(original_candidate(), candidates_generic(source, max_edits=1, budget=2000))
    
    # Use first_passing to find a valid repair
    repair_result = first_passing(candidates, "unique_day", TESTS, source, max_rps=0.35, max_checks=800)
    
    return repair_result
```
