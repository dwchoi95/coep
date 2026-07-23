You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Top-K
Write a function top_k that accepts a list of integers as the input and returns the greatest k number of values as a list, with its elements sorted in descending order. You may use any sorting algorithm you wish, but you are not allowed to use sort and sorted.

The solution must be a Python function named `top_k`.

## Visible test suite
assert top_k([9, 9, 4, 9, 7, 9, 3, 1, 6], 5) == [9, 9, 9, 9, 7]
assert top_k([9, 8, 4, 5, 7, 2, 3, 1, 6], 5) == [9, 8, 7, 6, 5]
assert top_k([4, 5, 2, 3, 1, 6], 6) == [6, 5, 4, 3, 2, 1]
assert top_k([4, 5, 2, 3, 1, 6], 3) == [6, 5, 4]
assert top_k([4, 5, 2, 3, 1, 6], 0) == []

## Buggy student submission
```python
def top_k(lst, k):
    lst2 = []
    max = lst[0]
    for i in lst:
        if i > max:
            max = i
        lst.pop(max)
        while len(lst2) != k:
            lst2.append(max)
    return lst2

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.


## Previous attempt (REJECTED)
Your previous repair passes the tests but changes 38% of the program's tokens, exceeding the 35% relative-patch-size limit. It rewrites too much of the student's approach:
```python
def top_k(lst, k):
    lst2 = []
    for _ in range(k):
        if lst:
            max = lst[0]
            for i in lst:
                if i > max:
                    max = i
            lst.remove(max)
            lst2.append(max)
    return lst2

```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens).
Output ONLY the complete corrected program in a single ```python code block, nothing else.
