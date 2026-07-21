You are an automated program repair system for introductory programming assignments.

## Assignment
In this assignment you will implement a function that selects the largest values from a list.

Write a function with the signature `top_k(lst, k)`. The parameter `lst` is a list of integers (possibly empty, possibly containing duplicates and negative numbers) and `k` is a non-negative integer. The function must return a new list containing the `k` largest elements of `lst`, arranged in descending order (largest first).

Precise semantics you must follow:
- If `k` is 0, return the empty list `[]`.
- If `k` is greater than or equal to `len(lst)`, return all of the elements of `lst` sorted in descending order.
- Duplicate values count separately: each occurrence in `lst` is an element in its own right, so duplicates may appear in the result.
- The returned list must be sorted from largest to smallest, even when `lst` itself is unsorted.

Worked examples:
- `top_k([3, 1, 2], 2)` returns `[3, 2]`.
- `top_k([5, 5, 1], 2)` returns `[5, 5]` (the duplicate 5 is kept).
- `top_k([1, 2], 5)` returns `[2, 1]` because `k` exceeds the length of the list.

You may use any approach you like (sorting, repeated selection, a heap, and so on). Do not print anything; return the list.

The solution must be a Python function named `top_k`.

## Visible test suite
assert top_k([5, 5, 1], 2) == [5, 5]
assert top_k([3, 1, 2], 2) == [3, 2]
assert top_k([1, 2, 3, 4, 5], 3) == [5, 4, 3]
assert top_k([], 0) == []
assert top_k([], 3) == []
assert top_k([7], 1) == [7]
assert top_k([4, 2], 0) == []
assert top_k([1, 2], 5) == [2, 1]
assert top_k([-1, -5, -3], 2) == [-1, -3]
assert top_k([10, 10, 10], 2) == [10, 10]
assert top_k([0, -1, 1], 3) == [1, 0, -1]
assert top_k([2, 8, 6, 4, 9, 1], 4) == [9, 8, 6, 4]
assert top_k([5, 3, 5, 3, 5], 3) == [5, 5, 5]
assert top_k([100], 0) == []

## Buggy student submission
```python
import heapq

def top_k(lst, k):
    return heapq.nlargest(lst, k)

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
