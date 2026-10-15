from src.core.repair import Rule
LEARNED = []


def _learned_nearly_lucky_offbyrange(source):
    """Fix the common misconception that 'nearly lucky' means the count of lucky digits must lie in the inclusive range 4..7; the correct check is whether the count itself is a lucky number (here, exactly 4 or 7)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def visit_IfExp(self, node):
            # Match: "YES" if count >= 4 and count <= 7 else "NO"
            if (
                isinstance(node.test, ast.BoolOp)
                and isinstance(node.test.op, ast.And)
                and len(node.test.values) == 2
                and all(isinstance(v, ast.Compare) for v in node.test.values)
            ):
                a, b = node.test.values
                if (
                    isinstance(a.left, ast.Name)
                    and a.left.id == "count"
                    and len(a.ops) == 1
                    and len(a.comparators) == 1
                    and isinstance(a.ops[0], ast.GtE)
                    and isinstance(a.comparators[0], ast.Constant)
                    and a.comparators[0].value == 4
                    and isinstance(b.left, ast.Name)
                    and b.left.id == "count"
                    and len(b.ops) == 1
                    and len(b.comparators) == 1
                    and isinstance(b.ops[0], ast.LtE)
                    and isinstance(b.comparators[0], ast.Constant)
                    and b.comparators[0].value == 7
                ):
                    self.target = node
            self.generic_visit(node)

    finder = Finder()
    finder.target = None
    finder.visit(tree)
    node = finder.target
    if node is None:
        return []

    lines = source.splitlines(keepends=True)

    def abspos(lineno, col):
        return sum(len(lines[i]) for i in range(lineno - 1)) + col

    start = abspos(node.test.lineno, node.test.col_offset)
    end = abspos(node.test.end_lineno, node.test.end_col_offset)
    edited = source[:start] + "count == 4 or count == 7" + source[end:]
    if edited != source:
        out.append(edited)
    return out

LEARNED.append(Rule("nearly_lucky_offbyrange", _learned_nearly_lucky_offbyrange, symptoms=('wrong')))
