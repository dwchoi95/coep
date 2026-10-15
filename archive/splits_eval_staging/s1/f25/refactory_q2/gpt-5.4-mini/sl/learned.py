from src.core.repair import Rule
LEARNED = []


def _learned_unique_day_and_contains_rule(source):
    """Fix off-by-one uniqueness checks (count must be exactly 1, and contains_unique_day should return whether any birthday in the month has a unique day)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def span(node):
        return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

    lines = source.splitlines(keepends=True)

    def replace_node(node, new_text):
        sl, sc, el, ec = span(node)
        start = sum(len(lines[i]) for i in range(sl - 1)) + sc
        end = sum(len(lines[i]) for i in range(el - 1)) + ec
        return source[:start] + new_text + source[end:]

    class Visitor(ast.NodeVisitor):
        def visit_If(self, node):
            # Fix `if count >= 2: ... else: return True` -> `if count == 1: return True else: return False`
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and len(node.test.comparators) == 1:
                op = node.test.ops[0]
                if isinstance(op, ast.GtE):
                    left = node.test.left
                    right = node.test.comparators[0]
                    if isinstance(left, ast.Name) and left.id == "count" and isinstance(right, ast.Constant) and right.value == 2:
                        if len(node.body) == 1 and len(node.orelse) == 1:
                            if isinstance(node.body[0], ast.Return) and isinstance(node.orelse[0], ast.Return):
                                new = "if count == 1:\n        return True\n    else:\n        return False"
                                out.append(replace_node(node, new))
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            if node.name == "contains_unique_day":
                # Replace bare `return` with the intended loop/check.
                if len(node.body) == 1 and isinstance(node.body[0], ast.Return) and node.body[0].value is None:
                    new = (
                        "for item in possible_birthdays:\n"
                        "        if month == item[0]:\n"
                        "            if unique_day(item[1], possible_birthdays):\n"
                        "                return True\n"
                        "    return False"
                    )
                    out.append(replace_node(node.body[0], new))
            self.generic_visit(node)

    Visitor().visit(tree)
    return out

LEARNED.append(Rule("unique_day_and_contains_rule", _learned_unique_day_and_contains_rule, symptoms=('wrong')))
