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
    results = []
    counter = 0
    while counter < k:
        for i in range(-len(lst),0):
            if lst[i] == max(lst):
                results.append(lst.pop(i))
                counter += 1
        continue
    return results

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
