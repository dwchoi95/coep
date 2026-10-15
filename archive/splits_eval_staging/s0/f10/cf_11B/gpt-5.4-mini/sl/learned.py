from src.core.repair import Rule
LEARNED = []


def _learned_starting_count_at_zero(source):
    """Incorrectly starts the jump counter at 1 instead of 0 for cases where the minimal number of jumps may be zero."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def visit_Assign(self, node):
            if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "nr" and isinstance(node.value, ast.Constant)
                    and node.value.value == 1):
                out.append((node.value.lineno, node.value.col_offset, node.value.end_lineno, node.value.end_col_offset))
            self.generic_visit(node)

    Finder().visit(tree)
    if not out:
        return []

    # Use the first matching assignment only.
    lineno, col, end_lineno, end_col = out[0]
    lines = source.splitlines(keepends=True)
    if lineno == end_lineno:
        start = sum(len(lines[i]) for i in range(lineno - 1)) + col
        end = sum(len(lines[i]) for i in range(end_lineno - 1)) + end_col
    else:
        start = sum(len(lines[i]) for i in range(lineno - 1)) + col
        end = sum(len(lines[i]) for i in range(end_lineno - 1)) + end_col

    edited = source[:start] + "0" + source[end:]
    if edited != source:
        return [edited]
    return []

LEARNED.append(Rule("starting_count_at_zero", _learned_starting_count_at_zero, symptoms=('wrong')))
