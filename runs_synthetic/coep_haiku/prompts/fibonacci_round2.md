You previously wrote the following per-assignment repair module for the assignment "fibonacci":

```python
from coep.repairlib import candidates_generic, first_passing, chain
import ast

TESTS = [
    {"args": [0], "expected": 0},
    {"args": [1], "expected": 1},
    {"args": [2], "expected": 1},
    {"args": [3], "expected": 2},
    {"args": [4], "expected": 3},
    {"args": [5], "expected": 5},
    {"args": [6], "expected": 8},
    {"args": [7], "expected": 13},
    {"args": [8], "expected": 21},
    {"args": [10], "expected": 55},
    {"args": [12], "expected": 144},
    {"args": [15], "expected": 610},
    {"args": [20], "expected": 6765},
    {"args": [24], "expected": 46368},
]

def repair(source: str) -> str | None:
    # Check for syntax errors
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Generate candidate repairs: first try single edits, then pairs of edits
    candidates = chain(
        candidates_generic(source, max_edits=1, budget=2000),
        candidates_generic(source, max_edits=2, budget=2000)
    )
    
    # Find the first candidate that passes all tests within patch size limit
    result = first_passing(candidates, "fibonacci", TESTS, source, max_rps=0.35, max_checks=800)
    
    return result

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_02.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- crafted_09.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- mutant_02.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- mutant_06.py: NOT REPAIRED — TypeError: 'function' object is not iterable
- mutant_14.py: NOT REPAIRED — TypeError: 'function' object is not iterable

For reference, the submissions the module failed on:

### Failed submission crafted_02.py
```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b

```

### Failed submission crafted_09.py
```python
def fibonacci(n):
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[-1]

```

### Failed submission mutant_02.py
```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 0) + fibonacci(n - 2)

```

### Failed submission mutant_06.py
```python
def fibonacci(n):
    seq = [-1, 1]
    while len(seq) <= n:
        seq.append(seq[-1 + 1] + seq[-2])
    return seq[n]

```

### Failed submission mutant_14.py
```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 3)

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
