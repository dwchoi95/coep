```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
import ast

TESTS = [
    {"args": [[["F", 19]]], "expected": [["F", 19]]},
    {"args": [[["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]], "expected": [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]], "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30]]], "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18]]},
    {"args": [[["M", 23], ["F", 19], ["M", 30]]], "expected": [["M", 30], ["M", 23], ["F", 19]]},
    {"args": [[]], "expected": []},
]

def custom_fixes(source):
    """Generate problem-specific fixes for common bugs in sorting assignments."""
    # Fix 1: return X.reverse() should be X.reverse(); return X
    # (list.reverse() returns None, not the reversed list)
    for var in ['lst', 'a', 'sort', 'new', 'result']:
        fixed = source.replace(f"return {var}.reverse()", f"{var}.reverse()\n    return {var}")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 2: print(...) should be return (...)
    # (missing return statement, has print instead)
    if "print(" in source:
        lines = source.split('\n')
        fixed_lines = []
        for line in lines:
            if "print(" in line:
                stripped = line.lstrip()
                indent = line[:len(line) - len(stripped)]
                stripped = stripped.replace("print(", "return (", 1)
                fixed_lines.append(indent + stripped)
            else:
                fixed_lines.append(line)
        fixed = '\n'.join(fixed_lines)
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except:
        return None
    
    # Test if original already passes all tests
    result = failing_tests(source, "sort_age", TESTS)
    if result.compiled and result.passed == result.total:
        return source
    
    # Don't attempt repair if code doesn't compile
    if not result.compiled:
        return None
    
    # Chain candidates in priority order: custom fixes first, then generic edits
    candidates = chain(
        custom_fixes(source),
        candidates_generic(source, max_edits=1, budget=2000),
        candidates_generic(source, max_edits=2, budget=2000)
    )
    
    # Find first candidate passing all tests with acceptable patch size
    fixed = first_passing(candidates, "sort_age", TESTS, source, max_rps=0.35, max_checks=800)
    return fixed
```
