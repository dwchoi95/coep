You previously wrote the following per-assignment repair module for the assignment "top_k":

```python
from coep.repairlib import candidates_generic, first_passing, chain
import ast
import re

TESTS = [
    {"args": [[5, 5, 1], 2], "expected": [5, 5]},
    {"args": [[3, 1, 2], 2], "expected": [3, 2]},
    {"args": [[1, 2, 3, 4, 5], 3], "expected": [5, 4, 3]},
    {"args": [[], 0], "expected": []},
    {"args": [[], 3], "expected": []},
    {"args": [[7], 1], "expected": [7]},
    {"args": [[4, 2], 0], "expected": []},
    {"args": [[1, 2], 5], "expected": [2, 1]},
    {"args": [[-1, -5, -3], 2], "expected": [-1, -3]},
    {"args": [[10, 10, 10], 2], "expected": [10, 10]},
    {"args": [[0, -1, 1], 3], "expected": [1, 0, -1]},
    {"args": [[2, 8, 6, 4, 9, 1], 4], "expected": [9, 8, 6, 4]},
    {"args": [[5, 3, 5, 3, 5], 3], "expected": [5, 5, 5]},
    {"args": [[100], 0], "expected": []},
]

def specific_fixes(source):
    """Generate problem-specific fixes for common top_k bugs."""
    fixes = [
        (r"\[:k\s*-\s*1\]", "[:k]"),
        (r"reverse\s*=\s*False", "reverse=True"),
        (r"nsmallest", "nlargest"),
        (r"len\(result\)\s*<=\s*k", "len(result) < k"),
        (r"m\s*=\s*temp\[-1\]", "m = temp[0]"),
    ]
    
    for pattern, replacement in fixes:
        modified = re.sub(pattern, replacement, source)
        if modified != source:
            yield modified

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    candidates = chain(
        specific_fixes(source),
        candidates_generic(source, max_edits=1, budget=1500)
    )
    result = first_passing(candidates, "top_k", TESTS, source, max_rps=0.35, max_checks=1000)
    if result:
        return result
    
    candidates = candidates_generic(source, max_edits=2, budget=1500)
    result = first_passing(candidates, "top_k", TESTS, source, max_rps=0.35, max_checks=500)
    if result:
        return result
    
    return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_04.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- crafted_10.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- mutant_02.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- mutant_03.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- mutant_06.py: NOT REPAIRED — TypeError: 'function' object is not iterable

For reference, the submissions the module failed on:

### Failed submission crafted_04.py
```python
def top_k(lst, k):
    return sorted(lst, reverse=True)[:k - 1]

```

### Failed submission crafted_10.py
```python
import heapq

def top_k(lst, k):
    return heapq.nsmallest(k, lst)

```

### Failed submission mutant_02.py
```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) <= k:
        m = temp[0]
        for v in temp:
            if v > m:
                m = v
        temp.remove(m)
        result.append(m)
    return result

```

### Failed submission mutant_03.py
```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) <= k:
        m = temp[-1]
        for v in temp:
            if v > m:
                m = v
        temp.remove(m)
        result.append(m)
    return result

```

### Failed submission mutant_06.py
```python
def top_k(lst, k):
    return sorted(lst, reverse=False)[:k]

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
