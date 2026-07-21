You are an automated program repair system for introductory programming assignments.

## Assignment
Write a function with the exact signature `def grade_stats(scores):` that computes summary statistics for a list of exam scores. The argument `scores` is guaranteed to be a non-empty list of numbers; each element may be an `int` or a `float`, and scores may be negative (for example, after a penalty adjustment). The function must return a list of exactly three values, in this order: `[minimum, maximum, mean]`.

Precise requirements: the minimum and maximum are the smallest and largest values in the list, returned with their original numeric type (do not convert an integer minimum to a float). The mean is the arithmetic average, `sum of scores divided by number of scores`, computed with true division and then rounded to exactly 2 decimal places using Python's built-in `round(value, 2)`. Do not truncate, do not use integer division, and do not round to a different precision. A single-element list is valid input: its minimum, maximum, and mean are all that one score. Do not assume the list is sorted, and do not modify the input list.

Worked examples:
- `grade_stats([70, 80, 90])` returns `[70, 90, 80.0]`.
- `grade_stats([1, 2, 4])` returns `[1, 4, 2.33]`, since 7 / 3 = 2.333... rounds to 2.33.
- `grade_stats([100])` returns `[100, 100, 100.0]`.

Your function will be tested with unsorted lists, all-negative lists, single-element lists, and means that require rounding.

The solution must be a Python function named `grade_stats`.

## Visible test suite
assert grade_stats([70, 80, 90]) == [70, 90, 80.0]
assert grade_stats([100]) == [100, 100, 100.0]
assert grade_stats([50.5, 60.5]) == [50.5, 60.5, 55.5]
assert grade_stats([-10, 0, 10]) == [-10, 10, 0.0]
assert grade_stats([1, 2]) == [1, 2, 1.5]
assert grade_stats([1, 2, 3]) == [1, 3, 2.0]
assert grade_stats([0, 0, 0]) == [0, 0, 0.0]
assert grade_stats([59.9, 60.1, 60.0]) == [59.9, 60.1, 60.0]
assert grade_stats([85, 92, 78, 95, 88]) == [78, 95, 87.6]
assert grade_stats([1, 2, 4]) == [1, 4, 2.33]
assert grade_stats([-5, -15, -10]) == [-15, -5, -10.0]
assert grade_stats([2.675, 2.675]) == [2.675, 2.675, 2.67]
assert grade_stats([0.1, 0.2, 0.3]) == [0.1, 0.3, 0.2]
assert grade_stats([10, 20, 30, 40]) == [10, 40, 25.0]

## Buggy student submission
```python
def grade_stats(scores):
    return [min(scores), max(scores), round(sum(scores) / len(scores), 1)]

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
