from src.core.repair import Rule
LEARNED = []


def _learned_unique_dates_months(source):
    """Fix off-by-one uniqueness checks (count>=2 / count>1) and a misspelled variable in month comparisons; also complete contains_unique_day by checking whether any birthday in the given month has a unique day."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def seg(node):
        return source[node.lineno - 1:][node.col_offset:] if False else None

    class V(ast.NodeVisitor):
        def visit_Compare(self, node):
            # count >= 2  ->  count == 1
            if (isinstance(node.left, ast.Name) and node.left.id == "count" and
                len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE) and
                len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant) and
                node.comparators[0].value == 2):
                out.append(("cmp", node.lineno, node.col_offset, node.end_lineno, node.end_col_offset))
            # motnh == item[0] -> month == item[0]
            if (isinstance(node.left, ast.Name) and node.left.id == "motnh"):
                out.append(("name", node.left.lineno, node.left.col_offset, node.left.end_lineno, node.left.end_col_offset, "month"))
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            if node.name == "contains_unique_day":
                # Replace bare "return" / "return None" with the intended loop-and-check logic
                for stmt in node.body:
                    if isinstance(stmt, ast.Return) and stmt.value is None:
                        out.append(("contains", stmt.lineno, stmt.col_offset, stmt.end_lineno, stmt.end_col_offset))
                        break
            self.generic_visit(node)

    V().visit(tree)
    if not out:
        return []

    lines = source.splitlines(keepends=True)

    def span_to_index(lineno, col):
        return sum(len(lines[i]) for i in range(lineno - 1)) + col

    edits = []
    for item in out:
        if item[0] == "cmp":
            _, l1, c1, l2, c2 = item
            s, e = span_to_index(l1, c1), span_to_index(l2, c2)
            edits.append((s, e, "count == 1"))
        elif item[0] == "name":
            _, l1, c1, l2, c2, repl = item
            s, e = span_to_index(l1, c1), span_to_index(l2, c2)
            edits.append((s, e, repl))
        elif item[0] == "contains":
            _, l1, c1, l2, c2 = item
            s, e = span_to_index(l1, c1), span_to_index(l2, c2)
            repl = (
                "for item in possible_birthdays:\n"
                "        if item[0] == month:\n"
                "            if unique_day(item[1], possible_birthdays):\n"
                "                return True\n"
                "    return False"
            )
            edits.append((s, e, repl))

    if not edits:
        return []

    edits.sort(key=lambda x: x[0], reverse=True)
    repaired = source
    for s, e, repl in edits:
        if repaired[s:e] == repl:
            continue
        repaired = repaired[:s] + repl + repaired[e:]

    return [repaired]

LEARNED.append(Rule("unique_dates_months", _learned_unique_dates_months, symptoms=('err:NameError', 'wrong')))
