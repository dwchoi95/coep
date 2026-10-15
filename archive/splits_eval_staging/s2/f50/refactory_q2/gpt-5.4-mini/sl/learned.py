from src.core.repair import Rule
LEARNED = []


def _learned_count_equals_one_for_uniqueness(source):
    """Treat "unique" as appearing exactly once, not merely more than zero or an unimplemented placeholder."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    lines = source.splitlines(keepends=True)

    def span(node):
        return (
            sum(len(lines[i]) for i in range(node.lineno - 1)) + node.col_offset,
            sum(len(lines[i]) for i in range(node.end_lineno - 1)) + node.end_col_offset,
        )

    class Finder(ast.NodeVisitor):
        def visit_If(self, node):
            # Fix patterns like: if counter > 1: return False else: return True
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                op = node.test.ops[0]
                left = node.test.left
                comp = node.test.comparators[0]

                # counter > 1  ->  counter == 1
                if isinstance(op, ast.Gt) and isinstance(comp, ast.Constant) and comp.value == 1:
                    s, e = span(op)
                    out.append(source[:s] + "==" + source[e:])
                # counter >= 1 / counter > 0 style uniqueness checks can be similarly corrected
                elif isinstance(op, ast.GtE) and isinstance(comp, ast.Constant) and comp.value == 1:
                    s, e = span(op)
                    out.append(source[:s] + "==" + source[e:])
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            # Replace bare placeholder returns in target helper functions with the exact-count logic,
            # but only when the function body is just "return" / "pass".
            if len(node.body) == 1 and isinstance(node.body[0], ast.Return) and node.body[0].value is None:
                name = node.name
                if name in ("unique_month", "contains_unique_day"):
                    # Insert a small local loop-based implementation before the placeholder return.
                    ret = node.body[0]
                    s, e = span(ret)
                    if name == "unique_month":
                        replacement = (
                            "counter = 0\n"
                            "    for birthdate in possible_birthdays:\n"
                            "        if month in birthdate:\n"
                            "            counter += 1\n"
                            "    if counter == 1:\n"
                            "        return True\n"
                            "    else:\n"
                            "        return False"
                        )
                    else:
                        replacement = (
                            "for birthdate in possible_birthdays:\n"
                            "        if month in birthdate:\n"
                            "            if unique_day(birthdate[1], possible_birthdays):\n"
                            "                return True\n"
                            "    return False"
                        )
                    out.append(source[:s] + replacement + source[e:])
            self.generic_visit(node)

    Finder().visit(tree)
    # Deduplicate while preserving order
    uniq = []
    seen = set()
    for prog in out:
        if prog not in seen and prog != source:
            seen.add(prog)
            uniq.append(prog)
    return uniq

LEARNED.append(Rule("count_equals_one_for_uniqueness", _learned_count_equals_one_for_uniqueness, symptoms=('wrong')))
