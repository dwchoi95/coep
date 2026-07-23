import ast
import re
from coep.repairlib import candidates_generic, first_passing, chain

TESTS = [
    {"args": [[9, 9, 4, 9, 7, 9, 3, 1, 6], 5], "expected": [9, 9, 9, 9, 7]},
    {"args": [[9, 8, 4, 5, 7, 2, 3, 1, 6], 5], "expected": [9, 8, 7, 6, 5]},
    {"args": [[4, 5, 2, 3, 1, 6], 6], "expected": [6, 5, 4, 3, 2, 1]},
    {"args": [[4, 5, 2, 3, 1, 6], 3], "expected": [6, 5, 4]},
    {"args": [[4, 5, 2, 3, 1, 6], 0], "expected": []},
]

def repair(source: str) -> str | None:
    """Repair a buggy top_k submission"""
    try:
        ast.parse(source)
    except:
        return None
    
    # Strategy 1: Try generic candidates with increasing edits
    # Handles off-by-one errors, comparison flips, loop condition bugs
    candidates = chain(
        candidates_generic(source, max_edits=1, budget=3000),
        candidates_generic(source, max_edits=2, budget=2000)
    )
    result = first_passing(candidates, "top_k", TESTS, original=source, max_rps=0.35, max_checks=1000)
    if result:
        return result
    
    # Strategy 2: Apply targeted fix for append(lst.remove(...)) pattern
    # This is a common bug: remove() returns None, so appending it always appends None
    # Fix: extract the max value first, then remove it, then append the value
    pattern = r'(\w+)\.append\s*\(\s*(\w+)\.remove\s*\(\s*max\s*\(\s*\2\s*\)\s*\)\s*\)'
    fixed = re.sub(
        pattern,
        lambda m: f"_m=max({m.group(2)});{m.group(2)}.remove(_m);{m.group(1)}.append(_m)",
        source
    )
    
    if fixed != source:
        try:
            ast.parse(fixed)
            candidates = chain(
                candidates_generic(fixed, max_edits=1, budget=2000),
                candidates_generic(fixed, max_edits=2, budget=1500)
            )
            result = first_passing(candidates, "top_k", TESTS, original=fixed, max_rps=0.35, max_checks=1000)
            if result:
                return result
        except:
            pass
    
    return None
