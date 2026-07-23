You are an automated program repair system for introductory programming assignments.

## Assignment
Implement a function `search_insert(lst, x)` that determines where a value would be inserted into a sorted list.

The parameter `lst` is a list of integers sorted in ascending order; it may be empty and it may contain duplicate values. The parameter `x` is an integer. Your function must return the leftmost index at which `x` could be inserted so that `lst` would remain sorted in ascending order. Equivalently, the answer is the number of elements of `lst` that are strictly smaller than `x` (this matches the behaviour of `bisect.bisect_left` from the standard library).

Precise semantics:
- If `lst` is empty, return `0`.
- If `x` is smaller than or equal to every element, return `0`.
- If `x` is larger than every element, return `len(lst)`.
- If `x` already occurs in `lst`, return the index of its first occurrence, not any later one.

Worked examples:
- `search_insert([1, 3, 5, 7], 5)` returns `2` because 5 is already at index 2.
- `search_insert([1, 3, 5, 7], 4)` returns `2` because inserting 4 at index 2 keeps the list sorted.
- `search_insert([2, 2, 2, 2], 2)` returns `0`, the leftmost valid position.

Do not modify `lst`; just return the index. Any correct strategy (linear scan, binary search, counting) is acceptable.

The solution must be a Python function named `search_insert`.

## Visible test suite
assert search_insert([1, 3, 5, 7], 5) == 2
assert search_insert([1, 3, 5, 7], 4) == 2
assert search_insert([1, 3, 5, 7], 0) == 0
assert search_insert([1, 3, 5, 7], 8) == 4
assert search_insert([], 4) == 0
assert search_insert([2, 2, 2, 2], 2) == 0
assert search_insert([1, 2, 2, 3], 2) == 1
assert search_insert([10], 10) == 0
assert search_insert([10], 5) == 0
assert search_insert([10], 15) == 1
assert search_insert([1, 1, 2, 3, 3, 3, 4], 3) == 3
assert search_insert([-5, -2, 0, 3], -2) == 1
assert search_insert([1, 3, 5, 7], 1) == 0
assert search_insert([1, 3, 5, 7], 7) == 3

## Buggy student submission
```python
def search_insert(lst, x):
    for i in range(len(lst) - 1, -1, -1):
        if lst[i] < x:
            return i
    return 0

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
