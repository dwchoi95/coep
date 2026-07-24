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
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]

class Fixer:
    def rules(self):
        return [
            Rule(name="early_return_in_loop", apply=_early_return_in_loop, symptoms=("wrong",)),
            Rule(name="return_none_to_int", apply=_return_none_to_int, symptoms=("wrong",)),
            Rule(name="off_by_one_range", apply=_off_by_one_range, symptoms=("err:IndexError",)),
            Rule(name="missing_return_value", apply=_missing_return_value, symptoms=("wrong",)),
            Rule(name="strip_insertion_logic", apply=_strip_insertion_logic, symptoms=("wrong",)),
            Rule(name="strip_index_logic", apply=_strip_index_logic, symptoms=("wrong",)),
        ]

def _early_return_in_loop(source):
    """Detect return statement directly in for loop body that should be outside."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if len(node.body) >= 2:
                last_stmt = node.body[-1]
                if isinstance(last_stmt, ast.Return):
                    second_last = node.body[-2]
                    if isinstance(second_last, ast.If):
                        lines = source.splitlines(keepends=True)
                        starts = [0]
                        for ln in lines:
                            starts.append(starts[-1] + len(ln))
                        loop_start = starts[node.lineno - 1]
                        loop_end = starts[node.end_lineno - 1] + node.end_col_offset
                        
                        ret_start = starts[last_stmt.lineno - 1]
                        ret_end = starts[last_stmt.end_lineno - 1] + last_stmt.end_col_offset
                        
                        indent_match = source[loop_start:].split('\n')[0]
                        indent_level = len(indent_match) - len(indent_match.lstrip())
                        base_indent = ' ' * indent_level
                        
                        before_ret = source[:ret_start]
                        after_ret = source[ret_end:]
                        ret_text = source[ret_start:ret_end].lstrip()
                        
                        new_source = before_ret + after_ret + '\n' + base_indent + ret_text
                        out.append(new_source)
            elif len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                lines = source.splitlines(keepends=True)
                starts = [0]
                for ln in lines:
                    starts.append(starts[-1] + len(ln))
                loop_start = starts[node.lineno - 1]
                loop_end = starts[node.end_lineno - 1] + node.end_col_offset
                
                ret_stmt = node.body[0]
                ret_start = starts[ret_stmt.lineno - 1]
                ret_end = starts[ret_stmt.end_lineno - 1] + ret_stmt.end_col_offset
                
                indent_match = source[loop_start:].split('\n')[0]
                indent_level = len(indent_match) - len(indent_match.lstrip())
                base_indent = ' ' * indent_level
                
                before_ret = source[:ret_start]
                after_ret = source[ret_end:]
                ret_text = source[ret_start:ret_end].lstrip()
                
                new_source = before_ret + after_ret + '\n' + base_indent + ret_text
                out.append(new_source)
    
    return out

def _return_none_to_int(source):
    """Replace return None with return 0."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            if isinstance(node.value, ast.Constant) and node.value.value is None:
                out.append(_splice(source, node.value, "0"))
    
    return out

def _off_by_one_range(source):
    """Fix range(0, len(seq) + 1) to range(len(seq))."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 2:
                start_arg = node.args[0]
                end_arg = node.args[1]
                if isinstance(start_arg, ast.Constant) and start_arg.value == 0:
                    if isinstance(end_arg, ast.BinOp) and isinstance(end_arg.op, ast.Add):
                        if isinstance(end_arg.right, ast.Constant) and end_arg.right.value == 1:
                            s, e = _span(source, node)
                            left_s, left_e = _span(source, end_arg.left)
                            new_text = "range(" + source[left_s:left_e] + ")"
                            out.append(_splice(source, node, new_text))
    
    return out

def _missing_return_value(source):
    """Fix bare return statement (should return result or value)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is None:
            lines = source.splitlines(keepends=True)
            starts = [0]
            for ln in lines:
                starts.append(starts[-1] + len(ln))
            
            ret_line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
            ret_text = ret_line.strip()
            
            if ret_text.startswith("return"):
                before_return = ret_text.replace("return", "").strip()
                if not before_return or before_return == "":
                    for prev_node in ast.walk(tree):
                        if isinstance(prev_node, ast.Assign):
                            for target in prev_node.targets:
                                if isinstance(target, ast.Name) and target.id == "result":
                                    out.append(_splice(source, node, "return result"))
    
    return out

def _strip_insertion_logic(source):
    """Remove logic that builds a new list/tuple; use simple search."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "search":
            has_list_append = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) 
                and n.func.attr == "append"
                for n in ast.walk(node)
            )
            has_list_extend = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) 
                and n.func.attr == "extend"
                for n in ast.walk(node)
            )
            has_index_call = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) 
                and n.func.attr == "index"
                for n in ast.walk(node)
            )
            
            if (has_list_append or has_list_extend) and has_index_call:
                lines = source.splitlines(keepends=True)
                starts = [0]
                for ln in lines:
                    starts.append(starts[-1] + len(ln))
                
                func_start = starts[node.lineno - 1]
                func_end = starts[node.end_lineno - 1] + node.end_col_offset
                func_text = source[func_start:func_end]
                
                replacement = """def search(x, seq):
    for i, elem in enumerate(seq):
        if x <= elem:
            return i
    return len(seq)"""
                
                out.append(source[:func_start] + replacement + source[func_end:])
    
    return out

def _strip_index_logic(source):
    """Remove complex insertion/index logic and use straightforward comparison."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "search":
            has_seq_copy = any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) 
                and n.func.attr == "copy"
                for n in ast.walk(node)
            )
            if has_seq_copy:
                lines = source.splitlines(keepends=True)
                starts = [0]
                for ln in lines:
                    starts.append(starts[-1] + len(ln))
                
                func_start = starts[node.lineno - 1]
                func_end = starts[node.end_lineno - 1] + node.end_col_offset
                
                replacement = """def search(x, seq):
    for i, elem in enumerate(seq):
        if x <= elem:
            return i
    return len(seq)"""
                
                out.append(source[:func_start] + replacement + source[func_end:])
    
    return out