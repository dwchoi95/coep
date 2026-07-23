You previously wrote the following per-assignment repair module for the assignment "refactory_q4":

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

Evaluated on the sample buggy submissions, the outcomes were:
- real_146.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_186.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_202.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_334.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- real_344.py: NOT REPAIRED — TypeError: 'function' object is not iterable

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

### Failed submission real_186.py
```python
def sort_age(lst):
    a = lst
    sort = []
    while a:
        largest = a[0]
        for item in a:
            if item[1] >largest[1]:
                largest = item
        a.remove(largest)
        sort.append(largest)

    print(sort)# Fill in your code here
    

```

### Failed submission real_202.py
```python
def sort_age(lst):
    decoy = []
    decoy2 = []
    final = []
    for i in lst:
        decoy.append(i[1])
    while decoy != []:
        decoy2.append(min(decoy))
        decoy.remove(min(decoy))
    for i in decoy2:
        for j in lst:
            if i == j[1]:
                final.append(j)
    return final
    
    

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
