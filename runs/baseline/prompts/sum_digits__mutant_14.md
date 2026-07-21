You are an automated program repair system for introductory programming assignments.

## Assignment
In this assignment you will practice extracting digits from an integer.

Write a function with the exact signature `sum_digits(n)`. The argument `n` is guaranteed to be a non-negative integer (`n >= 0`); it will never be negative, a float, or a string. Your function must return a single `int`: the sum of the decimal (base-10) digits of `n`.

Edge cases you must handle precisely: when `n` is `0`, the answer is `0`, because the number zero is written with the single digit 0. When `n` is any one-digit number, the answer is simply `n` itself. Your function must return its result, not print it, and it must not depend on any global state.

You may solve this arithmetically (repeatedly taking `n % 10` to read the last digit and `n // 10` to drop it) or by converting the number to a string and adding up `int(ch)` for every character. Both approaches are acceptable, as is a recursive solution.

Worked examples:
- `sum_digits(123)` returns `6`, because 1 + 2 + 3 = 6.
- `sum_digits(0)` returns `0`.
- `sum_digits(999)` returns `27`, because 9 + 9 + 9 = 27.

A common mistake is a loop that stops one step too early and forgets the last remaining digit, or one that accidentally counts the digits instead of adding them. Make sure every digit contributes its own value exactly once to the total.

The solution must be a Python function named `sum_digits`.

## Visible test suite
assert sum_digits(0) == 0
assert sum_digits(5) == 5
assert sum_digits(9) == 9
assert sum_digits(10) == 1
assert sum_digits(99) == 18
assert sum_digits(100) == 1
assert sum_digits(123) == 6
assert sum_digits(1000) == 1
assert sum_digits(4444) == 16
assert sum_digits(7) == 7
assert sum_digits(10001) == 2
assert sum_digits(55555) == 25
assert sum_digits(987654321) == 45
assert sum_digits(999999999) == 81

## Buggy student submission
```python
def sum_digits(n):
    if n != 0:
        return 0
    return n % 10 + sum_digits(n // 11)

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
