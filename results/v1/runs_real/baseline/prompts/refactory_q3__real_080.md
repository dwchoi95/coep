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
    new_lst = []
    for x in lst:
        if x not in new_lst:
            new_lst += [x]
    return lst

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
