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
    
    # Pattern 1: set() usage destroys order—fundamentally incompatible
    if "set(" in source:
        fixed = source.replace(
            "list(set(lst))",
            "[x for i, x in enumerate(lst) if i == 0 or x != lst[i-1]]"
        )
        if fixed != source:
            failure_info = failing_tests(fixed, "unique_in_order", TESTS)
            if failure_info.compiled and failure_info.passed == failure_info.total:
                return fixed
    
    # Pattern 2: Loop starting from 1 skips first element
    if "range(1," in source:
        fixed = source.replace(
            "result = []",
            "result = [lst[0]] if lst else []"
        )
        if fixed != source:
            failure_info = failing_tests(fixed, "unique_in_order", TESTS)
            if failure_info.compiled and failure_info.passed == failure_info.total:
                return fixed
    
    # Fallback: Try with progressively increasing edit limits
    for max_edits, budget in [
        (1, 2000),
        (2, 5000),
        (3, 15000),
        (4, 30000),
        (5, 50000),
    ]:
        candidates = candidates_generic(source, max_edits=max_edits, budget=budget)
        result = first_passing(candidates, "unique_in_order", TESTS, source, max_rps=0.35)
        if result is not None:
            return result
    
    return None
