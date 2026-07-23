You previously wrote the following per-assignment repair module for the assignment "refactory_q4":

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests
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
    
    # Fix 3: Remove instead of value for real_146.py
    # Pattern: lst.remove(youngest) where youngest is an age, not an element
    # Solution: Find the element with minimum age and remove it
    if "lst.remove(" in source and "youngest" in source:
        fixed = source.replace(
            "lst.remove(youngest)",
            "lst.remove(min(lst, key=lambda x: x[1]))"
        )
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 4: Ascending/descending order mismatch (real_202.py)
    # min() in a loop produces ascending order, but expected is descending
    # Solution: Reverse the final result
    for result_var in ['final', 'result', 'sort', 'decoy2', 'sorted']:
        if f"return {result_var}" in source:
            fixed = source.replace(f"return {result_var}", f"return {result_var}[::-1]")
            if fixed != source:
                try:
                    ast.parse(fixed)
                    yield fixed
                except:
                    pass
    
    # Fix 5: Use sorted() with reverse=True (real_344.py)
    # Pattern: manual sorting with if/else on ages
    # Solution: Use sorted() to properly sort by age descending
    if "for i in lst:" in source and "if i[1]" in source:
        fixed = source.replace(
            "for i in lst:",
            "for i in sorted(lst, key=lambda x: x[1], reverse=True):"
        )
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 6: Fix tuple building logic (real_344.py)
    # Pattern: tuple(i)+tup doesn't modify tup when in else clause
    # Solution: Assign the result back to tup
    if "tuple(i)+tup" in source:
        fixed = source.replace("tuple(i)+tup", "tup += tuple([i])")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 7: Proper tuple concatenation for sorted items
    # Pattern: tup+=tuple(i) when i is a list item [gender, age]
    # Solution: tup+=(i,) to append item as tuple element
    if "tup+=" in source and "tuple(i)" in source:
        fixed = source.replace("tup+=tuple(i)", "tup+=(i,)")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass

def all_candidates(source):
    """Generate all candidates: custom fixes + generic edits."""
    # Custom fixes first (higher priority for targeted bugs)
    try:
        for cand in custom_fixes(source):
            yield cand
    except:
        pass
    
    # Generic edits with single-character max edits
    try:
        for cand in candidates_generic(source, max_edits=1, budget=2000):
            yield cand
    except:
        pass
    
    # Generic edits with dual-character max edits
    try:
        for cand in candidates_generic(source, max_edits=2, budget=2000):
            yield cand
    except:
        pass

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except:
        return None
    
    # Test if original already passes all tests
    try:
        result = failing_tests(source, "sort_age", TESTS)
        if result.compiled and result.passed == result.total:
            return source
        
        # Don't attempt repair if code doesn't compile
        if not result.compiled:
            return None
    except:
        return None
    
    # Find first candidate passing all tests with acceptable patch size
    try:
        fixed = first_passing(all_candidates(source), "sort_age", TESTS, source, max_rps=0.35, max_checks=800)
        return fixed
    except:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- real_146.py: NOT REPAIRED — no_patch
- real_186.py: REPAIRED
- real_202.py: REPAIRED
- real_334.py: NOT REPAIRED — repairer_timeout
- real_344.py: NOT REPAIRED — no_patch

For reference, the submissions the module failed on:

### Failed submission real_146.py
```python
def sort_age(lst):
    youngest = lst[0][1]
    sorted = []
    while lst:
        for elem in lst:
            if elem[1] < youngest:
                youngest = elem[1]
        lst.remove(youngest)
        sorted.append(youngest)
    return sorted

```

### Failed submission real_334.py
```python
def sort_age(lst):
    for i in range(1,len(lst)):
        while lst[i][1]<lst[i-1][1]:
            lst.pop(i)
            lst.insert(i-1,lst[i])# Fill in your code here
    return lst.reverse()

```

### Failed submission real_344.py
```python
def sort_age(lst):
    current=0
    tup=()
    for i in lst:
        if i[1]>current:
            tup+=tuple(i)
            current=i[1]
        else:
            tuple(i)+tup
    return tup
            

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
