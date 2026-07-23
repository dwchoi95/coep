You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Task: Sequential Search

The solution must be a Python function named `search`.

## Visible test suite (the repairer validates candidates against exactly these)
assert search(42, [-5, 1, 3, 5, 7, 10]) == 6
assert search(42, [1, 5, 10]) == 3
assert search(5, [1, 5, 10]) == 1
assert search(7, [1, 5, 10]) == 2
assert search(3, [1, 5, 10]) == 1
assert search(-5, [1, 5, 10]) == 0
assert search(10, [-5, -1, 3, 5, 7, 10]) == 5
assert search(-100, [-5, -1, 3, 5, 7, 10]) == 0
assert search(0, [-5, -1, 3, 5, 7, 10]) == 2
assert search(100, []) == 0
assert search(-100, []) == 0

### Reference solution 1
```python
def search(x, seq):
    for i in range(len(seq)):
        if x <= seq[i]:
            return i
    return len(seq)
```

### Reference solution 2
```python
def search(x, seq):
    i=0
    while i<len(seq):
        if x<=seq[i]:
            return i
        else:
            i+=1
    return len(seq)

```

### Reference solution 3
```python
def search(x, seq):
    n = len(seq)
    for i in range(n):
        next_element = seq[i]
        if x <= next_element:
            return i
    return n


```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: real_008.py)
```python
def search(x, seq):
    if seq == () or seq == []:
        return 0
    elif x <= seq[0]:
        return 0
    elif x >= seq[-1]:
        return len(seq) - 1
    else:
        seq_enum = [i for i in enumerate(seq)]
        for j in range(len(seq_enum) - 1):
            if x >= seq_enum[j][1] and x <= seq_enum[j+1][1]:
                return j+1

```
### Example buggy submission 2 (id: real_099.py)
```python
def search(x, seq):
    for i in range (len(seq)):
        if x < seq[i]:
            return i
        elif x ==seq[i]:
            return i
        else:
            continue
    return i + 1

```
### Example buggy submission 3 (id: real_219.py)
```python
def search(x, seq):
    for i, elem in enumerate(seq):
        if x <= elem:
            return i
        elif i == len(seq) - 1 and x > elem:
            return i + 1

```
### Example buggy submission 4 (id: real_362.py)
```python
def search(x, seq):
    if len(seq)==0:
        return 0
    else:
        if x <= seq[0]:
            return 0
        elif x >= seq[-1]:
            return len(seq)
        else:
            for i in range(0, len(seq)-1):
                if seq[i] <= x <= seq[i+1]:
                    return i+1

```
### Example buggy submission 5 (id: real_384.py)
```python
def search(x, seq):
    for i in range(len(seq)):
        if seq[i] < x:
            continue
        elif seq[len(seq)-1] < x:
            return len(seq)-1
        else:
            return i
    """ Takes in a value x and a sorted sequence seq, and returns the
    position that x should go to such that the sequence remains sorted """

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

`repair` takes a buggy submission (a string containing a definition of `search`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
