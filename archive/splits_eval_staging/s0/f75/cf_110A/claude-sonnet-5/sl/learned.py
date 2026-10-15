from src.core.repair import Rule
LEARNED = []


def _learned_lucky_range_check(source):
    """Misconception: checking whether a count is a 'lucky number' by testing
    if it falls in the numeric range [4, 7] instead of checking that every
    digit of the count is 4 or 7 (lucky numbers can be 44, 47, 74, 77, 444...)."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []

    def get_var_name(node):
        if isinstance(node, ast.Name):
            return node.id
        return None

    def is_bound(node, val):
        # matches ast.Constant(val) or ast.Num(val)
        return isinstance(node, ast.Constant) and node.value == val

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.found = []

        def visit_BoolOp(self, node):
            if isinstance(node.op, ast.And) and len(node.values) == 2:
                a, b = node.values
                var = None
                lo_ok = hi_ok = False
                for cmp_node in (a, b):
                    if isinstance(cmp_node, ast.Compare) and len(cmp_node.ops) == 1:
                        left = cmp_node.left
                        op = cmp_node.ops[0]
                        right = cmp_node.comparators[0]
                        v = get_var_name(left)
                        if v is not None:
                            if isinstance(op, (ast.GtE, ast.Gt)) and is_bound(right, 4):
                                var = v
                                lo_ok = True
                            elif isinstance(op, (ast.LtE, ast.Lt)) and is_bound(right, 7):
                                var = v
                                hi_ok = True
                if var and lo_ok and hi_ok:
                    self.found.append((node, var))
            self.generic_visit(node)

        def visit_Compare(self, node):
            # chained comparison: 4 <= var <= 7
            if (len(node.ops) == 2 and
                    isinstance(node.ops[0], (ast.LtE, ast.Lt)) and
                    isinstance(node.ops[1], (ast.LtE, ast.Lt))):
                left = node.left
                mid = node.comparators[0]
                right = node.comparators[1]
                var = get_var_name(mid)
                if var and is_bound(left, 4) and is_bound(right, 7):
                    self.found.append((node, var))
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    if not finder.found:
        return []

    lines = source.splitlines(keepends=True)

    def node_span(node):
        start_line = node.lineno - 1
        start_col = node.col_offset
        end_line = node.end_lineno - 1
        end_col = node.end_col_offset
        return start_line, start_col, end_line, end_col

    def splice(src_lines, start_line, start_col, end_line, end_col, replacement):
        new_lines = src_lines[:]
        if start_line == end_line:
            line = new_lines[start_line]
            new_lines[start_line] = line[:start_col] + replacement + line[end_col:]
        else:
            first = new_lines[start_line][:start_col]
            last = new_lines[end_line][end_col:]
            new_lines[start_line:end_line + 1] = [first + replacement + last]
        return "".join(new_lines)

    for node, var in finder.found:
        start_line, start_col, end_line, end_col = node_span(node)
        replacement = f'all(c in "47" for c in str({var}))'
        new_source = splice(lines, start_line, start_col, end_line, end_col, replacement)
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("lucky_range_check", _learned_lucky_range_check, symptoms=('wrong')))
