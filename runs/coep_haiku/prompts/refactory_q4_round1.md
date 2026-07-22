You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Task: Sorting Tuples
Can we sort items other than integers? For this question, you will be sorting tuples! We represent a person using a tuple (<gender>, <age>). Given a list of people, write a function sort_age that sorts the people and return a list in an order such that the older people are at the front of the list. An example of the list of people is [("M", 23), ("F", 19), ("M", 30)]. The sorted list would look like [("M", 30), ("M", 23), ("F", 19)]. You may assume that no two members in the list of people are of the same age.

The solution must be a Python function named `sort_age`.

## Visible test suite (the repairer validates candidates against exactly these)
assert sort_age([["F", 19]]) == [["F", 19]]
assert sort_age([["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) == [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]
assert sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]) == [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]
assert sort_age([["F", 18], ["M", 23], ["F", 19], ["M", 30]]) == [["M", 30], ["M", 23], ["F", 19], ["F", 18]]
assert sort_age([["M", 23], ["F", 19], ["M", 30]]) == [["M", 30], ["M", 23], ["F", 19]]
assert sort_age([]) == []

### Reference solution 1
```python
def sort_age(lst):
    for i in range(0, len(lst)-1):
        for j in range(i+1, len(lst)):
            if lst[i][1] < lst[j][1]:
                tmp = lst[i]
                lst[i] = lst[j]
                lst[j] = tmp
    return lst
```

### Reference solution 2
```python
def sort_age(lst):
	sort = []
	while lst:
		largest = lst[0]
		for element in lst:
			if element[1] > largest[1]:
				largest = element
		lst.remove(largest)
		sort.append(largest)
	return sort

```

### Reference solution 3
```python
def sort_age(lst):
    new = []
    while lst:
        eldest = lst[0]
        for i in lst:
            if i[1] > eldest[1]:
                eldest = i 
        lst.remove(eldest)
        new.append(eldest)
    return new

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: real_146.py)
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
### Example buggy submission 2 (id: real_186.py)
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
### Example buggy submission 3 (id: real_202.py)
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
### Example buggy submission 4 (id: real_334.py)
```python
def sort_age(lst):
    for i in range(1,len(lst)):
        while lst[i][1]<lst[i-1][1]:
            lst.pop(i)
            lst.insert(i-1,lst[i])# Fill in your code here
    return lst.reverse()

```
### Example buggy submission 5 (id: real_344.py)
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

`repair` takes a buggy submission (a string containing a definition of `sort_age`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
