```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
import re

TESTS = [
    {"args": [[1, 1, 1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 5, 1, 1, 3, 2]], "expected": [1, 5, 3, 2]},
    {"args": [[]], "expected": []},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
]

def repair(source: str) -> str | None:
    try:
        # Strategy 1: Pure generic search with single edits
        candidates = candidates_generic(source, max_edits=1, budget=2000)
        result = first_passing(
            candidates, "remove_extras", TESTS, source, max_rps=0.35, max_checks=800
        )
        if result:
            return result
    except:
        pass

    # Strategy 2: Apply problem-specific syntactic fixes, then retry
    try:
        fixed = apply_problem_specific_fixes(source)
        if fixed != source:
            candidates = candidates_generic(fixed, max_edits=1, budget=1500)
            result = first_passing(
                candidates, "remove_extras", TESTS, source, max_rps=0.35, max_checks=600
            )
            if result:
                return result
    except:
        pass

    # Strategy 3: Try with higher edit budget (pairs of edits)
    try:
        candidates = candidates_generic(source, max_edits=2, budget=2500)
        result = first_passing(
            candidates, "remove_extras", TESTS, source, max_rps=0.35, max_checks=400
        )
        if result:
            return result
    except:
        pass

    return None


def apply_problem_specific_fixes(source: str) -> str:
    """Apply fixes for common bugs specific to duplicate elimination."""

    # Fix: list.reverse() returns None, not the reversed list
    # Pattern: var = some_list.reverse()
    source = re.sub(
        r"(\w+)\s*=\s*(\w+)\.reverse\(\)", r"\1 = \2[::-1]", source
    )

    # Fix: Remove debug print statements (on their own line)
    source = re.sub(r"^\s*print\s*\([^)]*\)\s*$", "", source, flags=re.MULTILINE)

    # Fix: Tuple syntax ((x)) should be (x,) to create single-element tuple
    source = re.sub(r"\(\(\s*(\w+)\s*\)\)", r"(\1,)", source)

    return source
```
