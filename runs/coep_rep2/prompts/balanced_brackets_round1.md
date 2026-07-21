You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

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

## Visible test suite (the repairer validates candidates against exactly these)
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

### Reference solution 1
```python
def balanced_brackets(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for c in s:
        if c in "([{":
            stack.append(c)
        elif c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return False
    return not stack

```

### Reference solution 2
```python
def balanced_brackets(s):
    t = "".join(c for c in s if c in "()[]{}")
    while True:
        reduced = t.replace("()", "").replace("[]", "").replace("{}", "")
        if reduced == t:
            return t == ""
        t = reduced

```

### Reference solution 3
```python
def balanced_brackets(s):
    br = [c for c in s if c in "()[]{}"]
    closing = {"(": ")", "[": "]", "{": "}"}

    def parse(i):
        while i < len(br) and br[i] in closing:
            want = closing[br[i]]
            i = parse(i + 1)
            if i is None or i >= len(br) or br[i] != want:
                return None
            i += 1
        return i

    return parse(0) == len(br)

```

## Sample buggy student submissions (from past semesters)
### Example buggy submission 1 (id: crafted_04.py)
```python
def balanced_brackets(s):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for c in s:
        if c in "([{":
            stack.append(c)
        elif c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return False
    return True

```
### Example buggy submission 2 (id: crafted_07.py)
```python
def balanced_brackets(s):
    t = "".join(c for c in s if c in "()[]{}")
    t = t.replace("()", "").replace("[]", "").replace("{}", "")
    return t == ""

```
### Example buggy submission 3 (id: mutant_05.py)
```python
def balanced_brackets(s):
    br = [c for c in s if c in '()[]{}']
    closing = {'(': ')', '[': ']', '{': '}'}

    def parse(i):
        while i < len(br) or br[i] in closing:
            want = closing[br[i]]
            i = parse(i + 1)
            if i is None or i >= len(br) or br[i + 1] != want:
                return None
            i += 1
        return i
    return parse(0) == len(br)

```
### Example buggy submission 4 (id: mutant_06.py)
```python
def balanced_brackets(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for c in s:
        if c in '([{':
            stack.append(c)
        elif c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return True
    return not stack

```
### Example buggy submission 5 (id: mutant_15.py)
```python
def balanced_brackets(s):
    br = [c for c in s if c in '()[]{}']
    closing = {'(': ')', '[': ']', '{': '}'}

    def parse(i):
        while i < len(br) and br[i] in closing:
            want = closing[br[i]]
            i = parse(i + 1)
            if i is None or i >= len(br) or br[i] != want:
                return None
            i += 2
        return i
    return parse(0) == len(br)

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

`repair` takes a buggy submission (a string containing a definition of `balanced_brackets`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{"args": [...], "expected": ...}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
