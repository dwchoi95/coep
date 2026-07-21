You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Write a function with the exact signature `def flatten(nested):` that takes a list `nested` whose elements are either integers or lists that themselves contain integers or further nested lists, to any depth. The function must return a new flat list containing every integer that appears anywhere inside `nested`, in left-to-right order, exactly as the integers would be encountered when reading the structure from left to right at every level.

Edge-case semantics you must get right: an empty input list produces an empty result, so `flatten([]) == []`. Empty sublists contribute nothing but must not cause errors; for example `flatten([1, [], 2]) == [1, 2]`. Nesting can be arbitrarily deep, so a value wrapped in many layers of lists, such as `[[[[1]]]]`, still yields just `[1]`. The integers themselves may be zero or negative and must be preserved exactly. Do not mutate the input list, do not sort the result, and do not remove duplicates -- every integer occurrence must appear in the output exactly once per occurrence, in order.

Worked examples:
- `flatten([1, [2, 3]])` returns `[1, 2, 3]`.
- `flatten([[1, 2], [3, [4]], 5])` returns `[1, 2, 3, 4, 5]`.
- `flatten([[[[1]]]])` returns `[1]`.

You may solve this with recursion, an explicit stack, or repeated single-level flattening passes; use `isinstance(item, list)` to decide whether an element needs further flattening. Only the standard library is allowed.

The solution must be a Python function named `flatten`.

## Visible test suite (the repairer validates candidates against exactly these)
assert flatten([]) == []
assert flatten([1, 2, 3]) == [1, 2, 3]
assert flatten([1, [2, 3]]) == [1, 2, 3]
assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]
assert flatten([[[[1]]]]) == [1]
assert flatten([1, [2, [3, [4, [5]]]]]) == [1, 2, 3, 4, 5]
assert flatten([[], [], []]) == []
assert flatten([0]) == [0]
assert flatten([1, [], 2]) == [1, 2]
assert flatten([[1], [2], 3, [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]
assert flatten([-1, [-2, [-3]]]) == [-1, -2, -3]
assert flatten([[[]], [[[]]], 5]) == [5]
assert flatten([10, [20], [30, [40]], 50]) == [10, 20, 30, 40, 50]
assert flatten([[1, [2]], 3]) == [1, 2, 3]

### Reference solution 1
```python
def flatten(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result

```

### Reference solution 2
```python
def flatten(nested):
    result = []
    stack = list(reversed(nested))
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(reversed(item))
        else:
            result.append(item)
    return result

```

### Reference solution 3
```python
def flatten(nested):
    flat = list(nested)
    while any(isinstance(x, list) for x in flat):
        nxt = []
        for x in flat:
            if isinstance(x, list):
                nxt.extend(x)
            else:
                nxt.append(x)
        flat = nxt
    return flat

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_02.py)
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
### Example buggy submission 2 (id: crafted_08.py)
```python
def flatten(nested):
    total = []
    for item in nested:
        total.extend(item)
    return total

```
### Example buggy submission 3 (id: mutant_01.py)
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
### Example buggy submission 4 (id: mutant_03.py)
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
### Example buggy submission 5 (id: mutant_04.py)
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

`repair` takes a buggy submission (a string containing a definition of `flatten`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
