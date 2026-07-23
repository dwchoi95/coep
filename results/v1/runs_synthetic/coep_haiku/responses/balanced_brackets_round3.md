```python
from coep.repairlib import candidates_generic, first_passing, failing_tests
import ast

TESTS = [
    {"args": ["()"], "expected": True},
    {"args": ["([)]"], "expected": False},
    {"args": [""], "expected": True},
    {"args": ["no brackets here!"], "expected": True},
    {"args": ["(a[b]{c})"], "expected": True},
    {"args": ["((("], "expected": False},
    {"args": [")("], "expected": False},
    {"args": ["{[()()]}"], "expected": True},
    {"args": ["([]"], "expected": False},
    {"args": ["())"], "expected": False},
    {"args": ["[(])"], "expected": False},
    {"args": ["{}[]()"], "expected": True},
    {"args": ["([{([{}])}])"], "expected": True},
    {"args": ["]"], "expected": False},
]

def repair(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    
    if not any(isinstance(node, ast.FunctionDef) and node.name == "balanced_brackets" 
               for node in ast.walk(tree)):
        return None
    
    result = failing_tests(source, "balanced_brackets", TESTS)
    
    if result.passed == result.total:
        return None
    
    # Stage 1: Single edit, tight RPS constraint
    candidates = candidates_generic(source, max_edits=1, budget=5000)
    found = first_passing(candidates, "balanced_brackets", TESTS, source, max_rps=0.35, max_checks=2000)
    if found:
        return found
    
    # Stage 2: Two edits, relaxed RPS as complexity grows
    candidates = candidates_generic(source, max_edits=2, budget=5000)
    found = first_passing(candidates, "balanced_brackets", TESTS, source, max_rps=0.5, max_checks=2000)
    if found:
        return found
    
    # Stage 3: Three edits, further relaxed
    candidates = candidates_generic(source, max_edits=3, budget=5000)
    found = first_passing(candidates, "balanced_brackets", TESTS, source, max_rps=0.65, max_checks=2000)
    if found:
        return found
    
    # Stage 4: Four edits, significantly relaxed
    candidates = candidates_generic(source, max_edits=4, budget=5000)
    found = first_passing(candidates, "balanced_brackets", TESTS, source, max_rps=0.8, max_checks=2000)
    if found:
        return found
    
    # Stage 5: Five edits, very relaxed (handles algorithm-level rewrites)
    candidates = candidates_generic(source, max_edits=5, budget=5000)
    found = first_passing(candidates, "balanced_brackets", TESTS, source, max_rps=0.85, max_checks=2000)
    if found:
        return found
    
    return None
```
