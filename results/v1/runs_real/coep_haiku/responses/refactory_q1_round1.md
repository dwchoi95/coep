```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
import ast

TESTS = [
    {"args": [42, [-5, 1, 3, 5, 7, 10]], "expected": 6},
    {"args": [42, [1, 5, 10]], "expected": 3},
    {"args": [5, [1, 5, 10]], "expected": 1},
    {"args": [7, [1, 5, 10]], "expected": 2},
    {"args": [3, [1, 5, 10]], "expected": 1},
    {"args": [-5, [1, 5, 10]], "expected": 0},
    {"args": [10, [-5, -1, 3, 5, 7, 10]], "expected": 5},
    {"args": [-100, [-5, -1, 3, 5, 7, 10]], "expected": 0},
    {"args": [0, [-5, -1, 3, 5, 7, 10]], "expected": 2},
    {"args": [100, []], "expected": 0},
    {"args": [-100, []], "expected": 0},
]


def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Strategy 1: Try generic edits with max_edits=1
    # This handles comparison operator swaps, off-by-one errors, etc.
    candidates = candidates_generic(source, max_edits=1, budget=2000)
    result = first_passing(candidates, "search", TESTS, source, max_rps=0.35, max_checks=800)
    if result is not None:
        return result
    
    # Strategy 2: Try with max_edits=2 for more complex fixes
    candidates = candidates_generic(source, max_edits=2, budget=3000)
    result = first_passing(candidates, "search", TESTS, source, max_rps=0.35, max_checks=800)
    if result is not None:
        return result
    
    # Strategy 3: Try adding missing return statement, then search again
    modified_source = add_missing_return(source)
    if modified_source != source:
        candidates = candidates_generic(modified_source, max_edits=1, budget=2000)
        result = first_passing(candidates, "search", TESTS, source, max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    
    return None


def add_missing_return(source: str) -> str:
    """
    Add 'return len(seq)' at the end of the search function if it doesn't 
    already end with a return statement. This handles cases where functions
    implicitly return None for certain inputs (e.g., empty sequences).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    
    # Check if search function ends with a return statement
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "search":
            if node.body and isinstance(node.body[-1], ast.Return):
                return source  # Already ends with return
            break
    
    # Find the last non-empty, non-comment line and add return after it
    lines = source.split('\n')
    last_code_idx = -1
    
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith('#'):
            last_code_idx = i
            break
    
    if last_code_idx < 0:
        return source
    
    # Preserve indentation
    indent = len(lines[last_code_idx]) - len(lines[last_code_idx].lstrip())
    new_lines = lines[:last_code_idx+1] + [' ' * indent + 'return len(seq)'] + lines[last_code_idx+1:]
    return '\n'.join(new_lines)
```
