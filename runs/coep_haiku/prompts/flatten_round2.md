You previously wrote the following per-assignment repair module for the assignment "flatten":

```python
from coep.repairlib import candidates_generic, first_passing
import ast

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, [2, 3]]], "expected": [1, 2, 3]},
    {"args": [[[1, 2], [3, 4]]], "expected": [1, 2, 3, 4]},
    {"args": [[[[[[1]]]]]]], "expected": [1]},
    {"args": [[1, [2, [3, [4, [5]]]]]], "expected": [1, 2, 3, 4, 5]},
    {"args": [[[], [], []]], "expected": []},
    {"args": [[0]], "expected": [0]},
    {"args": [[1, [], 2]], "expected": [1, 2]},
    {"args": [[[1], [2], 3, [4, [5, 6]]]], "expected": [1, 2, 3, 4, 5, 6]},
    {"args": [[-1, [-2, [-3]]]], "expected": [-1, -2, -3]},
    {"args": [[[[]], [[[]]], 5]], "expected": [5]},
    {"args": [[10, [20], [30, [40]], 50]], "expected": [10, 20, 30, 40, 50]},
    {"args": [[[1, [2]], 3]], "expected": [1, 2, 3]},
]

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Try single edit candidates first
    candidates = candidates_generic(source, max_edits=1, budget=2000)
    result = first_passing(candidates, 'flatten', TESTS, source, max_rps=0.35)
    if result:
        return result
    
    # Try double edit candidates if single edit didn't work
    candidates = candidates_generic(source, max_edits=2, budget=2000)
    result = first_passing(candidates, 'flatten', TESTS, source, max_rps=0.35)
    if result:
        return result
    
    return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_02.py: NOT REPAIRED — SyntaxError: closing parenthesis ']' does not match opening parenthesis '{' (repairer_haiku.py, line 9)
- crafted_08.py: NOT REPAIRED — SyntaxError: closing parenthesis ']' does not match opening parenthesis '{' (repairer_haiku.py, line 9)
- mutant_01.py: NOT REPAIRED — SyntaxError: closing parenthesis ']' does not match opening parenthesis '{' (repairer_haiku.py, line 9)
- mutant_03.py: NOT REPAIRED — SyntaxError: closing parenthesis ']' does not match opening parenthesis '{' (repairer_haiku.py, line 9)
- mutant_04.py: NOT REPAIRED — SyntaxError: closing parenthesis ']' does not match opening parenthesis '{' (repairer_haiku.py, line 9)

For reference, the submissions the module failed on:

### Failed submission crafted_02.py
```python
def flatten(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            for x in item:
                result.append(x)
        else:
            result.append(item)
    return result

```

### Failed submission crafted_08.py
```python
def flatten(nested):
    total = []
    for item in nested:
        total.extend(item)
    return total

```

### Failed submission mutant_01.py
```python
def flatten(nested):
    result = []
    for item in nested:
        if isinstance(list, item):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result

```

### Failed submission mutant_03.py
```python
def flatten(nested):
    flat = list(nested)
    while any((isinstance(list, x) for x in flat)):
        nxt = []
        for x in flat:
            if isinstance(x, list):
                nxt.extend(x)
            else:
                nxt.append(x)
        flat = nxt
    return flat

```

### Failed submission mutant_04.py
```python
def flatten(nested):
    flat = list(nested)
    while any((isinstance(list, x) for x in flat)):
        nxt = []
        for x in flat:
            if isinstance(list, x):
                nxt.extend(x)
            else:
                nxt.append(x)
        flat = nxt
    return flat

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
