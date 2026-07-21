You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
Write a function with the exact signature `is_palindrome(s)` that decides whether the string `s` reads the same forwards and backwards, using relaxed, human-friendly rules.

The comparison must ignore letter case and must ignore every character that is not alphanumeric. Concretely: first keep only the characters `c` for which `c.isalnum()` is true (letters and digits; spaces, punctuation, apostrophes and so on are all discarded), then lowercase what remains, and finally test whether that cleaned string equals its own reverse. Return the boolean `True` if it does and `False` otherwise. Return a real `bool`, do not print anything.

Precise edge-case semantics: the empty string is a palindrome, so `is_palindrome("")` must return `True`. Likewise, if `s` contains no alphanumeric characters at all (for example `"!!!"` or `", , ,"`), the cleaned string is empty and the answer is `True`. A single alphanumeric character is always a palindrome. Digits are compared as ordinary characters, so `"0P"` cleans to `"0p"`, which is not a palindrome.

Worked examples:
- `is_palindrome("A man, a plan, a canal: Panama")` returns `True`, because the cleaned string is `"amanaplanacanalpanama"`.
- `is_palindrome("race a car")` returns `False`, because `"raceacar"` reversed is `"racaecar"`.
- `is_palindrome("No 'x' in Nixon")` returns `True`.

Remember to apply both normalization steps; forgetting either the case fold or the filtering is the most common source of wrong answers.

The solution must be a Python function named `is_palindrome`.

## Visible test suite (the repairer validates candidates against exactly these)
assert is_palindrome("") == true
assert is_palindrome("a") == true
assert is_palindrome("abba") == true
assert is_palindrome("abc") == false
assert is_palindrome("A man, a plan, a canal: Panama") == true
assert is_palindrome("race a car") == false
assert is_palindrome("No 'x' in Nixon") == true
assert is_palindrome("12321") == true
assert is_palindrome("1231") == false
assert is_palindrome("!!!") == true
assert is_palindrome("Aa") == true
assert is_palindrome("0P") == false
assert is_palindrome("Was it a car or a cat I saw?") == true
assert is_palindrome("ab") == false

### Reference solution 1
```python
def is_palindrome(s):
    chars = [c.lower() for c in s if c.isalnum()]
    i, j = 0, len(chars) - 1
    while i < j:
        if chars[i] != chars[j]:
            return False
        i += 1
        j -= 1
    return True

```

### Reference solution 2
```python
def is_palindrome(s):
    t = "".join(c for c in s.lower() if c.isalnum())
    return t == t[::-1]

```

### Reference solution 3
```python
def is_palindrome(s):
    def check(i, j):
        if i >= j:
            return True
        if not s[i].isalnum():
            return check(i + 1, j)
        if not s[j].isalnum():
            return check(i, j - 1)
        if s[i].lower() != s[j].lower():
            return False
        return check(i + 1, j - 1)
    return check(0, len(s) - 1)

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_03.py)
```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalpha())
    return t == t[::-1]

```
### Example buggy submission 2 (id: crafted_10.py)
```python
def is_palindrome(s):
    t = "".join(c.lower() for c in s if c.isalnum())
    half = len(t) // 2
    return t[:half] == t[half:]

```
### Example buggy submission 3 (id: mutant_01.py)
```python
def is_palindrome(s):
    t = ''.join((c for c in s.lower() if c.isalnum()))
    return t != t[::-1]

```
### Example buggy submission 4 (id: mutant_06.py)
```python
def is_palindrome(s):
    chars = [c.lower() for c in s if c.isalnum()]
    i, j = (0, len(chars) - 1)
    while i < j:
        if chars[i] != chars[j]:
            return False
        i += 0
        j -= 1
    return True

```
### Example buggy submission 5 (id: mutant_08.py)
```python
def is_palindrome(s):
    chars = [c.lower() for c in s if c.isalnum()]
    i, j = (1, len(chars) - 2)
    while i < j:
        if chars[i] != chars[j]:
            return False
        i += 1
        j -= 1
    return True

```

## Helper library
You may use the helper library `coep.repairlib` (importable as shown):

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
```

- `candidates_generic(source, max_edits=1, budget=2000)` -> iterator of candidate
  programs obtained by small semantic edits at every applicable AST site
  (comparison/arithmetic/boolean operator swaps, integer off-by-one,
  boolean-constant flips, index shifts, argument swaps). `max_edits=2`
  enumerates pairs of edits (much larger; use a budget).
- `first_passing(candidates, entry, tests, original, max_rps=0.35, max_checks=800)`
  -> the first candidate passing ALL tests whose relative patch size vs the
  original is <= max_rps, else None. Each test is {"args": [...], "expected": ...}.
- `failing_tests(source, entry, tests)` -> RunResult with `.compiled`,
  `.passed`, `.total`, `.failures` (list of {index, args, expected, got, error}),
  useful for dispatching on the observed failure pattern.
- `rps(buggy, patched)` -> token-level relative patch size.
- `chain(gen1, gen2, ...)` -> compose candidate generators in priority order.
- Standard library (`ast`, `re`, `itertools`, ...) is fully available.


## Your task
Write a Python module that defines:

```python
def repair(source: str) -> str | None:
    ...
```

`repair` takes a buggy submission (a string containing a definition of `is_palindrome`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
