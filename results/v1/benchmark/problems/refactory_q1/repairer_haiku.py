from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
import ast

TESTS = [
    {"args": [42, [-5, 1, 3, 5, 7, 10]], "expected": 6},
    {"args": [42, [1, 5, 10]], "expected": 3},
    {"args": [5, [1, 5, 10]], "expected": 1},
    {"args": [7, [1, 5, 10]], "expected": 2},
    {"args": [3, [1, 5, 10]], "expected": 1},
    {"args": [-5, [1, 5, 10]], "expected": 0},
    {"args": [10, [-5, -1, 3, 5, 7, 10]], "expected": 5},
    {"args": [-100, [-5, -1, 3, 5, 7, 10]], "expected": 0},
    {"args": [0, [-5, -1, 3, 5, 7, 10]], "expected": 2},
    {"args": [100, []], "expected": 0},
    {"args": [-100, []], "expected": 0},
]


def detect_and_fix_undefined_loop_var(source: str) -> str | None:
    """
    Detect pattern where a for loop variable is used after the loop
    but not initialized before it. This causes NameError when the loop
    doesn't execute (e.g., empty sequence).
    
    Pattern: for i in range(len(seq)): ... return i + 1
    Fix: Add i = -1 before the for loop.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "search":
            # Look for a for loop with variable over range(len(...))
            for_loop_node = None
            for_loop_idx = None
            loop_var = None
            
            for i, stmt in enumerate(node.body):
                if isinstance(stmt, ast.For):
                    # Check if it's a for i in range(len(...)) loop
                    if (isinstance(stmt.iter, ast.Call) and
                        isinstance(stmt.iter.func, ast.Name) and
                        stmt.iter.func.id == "range" and
                        len(stmt.iter.args) == 1 and
                        isinstance(stmt.iter.args[0], ast.Call) and
                        isinstance(stmt.iter.args[0].func, ast.Name) and
                        stmt.iter.args[0].func.id == "len"):
                        for_loop_node = stmt
                        for_loop_idx = i
                        loop_var = stmt.target.id if isinstance(stmt.target, ast.Name) else None
                        break
            
            if for_loop_node is None or loop_var is None:
                continue
            
            # Check if the loop variable is used after the loop
            uses_after = False
            for stmt in node.body[for_loop_idx + 1:]:
                if uses_name(stmt, loop_var):
                    uses_after = True
                    break
            
            if not uses_after:
                continue
            
            # Check if the loop variable is initialized before the loop
            initialized_before = False
            for stmt in node.body[:for_loop_idx]:
                if assigns_name(stmt, loop_var):
                    initialized_before = True
                    break
            
            if initialized_before:
                continue
            
            # Pattern matched! Apply the fix.
            lines = source.split('\n')
            
            # Find the for loop in the source
            for_line_idx = -1
            for i, line in enumerate(lines):
                if f'for {loop_var} in range' in line:
                    for_line_idx = i
                    break
            
            if for_line_idx < 0:
                continue
            
            # Get indentation
            for_indent = len(lines[for_line_idx]) - len(lines[for_line_idx].lstrip())
            indent_str = ' ' * for_indent
            
            # Insert i = -1 before the for loop
            new_lines = lines[:for_line_idx] + [indent_str + f'{loop_var} = -1'] + lines[for_line_idx:]
            return '\n'.join(new_lines)
    
    return None


def uses_name(node, name: str) -> bool:
    """Check if a node uses a given name."""
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == name:
            return True
    return False


def assigns_name(node, name: str) -> bool:
    """Check if a node assigns to a given name."""
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return True
    return False


def repair(source: str) -> str | None:
    try:
        ast.parse(source)
    except SyntaxError:
        return None
    
    # Strategy 0: Try to detect and fix the undefined loop variable pattern
    fixed = detect_and_fix_undefined_loop_var(source)
    if fixed is not None:
        result = first_passing([fixed], "search", TESTS, source, max_rps=0.35, max_checks=1)
        if result is not None:
            return result
    
    # Strategy 1: Try generic edits with max_edits=1 (increased budget for better coverage)
    candidates = candidates_generic(source, max_edits=1, budget=3000)
    result = first_passing(candidates, "search", TESTS, source, max_rps=0.35, max_checks=1200)
    if result is not None:
        return result
    
    # Strategy 2: Try with max_edits=2 for more complex fixes
    candidates = candidates_generic(source, max_edits=2, budget=4000)
    result = first_passing(candidates, "search", TESTS, source, max_rps=0.35, max_checks=1200)
    if result is not None:
        return result
    
    # Strategy 3: Try adding missing return statement, then search again
    modified_source = add_missing_return(source)
    if modified_source != source:
        candidates = candidates_generic(modified_source, max_edits=1, budget=3000)
        result = first_passing(candidates, "search", TESTS, source, max_rps=0.35, max_checks=1200)
        if result is not None:
            return result
    
    return None


def add_missing_return(source: str) -> str:
    """
    Add 'return len(seq)' at the end of the search function if it doesn't 
    already end with a return statement. This handles cases where functions
    implicitly return None for certain inputs (e.g., empty sequences).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    
    # Check if search function ends with a return statement
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "search":
            if node.body and isinstance(node.body[-1], ast.Return):
                return source  # Already ends with return
            break
    
    lines = source.split('\n')
    
    # Find the line with 'def search'
    def_line_idx = -1
    for i, line in enumerate(lines):
        if 'def search' in line:
            def_line_idx = i
            break
    
    if def_line_idx < 0:
        return source
    
    # Get indentation of the def line and compute body indentation
    def_indent = len(lines[def_line_idx]) - len(lines[def_line_idx].lstrip())
    body_indent = def_indent + 4
    
    # Find the last line of the function (before any dedent back to def level or less)
    last_func_line_idx = def_line_idx
    for i in range(def_line_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= def_indent and stripped:
            # This line is at or outside the function level
            break
        last_func_line_idx = i
    
    # Add return statement with correct body-level indentation
    indent_str = ' ' * body_indent
    new_lines = lines[:last_func_line_idx+1] + [indent_str + 'return len(seq)'] + lines[last_func_line_idx+1:]
    return '\n'.join(new_lines)
