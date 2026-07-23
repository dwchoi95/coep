You are an automated program repair system for introductory programming assignments.

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

## Visible test suite
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

## Buggy student submission
```python
def is_palindrome(s):
    t = s.lower()
    return t == t[::-1]

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
