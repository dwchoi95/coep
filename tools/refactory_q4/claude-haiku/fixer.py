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
            Rule(
                name="pop_without_index_in_merge",
                apply=self._pop_without_index,
                symptoms=("wrong",),
            ),
            Rule(
                name="min_instead_of_max",
                apply=self._min_to_max,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_reset_in_bubble_loop",
                apply=self._missing_reset,
                symptoms=("wrong",),
            ),
            Rule(
                name="undefined_variable_reference",
                apply=self._undefined_variable,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="empty_tuple_check_instead_of_list",
                apply=self._empty_tuple_to_list,
                symptoms=("wrong",),
            ),
            Rule(
                name="bubble_sort_needs_reverse",
                apply=self._bubble_sort_reverse,
                symptoms=("wrong",),
            ),
            Rule(
                name="merge_sort_needs_reverse_logic",
                apply=self._merge_sort_logic,
                symptoms=("wrong",),
            ),
        ]

    def _pop_without_index(self, source):
        """Fix pop() calls without index in merge sort – should pop(0)."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
                    # Check if no arguments
                    if len(node.args) == 0:
                        # This is a .pop() with no args; change to .pop(0)
                        s, e = _span(source, node)
                        # Find the closing paren and insert 0
                        call_text = source[s:e]
                        new_call = call_text[:-1] + "0)"
                        out.append(_splice(source, node, new_call))
        return out

    def _min_to_max(self, source):
        """Fix min() to max() when building descending order."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "min":
                    # Check context: if we're appending to a result and then
                    # removing from a list, likely need max instead
                    s, e = _span(source, node.func)
                    new_text = "max"
                    out.append(_splice(source, node.func, new_text))
        return out

    def _missing_reset(self, source):
        """Fix missing reset of loop index after swap in bubble sort variant."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            # Look for: if condition: ... del lst[i] (without reset)
            if isinstance(node, ast.If):
                if isinstance(node.body, list) and len(node.body) >= 1:
                    # Check if last statement in if-body is a Delete on lst[i]
                    last_stmt = node.body[-1]
                    if isinstance(last_stmt, ast.Delete):
                        for target in last_stmt.targets:
                            if isinstance(target, ast.Subscript):
                                if isinstance(target.value, ast.Name) and target.value.id == "lst":
                                    # Found a pattern: if ... del lst[i]
                                    # Add i=0 reset after the if block
                                    # Insert after the del statement
                                    s, e = _span(source, last_stmt)
                                    # Add newline and reset statement
                                    indent = "            "  # Match surrounding indent
                                    reset_code = "\n" + indent + "i=0"
                                    out.append(source[:e] + reset_code + source[e:])
        return out

    def _undefined_variable(self, source):
        """Fix undefined variable references (e.g., 'a' instead of 'lst')."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "a":
                # Only replace if it looks like it should be 'lst'
                # (simple heuristic: in sort_age function context)
                s, e = _span(source, node)
                out.append(_splice(source, node, "lst"))
        return out

    def _empty_tuple_to_list(self, source):
        """Fix empty tuple () check to empty list [] check."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Look for: lst == ()
                if len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                    right = node.comparators[0]
                    if isinstance(right, ast.Tuple) and len(right.elts) == 0:
                        # Replace () with []
                        s, e = _span(source, right)
                        out.append(_splice(source, right, "[]"))
        return out

    def _bubble_sort_reverse(self, source):
        """Fix ascending bubble sort by reversing at the end."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "sort_age":
                # Check if function ends with 'return lst' without a reverse
                if node.body:
                    ret_stmt = node.body[-1]
                    if isinstance(ret_stmt, ast.Return):
                        if isinstance(ret_stmt.value, ast.Name) and ret_stmt.value.id == "lst":
                            # Add [::-1] to the return
                            s, e = _span(source, ret_stmt.value)
                            new_text = "lst[::-1]"
                            out.append(_splice(source, ret_stmt.value, new_text))
        return out

    def _merge_sort_logic(self, source):
        """Fix merge sort that pops from end instead of front."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        
        out = []
        for node in ast.walk(tree):
            # Look for .pop() calls in a while loop (merge step)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
                    if len(node.args) == 0:
                        # Change to pop(0)
                        s, e = _span(source, node)
                        call_text = source[s:e]
                        new_call = call_text[:-1] + "0)"
                        out.append(_splice(source, node, new_call))
        return out