You are an automated program repair system for introductory programming assignments.

## Assignment
In this assignment you will implement the classic greatest common divisor function. Write a function with the exact signature `def gcd(a, b):` where `a` and `b` are non-negative integers. The greatest common divisor of two integers is the largest integer that divides both of them with no remainder. Your function must return this value as an integer.

Pay careful attention to the edge cases involving zero. By mathematical convention, every integer divides zero, so the greatest common divisor of zero and any positive integer `x` is `x` itself: `gcd(0, x) == x` and `gcd(x, 0) == x`. When both arguments are zero, your function must return 0, i.e. `gcd(0, 0) == 0`. Your solution should handle arguments in either order, since `gcd(a, b)` always equals `gcd(b, a)`. You must implement the algorithm yourself; do not call `math.gcd`. Any correct approach is acceptable (the Euclidean algorithm with the modulo operator is recommended, but repeated subtraction or trial division also work if they handle zeros correctly).

Worked examples:
- `gcd(48, 18)` returns `6`, because 6 divides both 48 and 18 and no larger integer does.
- `gcd(7, 7)` returns `7`, since every integer divides itself.
- `gcd(0, 5)` returns `5`, by the zero convention described above.

Your function will be tested on small and large inputs, including coprime pairs (where the answer is 1) and pairs where one argument evenly divides the other.

The solution must be a Python function named `gcd`.

## Visible test suite
assert gcd(48, 18) == 6
assert gcd(18, 48) == 6
assert gcd(0, 5) == 5
assert gcd(5, 0) == 5
assert gcd(0, 0) == 0
assert gcd(7, 7) == 7
assert gcd(1, 999) == 1
assert gcd(12, 8) == 4
assert gcd(100, 75) == 25
assert gcd(13, 17) == 1
assert gcd(270, 192) == 6
assert gcd(1000000, 999999) == 1
assert gcd(36, 60) == 12
assert gcd(2, 4) == 2

## Buggy student submission
```python
def gcd(a, b):
    if a != 0:
        return b
    if b == 0:
        return a
    while a == b:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
