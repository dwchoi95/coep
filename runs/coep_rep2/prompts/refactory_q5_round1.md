You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Task: Top-K
Write a function top_k that accepts a list of integers as the input and returns the greatest k number of values as a list, with its elements sorted in descending order. You may use any sorting algorithm you wish, but you are not allowed to use sort and sorted.

The solution must be a Python function named `top_k`.

## Visible test suite (the repairer validates candidates against exactly these)
assert top_k([9, 9, 4, 9, 7, 9, 3, 1, 6], 5) == [9, 9, 9, 9, 7]
assert top_k([9, 8, 4, 5, 7, 2, 3, 1, 6], 5) == [9, 8, 7, 6, 5]
assert top_k([4, 5, 2, 3, 1, 6], 6) == [6, 5, 4, 3, 2, 1]
assert top_k([4, 5, 2, 3, 1, 6], 3) == [6, 5, 4]
assert top_k([4, 5, 2, 3, 1, 6], 0) == []

### Reference solution 1
```python
def top_k(lst, k):
    ls = []
    for i in range(k):
        ls.append(max(lst))
        lst.remove(max(lst))
    return ls
```

### Reference solution 2
```python
def top_k(lst, k):
    n= []
    while lst:
        big = lst[0]
        for ele in lst:
            if ele>big:
                big = ele
        if len(n)==k:
            break 
        else:
            n.append(big)
            lst.remove(big)
    return n
        
                
    
    pass

```

### Reference solution 3
```python
def top_k(lst, k):
    count=0
    newlst=[]
    while lst:
        newlst+=[max(lst)]
        lst.remove(max(lst))
    for i in range(k):
        lst.append(newlst[i])
    return lst

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: real_011.py)
```python
def sort_age(lst):
        new=[]
        while lst !=[]:
            big=lst[0]
            for i in lst:
                if i[1]>big[1]:
                    big=i
            lst.remove(big)
            new.append(big)
        return new
def top_k(lst, k):
    return sort_age(lst)[:k]
    pass

```
### Example buggy submission 2 (id: real_016.py)
```python
def top_k(lst, k):
    
    if lst == []:
        return lst
    
    lower = []
    higher = []
    plist = []
    
    pivot = lst[0]
    for e in lst:
        if e < pivot:
            lower.append(e)
        if e == pivot:
            plist.append(e)
        if e > pivot:
            higher.append(e)
    sort_list = lower + plist + higher
    sort_list = sort_list[::-1]
    
    if k == len(lst):
        return sort_list[:k-1]
    elif k > len(lst):
        return sort_list
    else:
        return sort_list[:k]

```
### Example buggy submission 3 (id: real_030.py)
```python
def top_k(lst, k):
    sort, output = [], []
    while lst:
        largest = lst[0]
        for i in lst:
            if i > largest:
                largest = i
        lst.remove(largest)
        sort.append(largest)
    for j in sort:
        output.append(j)
        if len(output) == k:
            break
    return output    

```
### Example buggy submission 4 (id: real_070.py)
```python
def top_k(lst, k):
    new = []
    while len(lst) > len(lst) - k:
        new.append(lst.remove(max(lst)))
        
    return new
        

```
### Example buggy submission 5 (id: real_081.py)
```python
def top_k(lst, k):
    sotsot = []
    while lst:
        while len(sotsot) <=k:
            sotsot.append(max(lst))
            lst.remove(max(lst)) #wont return u any value just modified the list only.
        return sotsot 
    

```

## Helper library
You may use the helper library `coep.repairlib` (importable as shown):

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
```

- `candidates_generic(source, max_edits=1, budget=2000)` -> iterator of candidate
  programs obtained by small semantic edits at every applicable AST site
  (comparison/arithmetic/boolean operator swaps, integer off-by-one,
  boolean-constant flips, index shifts, argument swaps). `max_edits=2`
  enumerates pairs of edits (much larger; use a budget).
- `first_passing(candidates, entry, tests, original, max_rps=0.35, max_checks=800)`
  -> the first candidate passing ALL tests whose relative patch size vs the
  original is <= max_rps, else None. Each test is {"args": [...], "expected": ...}.
- `failing_tests(source, entry, tests)` -> RunResult with `.compiled`,
  `.passed`, `.total`, `.failures` (list of {index, args, expected, got, error}),
  useful for dispatching on the observed failure pattern.
- `rps(buggy, patched)` -> token-level relative patch size.
- `chain(gen1, gen2, ...)` -> compose candidate generators in priority order.
- Standard library (`ast`, `re`, `itertools`, ...) is fully available.


## Your task
Write a Python module that defines:

```python
def repair(source: str) -> str | None:
    ...
```

`repair` takes a buggy submission (a string containing a definition of `top_k`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
