```python
def repair(source: str) -> str | None:
    from coep.repairlib import candidates_generic, first_passing, failing_tests
    from coep.evaluate import rps
    import ast
    
    TESTS = [
        {"args": [[]], "expected": []},
        {"args": [[1]], "expected": [1]},
        {"args": [[1, 1]], "expected": [1]},
        {"args": [[1, 1, 2, 1]], "expected": [1, 2, 1]},
        {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
        {"args": [[1, 1, 1, 1]], "expected": [1]},
        {"args": [["a", "a", "b", "b", "a"]], "expected": ["a", "b", "a"]},
        {"args": [[1, "1", 1]], "expected": [1, "1", 1]},
        {"args": [[2, 2, 2, 3, 3, 1, 1, 2]], "expected": [2, 3, 1, 2]},
        {"args": [["A", "a", "A"]], "expected": ["A", "a", "A"]},
        {"args": [[0, 0, 0]], "expected": [0]},
        {"args": [[5, 4, 4, 5, 5, 4]], "expected": [5, 4, 5, 4]},
        {"args": [["x"]], "expected": ["x"]},
        {"args": [[1, 2, 2, 3, 3, 3, 4]], "expected": [1, 2, 3, 4]},
    ]
    
    # Validate syntax
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Check if already passing all tests
    failure_info = failing_tests(source, "unique_in_order", TESTS)
    if not failure_info.compiled:
        return None
    if failure_info.passed == failure_info.total:
        return source
    
    # Try with single edits (catches most off-by-one, operator, and index errors)
    candidates = candidates_generic(source, max_edits=1, budget=2000)
    result = first_passing(candidates, "unique_in_order", TESTS, source, max_rps=0.35)
    if result is not None:
        return result
    
    # Try with pairs of edits (catches more complex bug combinations)
    candidates = candidates_generic(source, max_edits=2, budget=5000)
    result = first_passing(candidates, "unique_in_order", TESTS, source, max_rps=0.35)
    if result is not None:
        return result
    
    return None
```
