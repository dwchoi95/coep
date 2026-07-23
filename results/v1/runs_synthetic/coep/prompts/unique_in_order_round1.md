You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Write a function with the exact signature `unique_in_order(lst)`. The argument `lst` is a list whose elements are ints and/or strings. Your function must return a NEW list containing the same elements in their original order, except that every run of consecutive equal elements is collapsed to a single copy.

Only adjacent duplicates are removed. If a value appears again later, after a different value has occurred in between, it must be kept again. This is the key difference from removing all duplicates: `[1, 1, 2, 1]` becomes `[1, 2, 1]`, not `[1, 2]`. Elements are compared with ordinary equality (`==`) and comparisons are case-sensitive for strings, so `"A"` and `"a"` are different values. Note that the int `1` and the string `"1"` are different values as well.

Precise edge-case semantics: an empty list returns an empty list `[]`; a one-element list returns a one-element list with that same element; a list where every element is equal returns a single-element list. The value `0` is a normal element and must be kept, so `[0, 0, 0]` returns `[0]`. Do not mutate the input list; build and return a fresh list, and do not sort anything.

Worked examples:
- `unique_in_order([1, 1, 2, 1])` returns `[1, 2, 1]`.
- `unique_in_order(["a", "a", "b", "b", "a"])` returns `["a", "b", "a"]`.
- `unique_in_order([])` returns `[]`.

A good strategy is to walk the list once and append an element only when it differs from the last element you appended.

The solution must be a Python function named `unique_in_order`.

## Visible test suite (the repairer validates candidates against exactly these)
assert unique_in_order([]) == []
assert unique_in_order([1]) == [1]
assert unique_in_order([1, 1]) == [1]
assert unique_in_order([1, 1, 2, 1]) == [1, 2, 1]
assert unique_in_order([1, 2, 3]) == [1, 2, 3]
assert unique_in_order([1, 1, 1, 1]) == [1]
assert unique_in_order(["a", "a", "b", "b", "a"]) == ["a", "b", "a"]
assert unique_in_order([1, "1", 1]) == [1, "1", 1]
assert unique_in_order([2, 2, 2, 3, 3, 1, 1, 2]) == [2, 3, 1, 2]
assert unique_in_order(["A", "a", "A"]) == ["A", "a", "A"]
assert unique_in_order([0, 0, 0]) == [0]
assert unique_in_order([5, 4, 4, 5, 5, 4]) == [5, 4, 5, 4]
assert unique_in_order(["x"]) == ["x"]
assert unique_in_order([1, 2, 2, 3, 3, 3, 4]) == [1, 2, 3, 4]

### Reference solution 1
```python
def unique_in_order(lst):
    result = []
    for x in lst:
        if not result or result[-1] != x:
            result.append(x)
    return result

```

### Reference solution 2
```python
def unique_in_order(lst):
    return [lst[i] for i in range(len(lst)) if i == 0 or lst[i] != lst[i - 1]]

```

### Reference solution 3
```python
def unique_in_order(lst):
    from itertools import groupby
    return [key for key, _ in groupby(lst)]

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_02.py)
```python
def unique_in_order(lst):
    return list(set(lst))

```
### Example buggy submission 2 (id: crafted_09.py)
```python
def unique_in_order(lst):
    result = []
    for i in range(1, len(lst)):
        if lst[i] == lst[i - 1]:
            continue
        result.append(lst[i])
    return result

```
### Example buggy submission 3 (id: mutant_02.py)
```python
def unique_in_order(lst):
    return [lst[i] for i in range(len(lst)) if i != 0 or lst[i] != lst[i - 1]]

```
### Example buggy submission 4 (id: mutant_06.py)
```python
def unique_in_order(lst):
    return [lst[i] for i in range(len(lst)) if i == 1 or lst[i] != lst[i - 1]]

```
### Example buggy submission 5 (id: mutant_14.py)
```python
def unique_in_order(lst):
    result = []
    for x in lst:
        if not result or result[-2] != x:
            result.append(x)
    return result

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

`repair` takes a buggy submission (a string containing a definition of `unique_in_order`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
