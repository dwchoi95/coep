from src.core.repair import Rule
LEARNED = []


def _learned_count_exactly_one(source):
    """Fix uniqueness checks that incorrectly use `> 1` when the intent is to require exactly one match."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Fixer(ast.NodeVisitor):
        def visit_If(self, node):
            # Match: if count > 1: ...  ->  if count != 1: ...
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == 1
            ):
                start = (test.lineno, test.col_offset)
                end = (test.end_lineno, test.end_col_offset)

                lines = source.splitlines(keepends=True)
                offsets = [0]
                for line in lines:
                    offsets.append(offsets[-1] + len(line))

                s = offsets[start[0] - 1] + start[1]
                e = offsets[end[0] - 1] + end[1]

                edited = source[:s] + source[s:e].replace(">", "!=", 1) + source[e:]
                if edited != source:
                    out.append(edited)

    Fixer().visit(tree)
    return out

LEARNED.append(Rule("count_exactly_one", _learned_count_exactly_one, symptoms=('wrong')))


def _learned_exactly_one_for_uniqueness(source):
    """Detects the misconception that a value is considered unique when it appears fewer than two times, and repairs it to require exactly one occurrence."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Fixer(ast.NodeVisitor):
        def visit_If(self, node):
            # Match: if count >= 2: return False
            if (
                isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "count"
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.GtE)
                and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == 2
                and node.body
                and isinstance(node.body[0], ast.Return)
                and isinstance(node.body[0].value, ast.Constant)
                and node.body[0].value.value is False
            ):
                cmp = node.test
                start = cmp.left.end_col_offset
                end = cmp.comparators[0].col_offset + len("2")
                lines = source.splitlines(True)
                idx = cmp.left.lineno - 1
                # compute absolute char offsets
                prefix = sum(len(lines[i]) for i in range(idx))
                abs_start = prefix + start
                abs_end = prefix + end
                edited = source[:abs_start] + " != 1" + source[abs_end:]
                out.append(edited)
            self.generic_visit(node)

    Fixer().visit(tree)
    return out

LEARNED.append(Rule("exactly_one_for_uniqueness", _learned_exactly_one_for_uniqueness, symptoms=('wrong')))
