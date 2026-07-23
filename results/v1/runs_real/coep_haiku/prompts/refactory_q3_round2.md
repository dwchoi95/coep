You previously wrote the following per-assignment repair module for the assignment "refactory_q3":

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
import re

TESTS = [
    {"args": [[1, 1, 1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 5, 1, 1, 3, 2]], "expected": [1, 5, 3, 2]},
    {"args": [[]], "expected": []},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
]

def repair(source: str) -> str | None:
    try:
        # Strategy 1: Pure generic search with single edits
        candidates = candidates_generic(source, max_edits=1, budget=2000)
        result = first_passing(
            candidates, "remove_extras", TESTS, source, max_rps=0.35, max_checks=800
        )
        if result:
            return result
    except:
        pass

    # Strategy 2: Apply problem-specific syntactic fixes, then retry
    try:
        fixed = apply_problem_specific_fixes(source)
        if fixed != source:
            candidates = candidates_generic(fixed, max_edits=1, budget=1500)
            result = first_passing(
                candidates, "remove_extras", TESTS, source, max_rps=0.35, max_checks=600
            )
            if result:
                return result
    except:
        pass

    # Strategy 3: Try with higher edit budget (pairs of edits)
    try:
        candidates = candidates_generic(source, max_edits=2, budget=2500)
        result = first_passing(
            candidates, "remove_extras", TESTS, source, max_rps=0.35, max_checks=400
        )
        if result:
            return result
    except:
        pass

    return None


def apply_problem_specific_fixes(source: str) -> str:
    """Apply fixes for common bugs specific to duplicate elimination."""

    # Fix: list.reverse() returns None, not the reversed list
    # Pattern: var = some_list.reverse()
    source = re.sub(
        r"(\w+)\s*=\s*(\w+)\.reverse\(\)", r"\1 = \2[::-1]", source
    )

    # Fix: Remove debug print statements (on their own line)
    source = re.sub(r"^\s*print\s*\([^)]*\)\s*$", "", source, flags=re.MULTILINE)

    # Fix: Tuple syntax ((x)) should be (x,) to create single-element tuple
    source = re.sub(r"\(\(\s*(\w+)\s*\)\)", r"(\1,)", source)

    return source

```

Evaluated on the sample buggy submissions, the outcomes were:
- real_053.py: NOT REPAIRED — no_patch
- real_087.py: NOT REPAIRED — no_patch
- real_142.py: NOT REPAIRED — no_patch
- real_265.py: NOT REPAIRED — no_patch
- real_281.py: NOT REPAIRED — no_patch

For reference, the submissions the module failed on:

### Failed submission real_053.py
```python
def remove_extras(lst):
    for num in lst:
        while lst.count(num)>1:
            lst.remove(num)
    return lst

```

### Failed submission real_087.py
```python
def remove_extras(lst):
    a = ()
    n = len(lst)
    for i in range(n):
        for j in range(i,n):
            if lst[i] == lst[j] and i != j:
                a += (lst[j],)
            else:
                continue
    c = a[:-1]
    b = lst[::-1]
    for i in range(len(c)):
        b.remove(c[i])
    d = b[::-1]
    return d

```

### Failed submission real_142.py
```python
def remove_extras(lst):
    for i in range (0, len(lst)):
        for j in range (i + 1, len(lst)):
            if lst[j] == lst[i]:
                lst.pop(j)
                print (lst)
            else:
                continue
            return remove_extras(lst)

```

### Failed submission real_265.py
```python
def remove_extras(lst):
    listt = lst.reverse()
    for element in listt:
        if listt.count(element) > 1:
            listt.remove(element)
    return listt.reverse()

```

### Failed submission real_281.py
```python
def remove_extras(lst):
    new_list = ()
    for x in lst:
        if x not in new_list:
            new_list += ((x))
    return new_list

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
