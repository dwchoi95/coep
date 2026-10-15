from src.core.repair import Rule
LEARNED = []


def _learned_count_le1_unique_misconception(source):
    """Misconception: treating `count <= 1` as "unique" conflates the
    zero-matches case (nothing found) with the exactly-one-match case
    (truly unique). A preceding `if count > 1: return False` branch followed
    by `elif count <= 1: return True` must be split so that `count == 0`
    also returns False, and only the true in-between case returns True."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.hits = []

        def visit_If(self, node):
            # Look for elif test: <var> <= 1
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.LtE)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == 1
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Return)
                and isinstance(node.body[0].value, ast.Constant)
                and node.body[0].value.value is True
            ):
                self.hits.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    if not finder.hits:
        return []

    lines = source.splitlines(keepends=True)

    def offset(lineno, col):
        return sum(len(l) for l in lines[: lineno - 1]) + col

    for node in finder.hits:
        start = offset(node.lineno, node.col_offset)
        end = offset(node.end_lineno, node.end_col_offset)

        var_name = ast.unparse(node.test.left)
        elif_indent = ' ' * node.col_offset
        body_indent = elif_indent + '    '

        replacement = (
            f"elif {var_name} == 0:\n"
            f"{body_indent}return False\n"
            f"{elif_indent}else:\n"
            f"{body_indent}return True"
        )

        new_source = source[:start] + replacement + source[end:]
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("count_le1_unique_misconception", _learned_count_le1_unique_misconception, symptoms=('wrong',)))
