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
    """ Takes in a value x and a sorted sequence seq, and returns the
    position that x should go to such that the sequence remains sorted """
    counter = -1
    for i in seq:
        if len(seq) == 0:
            return 0
        elif x <= i:
            counter += 1
            return counter
        else:
            counter += 1
    if x > seq[counter]:
        return counter + 1

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.


## Previous attempt (REJECTED)
Your previous repair passes the tests but changes 36% of the program's tokens, exceeding the 35% relative-patch-size limit. It rewrites too much of the student's approach:
```python
def search(x, seq):
    if len(seq) == 0:
        return 0
    counter = -1
    for i in seq:
        if x <= i:
            counter += 1
            return counter
        else:
            counter += 1
    if x > seq[counter]:
        return counter + 1

```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens).
Output ONLY the complete corrected program in a single ```python code block, nothing else.
