You are an automated program repair system for introductory programming assignments.

## Assignment
Task: Duplicate elimination
Write a function remove_extras(lst) that takes in a list and returns a new list with all repeated occurrences of any element removed. For example, remove_extras([5, 2, 1, 2, 3]) returns the list [5, 2, 1, 3].

The solution must be a Python function named `remove_extras`.

## Visible test suite
assert remove_extras([1, 1, 1, 2, 3]) == [1, 2, 3]
assert remove_extras([1, 5, 1, 1, 3, 2]) == [1, 5, 3, 2]
assert remove_extras([]) == []
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]
assert remove_extras([3, 4, 5, 1, 3]) == [3, 4, 5, 1]

## Buggy student submission
```python
def remove_extras(lst):
    for i in range(len(lst)-1):
        if lst[i] in lst[i+1:]:
            lst.pop(i)
    return lst

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
def remove_extras(lst):
    i = 0
    while i < len(lst)-1:
        if lst[i] in lst[i+1:]:
            lst.pop(i)
        else:
            i += 1
    return lst

```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens).
Output ONLY the complete corrected program in a single ```python code block, nothing else.
