You previously wrote the following per-assignment repair module for the assignment "balanced_brackets":

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests
import ast

TESTS = [
    {"args": ["()"], "expected": True},
    {"args": ["([)]"], "expected": False},
    {"args": [""], "expected": True},
    {"args": ["no brackets here!"], "expected": True},
    {"args": ["(a[b]{c})"], "expected": True},
    {"args": ["((("], "expected": False},
    {"args": [")("], "expected": False},
    {"args": ["{[()()]}"], "expected": True},
    {"args": ["([]"], "expected": False},
    {"args": ["())"], "expected": False},
    {"args": ["[(])"], "expected": False},
    {"args": ["{}[]()"], "expected": True},
    {"args": ["([{([{}])}])"], "expected": True},
    {"args": ["]"], "expected": False},
]

def repair(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    
    if not any(isinstance(node, ast.FunctionDef) and node.name == "balanced_brackets" 
               for node in ast.walk(tree)):
        return None
    
    result = failing_tests(source, "balanced_brackets", TESTS)
    
    if result.passed == result.total:
        return None
    
    candidates = candidates_generic(source, max_edits=1, budget=3000)
    found = first_passing(candidates, "balanced_brackets", TESTS, source, max_rps=0.35, max_checks=1000)
    if found:
        return found
    
    candidates = candidates_generic(source, max_edits=2, budget=3000)
    found = first_passing(candidates, "balanced_brackets", TESTS, source, max_rps=0.35, max_checks=1000)
    if found:
        return found
    
    return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_04.py: NOT REPAIRED — no_patch
- crafted_07.py: NOT REPAIRED — no_patch
- mutant_05.py: REPAIRED
- mutant_06.py: REPAIRED
- mutant_15.py: REPAIRED

For reference, the submissions the module failed on:

### Failed submission crafted_04.py
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

### Failed submission crafted_07.py
```python
def balanced_brackets(s):
    t = "".join(c for c in s if c in "()[]{}")
    t = t.replace("()", "").replace("[]", "").replace("{}", "")
    return t == ""

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
