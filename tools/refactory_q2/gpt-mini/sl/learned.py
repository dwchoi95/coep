from src.core.repair import Rule
LEARNED = []


def _learned_count_equals_one(source):
    """Treat a uniqueness check as exact-one, not greater-than-one, when counting matches."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Rewriter(ast.NodeVisitor):
        def visit_If(self, node):
            # Match: if count > 1: ...  ->  if count != 1: ...
            if isinstance(node.test, ast.Compare):
                cmp = node.test
                if (
                    isinstance(cmp.left, ast.Name)
                    and cmp.left.id == "count"
                    and len(cmp.ops) == 1
                    and isinstance(cmp.ops[0], ast.Gt)
                    and len(cmp.comparators) == 1
                    and isinstance(cmp.comparators[0], ast.Constant)
                    and cmp.comparators[0].value == 1
                ):
                    start = cmp.left.lineno, cmp.left.col_offset
                    end = cmp.comparators[0].end_lineno, cmp.comparators[0].end_col_offset
                    lines = source.splitlines(keepends=True)
                    def pos_to_idx(line, col):
                        return sum(len(lines[i]) for i in range(line - 1)) + col
                    s = pos_to_idx(*start)
                    e = pos_to_idx(*end)
                    out.append(source[:s] + "count != 1" + source[e:])
            self.generic_visit(node)

    Rewriter().visit(tree)
    return out

LEARNED.append(Rule("count_equals_one", _learned_count_equals_one, symptoms=('wrong')))


def _learned_exactly_one_for_uniqueness_checks(source):
    """Fix uniqueness checks that incorrectly treat counts of 0 as unique by using != 1 instead of > 1."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Rewriter(ast.NodeVisitor):
        def visit_If(self, node):
            # Match: if counter > 1: return False
            if (
                isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.Gt)
                and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == 1
            ):
                # Only rewrite if the body returns False and the condition is a simple count variable
                if (
                    len(node.body) == 1
                    and isinstance(node.body[0], ast.Return)
                    and isinstance(node.body[0].value, ast.Constant)
                    and node.body[0].value.value is False
                    and isinstance(node.test.left, ast.Name)
                ):
                    start = node.test.left.end_lineno
                    end = node.test.comparators[0].end_lineno
                    # Replace only the operator token ">"
                    lines = source.splitlines(keepends=True)
                    abs_start = sum(len(l) for l in lines[:node.test.left.end_lineno - 1]) + node.test.left.end_col_offset
                    abs_end = sum(len(l) for l in lines[:node.test.comparators[0].lineno - 1]) + node.test.comparators[0].col_offset
                    if abs_start < abs_end:
                        edited = source[:abs_start] + " != " + source[abs_end:]
                        out.append(edited)
            self.generic_visit(node)

    Rewriter().visit(tree)
    return out

LEARNED.append(Rule("exactly_one_for_uniqueness_checks", _learned_exactly_one_for_uniqueness_checks, symptoms=('wrong')))
