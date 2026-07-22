from coep.repairlib import candidates_generic, first_passing, failing_tests
from coep.evaluate import rps
import ast

TESTS = [
    {"args": [[["F", 19]]], "expected": [["F", 19]]},
    {"args": [[["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]], "expected": [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]], "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30]]], "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18]]},
    {"args": [[["M", 23], ["F", 19], ["M", 30]]], "expected": [["M", 30], ["M", 23], ["F", 19]]},
    {"args": [[]], "expected": []},
]

def custom_fixes(source):
    """Generate problem-specific fixes for common bugs in sorting assignments."""
    
    # Fix 1: return X.reverse() should be X.reverse(); return X
    # (list.reverse() returns None, not the reversed list)
    for var in ['lst', 'a', 'sort', 'new', 'result']:
        fixed = source.replace(f"return {var}.reverse()", f"{var}.reverse()\n    return {var}")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 2: print(...) should be return (...)
    # (missing return statement, has print instead)
    if "print(" in source:
        lines = source.split('\n')
        fixed_lines = []
        for line in lines:
            if "print(" in line:
                stripped = line.lstrip()
                indent = line[:len(line) - len(stripped)]
                stripped = stripped.replace("print(", "return (", 1)
                fixed_lines.append(indent + stripped)
            else:
                fixed_lines.append(line)
        fixed = '\n'.join(fixed_lines)
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 3: Track element instead of age for real_146
    # Pattern: youngest = lst[0][1] tracks age, not element
    # Solution: Change to youngest = lst[0] to track element
    if "youngest = lst[0][1]" in source and "lst.remove(youngest)" in source:
        fixed = source.replace("youngest = lst[0][1]", "youngest = lst[0]")
        fixed = fixed.replace("if elem[1] < youngest:", "if elem[1] < youngest[1]:")
        fixed = fixed.replace("youngest = elem[1]", "youngest = elem")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 4: Remove instead of value for real_146.py (original Fix 3)
    # Pattern: lst.remove(youngest) where youngest is an age, not an element
    # Solution: Find the element with minimum age and remove it
    if "lst.remove(" in source and "youngest" in source:
        fixed = source.replace(
            "lst.remove(youngest)",
            "lst.remove(min(lst, key=lambda x: x[1]))"
        )
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 5: Ascending/descending order mismatch (real_202.py)
    # min() in a loop produces ascending order, but expected is descending
    # Solution: Reverse the final result
    for result_var in ['final', 'result', 'sort', 'decoy2', 'sorted']:
        if f"return {result_var}" in source:
            fixed = source.replace(f"return {result_var}", f"return {result_var}[::-1]")
            if fixed != source:
                try:
                    ast.parse(fixed)
                    yield fixed
                except:
                    pass
    
    # Fix 6: Use sorted() with reverse=True (real_344.py)
    # Pattern: manual sorting with if/else on ages
    # Solution: Use sorted() to properly sort by age descending
    if "for i in lst:" in source and "if i[1]" in source:
        fixed = source.replace(
            "for i in lst:",
            "for i in sorted(lst, key=lambda x: x[1], reverse=True):"
        )
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 7: Fix tuple building logic (real_344.py)
    # Pattern: tuple(i)+tup doesn't modify tup when in else clause
    # Solution: Assign the result back to tup
    if "tuple(i)+tup" in source:
        fixed = source.replace("tuple(i)+tup", "tup+=(i,)")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 8: Proper tuple concatenation for sorted items
    # Pattern: tup+=tuple(i) when i is a list item [gender, age]
    # Solution: tup+=(i,) to append item as tuple element
    if "tup+=" in source and "tuple(i)" in source:
        fixed = source.replace("tup+=tuple(i)", "tup+=(i,)")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 9: Complete fix for real_344 with sorting and list conversion
    # Pattern: if i[1]>current with tuple-based sorting
    # Solution: Sort list first, fix tuple building, and convert to list
    if "for i in lst:" in source and "if i[1]>current:" in source and "tup=" in source:
        fixed = source.replace("for i in lst:", "for i in sorted(lst, key=lambda x: x[1], reverse=True):")
        fixed = fixed.replace("tup+=tuple(i)", "tup+=(i,)")
        fixed = fixed.replace("tuple(i)+tup", "tup+=(i,)")
        fixed = fixed.replace("return tup", "return list(tup)")
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass
    
    # Fix 10: Save popped element for real_334
    # Pattern: lst.pop(i) followed by lst.insert(i-1,lst[i])
    # Issue: After pop, lst[i] no longer exists at that index
    # Solution: Save the popped element first
    if "lst.pop(i)" in source and "lst.insert(i-1,lst[i])" in source:
        fixed = source.replace(
            "lst.pop(i)\n            lst.insert(i-1,lst[i])",
            "elem = lst.pop(i)\n            lst.insert(i-1,elem)"
        )
        if fixed != source:
            try:
                ast.parse(fixed)
                yield fixed
            except:
                pass

def all_candidates(source):
    """Generate all candidates: custom fixes + generic edits."""
    # Custom fixes first (higher priority for targeted bugs)
    try:
        for cand in custom_fixes(source):
            yield cand
    except:
        pass
    
    # Generic edits with single-character max edits
    try:
        for cand in candidates_generic(source, max_edits=1, budget=2000):
            yield cand
    except:
        pass
    
    # Generic edits with dual-character max edits
    try:
        for cand in candidates_generic(source, max_edits=2, budget=2000):
            yield cand
    except:
        pass

def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except:
        return None
    
    # Test if original already passes all tests
    try:
        result = failing_tests(source, "sort_age", TESTS)
        if result.compiled and result.passed == result.total:
            return source
        
        # Don't attempt repair if code doesn't compile
        if not result.compiled:
            return None
    except:
        return None
    
    # Find first candidate passing all tests with acceptable patch size
    try:
        fixed = first_passing(all_candidates(source), "sort_age", TESTS, source, max_rps=0.35, max_checks=800)
        return fixed
    except:
        return None
