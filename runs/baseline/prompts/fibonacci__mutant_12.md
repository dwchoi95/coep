You are an automated program repair system for introductory programming assignments.

## Assignment
The Fibonacci sequence is defined by two starting values and a simple recurrence: each later term is the sum of the two terms before it.

Write a function with the exact signature `fibonacci(n)` that returns the nth Fibonacci number as an `int`. Use zero-based indexing with these exact base cases: `fibonacci(0)` returns `0` and `fibonacci(1)` returns `1`. For every `n >= 2`, the value is `fibonacci(n - 1) + fibonacci(n - 2)`, so the sequence begins 0, 1, 1, 2, 3, 5, 8, 13, 21, ...

The argument `n` is guaranteed to be an integer with `0 <= n <= 24`, so any correct approach is fast enough: a simple loop that keeps the last two values, a list built bottom-up, plain recursion, or recursion with memoization. Do not print anything and do not read input; just return the value.

Be very careful with the indexing convention. Some textbooks start the sequence at 1, 1; that is NOT the convention here. Off-by-one errors (returning the (n+1)th term, or running the update loop one time too many or too few) are the most common way to fail this assignment, so check the small cases by hand before you submit.

Worked examples:
- `fibonacci(0)` returns `0`.
- `fibonacci(6)` returns `8`, since the sequence runs 0, 1, 1, 2, 3, 5, 8.
- `fibonacci(10)` returns `55`.

If you use a loop with two variables, make sure both are updated simultaneously (for example with tuple assignment), not one after the other.

The solution must be a Python function named `fibonacci`.

## Visible test suite
assert fibonacci(0) == 0
assert fibonacci(1) == 1
assert fibonacci(2) == 1
assert fibonacci(3) == 2
assert fibonacci(4) == 3
assert fibonacci(5) == 5
assert fibonacci(6) == 8
assert fibonacci(7) == 13
assert fibonacci(8) == 21
assert fibonacci(10) == 55
assert fibonacci(12) == 144
assert fibonacci(15) == 610
assert fibonacci(20) == 6765
assert fibonacci(24) == 46368

## Buggy student submission
```python
def fibonacci(n):
    seq = [0, 0]
    while len(seq) <= n:
        seq.append(seq[-1] + seq[-2])
    return seq[n]

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
