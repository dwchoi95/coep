import ast
from src.core.repair import Rule


def _span(source, node):
    """(start, end) char offsets of node in source."""
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _splice(source, node, new_text):
    """Replace node in source with new_text."""
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _fix_parameter_name_mismatch(source):
    """
    Fix parameter name mismatches in function signatures vs. usage.
    E.g., parameter named 'date' but code references 'day', or vice versa.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # For unique_day function
            if node.name == "unique_day":
                # Get the actual parameter name
                param_name = node.args.args[0].arg if node.args.args else None
                if param_name:
                    # Walk the function body and find references to the wrong variable
                    for child in ast.walk(node):
                        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                            # Check if code uses 'day' but parameter is 'date' or vice versa
                            if param_name == "date" and child.id == "day":
                                new_source = _splice(source, child, "date")
                                out.append(new_source)
                            elif param_name == "day" and child.id == "date":
                                new_source = _splice(source, child, "day")
                                out.append(new_source)
            
            # For unique_month function (generally correct, but check for consistency)
            elif node.name == "unique_month":
                param_name = node.args.args[0].arg if node.args.args else None
    
    return out


def _fix_missing_return_statement(source):
    """
    Fix functions missing explicit return False at the end.
    Specifically for unique_month where the function may not return False.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            # Check if the function ends without an explicit return False
            if node.body:
                last_stmt = node.body[-1]
                # If the last statement is not a return, or is a conditional return
                if not isinstance(last_stmt, ast.Return):
                    # Add return False at the end
                    lines = source.splitlines(keepends=True)
                    # Find the indentation of the function body
                    if node.body:
                        body_indent = node.body[0].col_offset
                        indent_str = " " * body_indent
                        # Insert return False before the next function or EOF
                        insert_pos = source.rfind('\n', 0, _span(source, last_stmt)[1])
                        if insert_pos != -1:
                            new_source = source[:insert_pos + 1] + indent_str + "return False\n" + source[insert_pos + 1:]
                            out.append(new_source)
    
    return out


def _fix_contains_unique_day_logic(source):
    """
    Fix contains_unique_day implementations that incorrectly track unique days.
    Some implementations use add/remove logic on a list instead of checking unique_day.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            # Check if the implementation uses the buggy add/remove pattern
            source_text = source[_span(source, node)[0]:_span(source, node)[1]]
            if "remove" in source_text and "append" in source_text and "not in" in source_text:
                # This looks like the buggy Repair 3 pattern
                # We need to rewrite it to use unique_day calls instead
                # But we can't do a wholesale rewrite; let's check if unique_day is being called properly
                has_unique_day_call = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == "unique_day":
                            has_unique_day_call = True
                
                if not has_unique_day_call:
                    # The logic exists but doesn't call unique_day
                    # We can't easily fix this without wholesale rewrite
                    pass
    
    return out


def _fix_return_none_in_unique_month(source):
    """
    Fix unique_month functions that implicitly return None instead of False.
    Happens when a conditional if/else has only the True case.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "unique_month":
            # Look for incomplete if statements
            for child in ast.walk(node):
                if isinstance(child, ast.If):
                    # If there's an if with only a return True, check for missing else
                    if isinstance(child.body[-1], ast.Return):
                        ret_node = child.body[-1]
                        if isinstance(ret_node.value, ast.Constant) and ret_node.value.value is True:
                            if not child.orelse:
                                # Missing else clause - add return False
                                s, e = _span(source, child)
                                # Find the end of the if block
                                lines = source.splitlines(keepends=True)
                                if_end = _span(source, ret_node)[1]
                                # Insert newline and return False at same indentation
                                indent = " " * child.col_offset
                                new_source = source[:if_end] + "\n" + indent + "return False" + source[if_end:]
                                out.append(new_source)
    
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="parameter_name_mismatch_day_date",
                apply=_fix_parameter_name_mismatch,
                symptoms=("err:NameError", "wrong")
            ),
            Rule(
                name="missing_return_false_unique_month",
                apply=_fix_return_none_in_unique_month,
                symptoms=("wrong",)
            ),
        ]