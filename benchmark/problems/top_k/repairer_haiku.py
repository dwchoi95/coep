from coep.repairlib import candidates_generic, first_passing
from itertools import chain
import ast
import re

TESTS = [
    {"args": [[5, 5, 1], 2], "expected": [5, 5]},
    {"args": [[3, 1, 2], 2], "expected": [3, 2]},
    {"args": [[1, 2, 3, 4, 5], 3], "expected": [5, 4, 3]},
    {"args": [[], 0], "expected": []},
    {"args": [[], 3], "expected": []},
    {"args": [[7], 1], "expected": [7]},
    {"args": [[4, 2], 0], "expected": []},
    {"args": [[1, 2], 5], "expected": [2, 1]},
    {"args": [[-1, -5, -3], 2], "expected": [-1, -3]},
    {"args": [[10, 10, 10], 2], "expected": [10, 10]},
    {"args": [[0, -1, 1], 3], "expected": [1, 0, -1]},
    {"args": [[2, 8, 6, 4, 9, 1], 4], "expected": [9, 8, 6, 4]},
    {"args": [[5, 3, 5, 3, 5], 3], "expected": [5, 5, 5]},
    {"args": [[100], 0], "expected": []},
]

def specific_fixes(source):
    """Generate problem-specific fixes for common top_k bugs."""
    fixes = [
        (r"\[:k\s*-\s*1\]", "[:k]"),
        (r"reverse\s*=\s*False", "reverse=True"),
        (r"nsmallest", "nlargest"),
        (r"len\(result\)\s*<=\s*k", "len(result) < k"),
        (r"m\s*=\s*temp\[-1\]", "m = temp[0]"),
    ]
    
    for pattern, replacement in fixes:
        modified = re.sub(pattern, replacement, source)
        if modified != source:
            yield modified

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    candidates = chain(
        specific_fixes(source),
        candidates_generic(source, max_edits=1, budget=1500)
    )
    result = first_passing(candidates, "top_k", TESTS, source, max_rps=0.35, max_checks=1000)
    if result:
        return result
    
    candidates = candidates_generic(source, max_edits=2, budget=1500)
    result = first_passing(candidates, "top_k", TESTS, source, max_rps=0.35, max_checks=500)
    if result:
        return result
    
    return None
