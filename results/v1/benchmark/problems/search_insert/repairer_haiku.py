def repair(source: str) -> str | None:
    from coep.repairlib import candidates_generic, first_passing, failing_tests
    import ast
    
    TESTS = [
        {"args": [[1, 3, 5, 7], 5], "expected": 2},
        {"args": [[1, 3, 5, 7], 4], "expected": 2},
        {"args": [[1, 3, 5, 7], 0], "expected": 0},
        {"args": [[1, 3, 5, 7], 8], "expected": 4},
        {"args": [[], 4], "expected": 0},
        {"args": [[2, 2, 2, 2], 2], "expected": 0},
        {"args": [[1, 2, 2, 3], 2], "expected": 1},
        {"args": [[10], 10], "expected": 0},
        {"args": [[10], 5], "expected": 0},
        {"args": [[10], 15], "expected": 1},
        {"args": [[1, 1, 2, 3, 3, 3, 4], 3], "expected": 3},
        {"args": [[-5, -2, 0, 3], -2], "expected": 1},
        {"args": [[1, 3, 5, 7], 1], "expected": 0},
        {"args": [[1, 3, 5, 7], 7], "expected": 3},
    ]
    
    # Validate syntax
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    entry = "search_insert"
    
    # Check if already passing
    failures = failing_tests(source, entry, TESTS)
    if failures.passed == failures.total:
        return source
    
    # Try single edits first (most common fixes)
    candidates = candidates_generic(source, max_edits=1, budget=2000)
    fixed = first_passing(candidates, entry, TESTS, source, max_rps=0.35, max_checks=800)
    if fixed:
        return fixed
    
    # Try double edits if single edit didn't work
    candidates = candidates_generic(source, max_edits=2, budget=2000)
    fixed = first_passing(candidates, entry, TESTS, source, max_rps=0.35, max_checks=800)
    
    return fixed
