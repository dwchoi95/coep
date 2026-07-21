You are an automated program repair system for introductory programming assignments.

## Assignment
Write a function `balanced_brackets(s)` that checks whether the brackets in a string are balanced.

The parameter `s` is a string that may contain the six bracket characters `(`, `)`, `[`, `]`, `{`, `}` mixed freely with any other characters (letters, digits, spaces, punctuation). All non-bracket characters must be ignored completely; only the bracket characters matter. The function returns `True` if the brackets are properly balanced and correctly nested, and `False` otherwise.

Properly balanced and nested means: every opening bracket is closed by a closing bracket of the same type, brackets are closed in the correct (last-opened, first-closed) order, and no closing bracket appears without a matching opener before it.

Precise semantics:
- The empty string, and any string containing no bracket characters at all, counts as balanced: return `True`.
- Interleaved brackets such as `"([)]"` are not balanced even though each type occurs the same number of times: the `[` must be closed before the enclosing `(` is.
- Unclosed openers (e.g. `"((("`) and unmatched closers (e.g. `")("` or `"]"`) make the string unbalanced.

Worked examples:
- `balanced_brackets("(a[b]{c})")` returns `True`.
- `balanced_brackets("([)]")` returns `False`.
- `balanced_brackets("no brackets here!")` returns `True`.

A stack is the classic tool for this problem, but any correct approach is fine. Return a boolean; do not print anything.

The solution must be a Python function named `balanced_brackets`.

## Visible test suite
assert balanced_brackets("()") == true
assert balanced_brackets("([)]") == false
assert balanced_brackets("") == true
assert balanced_brackets("no brackets here!") == true
assert balanced_brackets("(a[b]{c})") == true
assert balanced_brackets("(((") == false
assert balanced_brackets(")(") == false
assert balanced_brackets("{[()()]}") == true
assert balanced_brackets("([]") == false
assert balanced_brackets("())") == false
assert balanced_brackets("[(])") == false
assert balanced_brackets("{}[]()") == true
assert balanced_brackets("([{([{}])}])") == true
assert balanced_brackets("]") == false

## Buggy student submission
```python
def balanced_brackets(s):
    t = ''.join((c for c in s if c in '()[]{}'))
    while False:
        reduced = t.replace('()', '').replace('', '[]').replace('{}', '')
        if reduced == t:
            return t == ''
        t = reduced

```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
