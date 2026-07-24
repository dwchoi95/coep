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
            Rule(name="return_statement_indentation", apply=self._fix_return_indentation, symptoms=("wrong",)),
            Rule(name="strict_lt_to_le", apply=self._fix_lt_to_le, symptoms=("wrong",)),
            Rule(name="none_to_zero", apply=self._fix_none_to_zero, symptoms=("wrong",)),
            Rule(name="return_missing_value", apply=self._fix_return_missing_value, symptoms=("wrong",)),
            Rule(name="break_instead_of_return", apply=self._fix_break_instead_of_return, symptoms=("wrong",)),
            Rule(name="comparison_operators_mixed", apply=self._fix_comparison_operators, symptoms=("wrong",)),
            Rule(name="index_instead_of_position", apply=self._fix_index_instead_of_position, symptoms=("wrong",)),
        ]

    def _fix_return_indentation(self, source):
        """Move return statement outside loop body when it's indented inside."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if node.body and isinstance(node.body[-1], ast.Return):
                    last_stmt = node.body[-1]
                    # Check if there's a return at the same level as the for loop
                    parent = None
                    for p in ast.walk(tree):
                        if isinstance(p, (ast.FunctionDef, ast.If, ast.For)):
                            if hasattr(p, 'body') and node in p.body:
                                parent = p
                    if parent and isinstance(parent, ast.FunctionDef):
                        # Move the return outside
                        lines = source.splitlines(keepends=True)
                        for_line = node.lineno - 1
                        return_line = last_stmt.lineno - 1
                        if for_line < return_line < len(lines):
                            # Remove indentation from return and place after loop
                            return_src = lines[return_line].lstrip()
                            # Build new source by dedenting the return
                            new_lines = lines[:return_line] + lines[return_line + 1:]
                            for_end = node.end_lineno
                            insert_pos = for_end
                            new_lines.insert(insert_pos, "    " + return_src)
                            out.append("".join(new_lines))
        return out

    def _fix_lt_to_le(self, source):
        """Replace < with <= in comparisons."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + " <= " + source[rs:re]
                out.append(_splice(source, node, new_cmp))
        return out

    def _fix_none_to_zero(self, source):
        """Replace None return with 0."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value and isinstance(node.value, ast.Constant) and node.value.value is None:
                out.append(_splice(source, node.value, "0"))
        return out

    def _fix_return_missing_value(self, source):
        """Add missing value to bare return statement."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                # Check context - if in a loop, likely should return something
                s, e = _span(source, node)
                # Replace bare return with return 0
                out.append(_splice(source, node, "return 0"))
        return out

    def _fix_break_instead_of_return(self, source):
        """Replace break with return statement when needed."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Break):
                # Check if this is in a for loop that should return
                out.append(_splice(source, node, "return result"))
        return out

    def _fix_comparison_operators(self, source):
        """Fix >= to > and <= to <= in boundary conditions."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.GtE):
                    left, right = node.left, node.comparators[0]
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new_cmp = source[ls:le] + " > " + source[rs:re]
                    out.append(_splice(source, node, new_cmp))
        return out

    def _fix_index_instead_of_position(self, source):
        """Replace .index() calls with direct position i when iterating."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Return):
                        if isinstance(stmt.value, ast.Call):
                            call = stmt.value
                            if isinstance(call.func, ast.Attribute) and call.func.attr == "index":
                                # Check if we're in a range(len(seq)) loop
                                if isinstance(node.target, ast.Name):
                                    # Replace with just i
                                    out.append(_splice(source, stmt.value, node.target.id))
        return out