You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Task: Duplicate elimination
Write a function remove_extras(lst) that takes in a list and returns a new list with all repeated occurrences of any element removed. For example, remove_extras([5, 2, 1, 2, 3]) returns the list [5, 2, 1, 3].

The solution must be a Python function named `remove_extras`.

## Visible test suite (the repairer validates candidates against exactly these)
assert remove_extras([1, 1, 1, 2, 3]) == [1, 2, 3]
assert remove_extras([1, 5, 1, 1, 3, 2]) == [1, 5, 3, 2]
assert remove_extras([]) == []
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]

### Reference solution 1
```python
def remove_extras(lst):
    newlist = []
    for i in lst:
        if i not in newlist:
            newlist.append(i)
    return newlist

```

### Reference solution 2
```python
def remove_extras(lst):
    new=[]
    for i in lst:
        new=new+[i] if i not in new else new
    return new

```

### Reference solution 3
```python
def remove_extras(lst):
    rev_lst=lst.copy()
    rev_lst.reverse()
    ori_len=len(lst)
    new_lst=lst.copy()
    for i in range(ori_len):
        if rev_lst[i] in rev_lst[i+1:]:
            new_lst.pop(ori_len-i-1)
    return new_lst

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: real_053.py)
```python
def remove_extras(lst):
    for num in lst:
        while lst.count(num)>1:
            lst.remove(num)
    return lst

```
### Example buggy submission 2 (id: real_087.py)
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
### Example buggy submission 3 (id: real_142.py)
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
### Example buggy submission 4 (id: real_265.py)
```python
def remove_extras(lst):
    listt = lst.reverse()
    for element in listt:
        if listt.count(element) > 1:
            listt.remove(element)
    return listt.reverse()

```
### Example buggy submission 5 (id: real_281.py)
```python
def remove_extras(lst):
    new_list = ()
    for x in lst:
        if x not in new_list:
            new_list += ((x))
    return new_list

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

`repair` takes a buggy submission (a string containing a definition of `remove_extras`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
