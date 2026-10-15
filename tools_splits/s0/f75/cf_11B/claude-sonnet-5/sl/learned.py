from src.core.repair import Rule
LEARNED = []


def _learned_triangular_off_by_one_parity(source):
    """Fixes the 'find jumps via triangular numbers' misconception: searching
    for the first csc[i] >= x then computing ad-hoc min(a,b,c) candidates
    (often off-by-one / wrong-parity) instead of simply checking the parity
    of csc[i]-x, csc[i+1]-x, and otherwise returning i+2; also the related
    off-by-one in the precomputed csc array bound and missing x==0 guard."""
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
            test = node.test
            is_target = False
            if isinstance(test, ast.Compare) and len(test.ops) == 1:
                left = test.left
                op = test.ops[0]
                right = test.comparators[0]
                if (isinstance(op, (ast.Eq, ast.Lt)) and
                        isinstance(left, ast.Name) and left.id == 'x' and
                        isinstance(right, ast.Subscript)):
                    is_target = True
            if is_target:
                self.hits.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)
    if not finder.hits:
        return []

    for node in finder.hits:
        start = node.lineno
        start_col = node.col_offset
        end = node.end_lineno
        end_col = node.end_col_offset

        lines = source.splitlines(keepends=True)
        # compute absolute char offsets
        def offset(line, col):
            return sum(len(l) for l in lines[:line - 1]) + col

        start_off = offset(start, start_col)
        end_off = offset(end, end_col)

        indent = ' ' * start_col
        replacement = (
            "if x == csc[i]:\n"
            f"{indent}    return i\n"
            f"{indent}elif x < csc[i]:\n"
            f"{indent}    if (csc[i] - x) % 2 == 0:\n"
            f"{indent}        return i\n"
            f"{indent}    elif (csc[i + 1] - x) % 2 == 0:\n"
            f"{indent}        return i + 1\n"
            f"{indent}    else:\n"
            f"{indent}        return i + 2"
        )

        new_source = source[:start_off] + replacement + source[end_off:]
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("triangular_off_by_one_parity", _learned_triangular_off_by_one_parity, symptoms=('wrong',)))
