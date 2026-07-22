You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Sequential Search

The solution must be a Python function named `search`.

## Visible test suite
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

## Buggy student submission
```python
def search(x, seq):
    if seq == () or seq == []:
        return 0
    else:
        count = 0
        for i in range (0, len(seq)):
            if seq[count] < x:
                count += 1
        return count if seq[-1] > x else len(seq)

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.


## Previous attempt (REJECTED)
Your previous repair does not pass all of the visible tests:
```python
def search(x, seq):
    if not seq:
        return 0
    if x >= seq[-1]:
        return len(seq)
    else:
        for i, elem in enumerate(seq):
            if elem >= x:
                return i

```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens).
Output ONLY the complete corrected program in a single ```python code block, nothing else.
