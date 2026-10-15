from src.core.repair import Rule
LEARNED = []


def _learned_unique_day_month_contains(source):
    """Comparing a function object to a number instead of calling it, plus missing simple count/scan logic for uniqueness checks."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    lines = source.splitlines(keepends=True)

    def span(node):
        start = sum(len(lines[i]) for i in range(node.lineno - 1)) + node.col_offset
        end = sum(len(lines[i]) for i in range(node.end_lineno - 1)) + node.end_col_offset
        return start, end

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.unique_day_if = None
            self.unique_month_body = None
            self.contains_unique_day_body = None

        def visit_FunctionDef(self, node):
            if node.name == "unique_day" and node.body and isinstance(node.body[0], ast.If):
                self.unique_day_if = node.body[0]
            elif node.name == "unique_month":
                self.unique_month_body = node
            elif node.name == "contains_unique_day":
                self.contains_unique_day_body = node
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    # Fix unique_day: call count_dates(date, possible_birthdays) and compare to 1
    if finder.unique_day_if and isinstance(finder.unique_day_if.test, ast.Compare):
        test = finder.unique_day_if.test
        if isinstance(test.left, ast.Name) and test.left.id == "count_dates":
            start, end = span(test)
            out.append(source[:start] + "count_dates(date, possible_birthdays) == 1" + source[end:])

    # Insert implementation for unique_month if it is just `return` or otherwise empty body
    if finder.unique_month_body:
        fn = finder.unique_month_body
        if len(fn.body) == 1 and isinstance(fn.body[0], ast.Return) and fn.body[0].value is None:
            insert_at = span(fn.body[0])[0]
            indent = " " * (fn.body[0].col_offset)
            replacement = (
                "count = 0\n"
                f"{indent}for i in possible_birthdays:\n"
                f"{indent}    if i[0] == month:\n"
                f"{indent}        count += 1\n"
                f"{indent}if count == 1:\n"
                f"{indent}    return True\n"
                f"{indent}else:\n"
                f"{indent}    return False"
            )
            out.append(source[:insert_at] + replacement + source[span(fn.body[0])[1]:])

    # Insert implementation for contains_unique_day if it is just `return`
    if finder.contains_unique_day_body:
        fn = finder.contains_unique_day_body
        if len(fn.body) == 1 and isinstance(fn.body[0], ast.Return) and fn.body[0].value is None:
            insert_at = span(fn.body[0])[0]
            indent = " " * (fn.body[0].col_offset)
            replacement = (
                f"for i in possible_birthdays:\n"
                f"{indent}if i[0] == month:\n"
                f"{indent}    if unique_day(i[1], possible_birthdays):\n"
                f"{indent}        return True\n"
                f"{indent}return False"
            )
            out.append(source[:insert_at] + replacement + source[span(fn.body[0])[1]:])

    return out

LEARNED.append(Rule("unique_day_month_contains", _learned_unique_day_month_contains, symptoms=('wrong')))


def _learned_count_duplicates_for_uniqueness(source):
    """Targets the misconception that membership in a fixed index or a bare function object can test uniqueness; instead, uniqueness must be checked by counting matches across the full list, and contains_unique_day must call the helper on actual values."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Fixer(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            nonlocal source, out
            if node.name == "unique_day":
                if len(node.body) >= 1 and isinstance(node.body[0], ast.If):
                    test = node.body[0].test
                    if isinstance(test, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in test.ops):
                        # Replace the whole function body with count-based uniqueness check
                        new_text = (
                            "    count = 0\n"
                            "    for i in possible_birthdays:\n"
                            "        if date in i:\n"
                            "            count += 1\n"
                            "    if count == 1:\n"
                            "        return True\n"
                            "    else:\n"
                            "        return False"
                        )
                        start = node.body[0].lineno - 1
                        end = node.body[-1].end_lineno
                        lines = source.splitlines(True)
                        prefix = "".join(lines[:start])
                        suffix = "".join(lines[end:])
                        func_header = source.splitlines(True)[node.lineno - 1][:node.col_offset] + f"def {node.name}(date, possible_birthdays):\n"
                        # splice only body region
                        body_start = node.body[0].lineno - 1
                        body_end = node.body[-1].end_lineno
                        out.append("".join(lines[:body_start]) + new_text + "\n" + "".join(lines[body_end:]))
                        return
            if node.name == "unique_month":
                if len(node.body) >= 1 and isinstance(node.body[0], ast.If):
                    test = node.body[0].test
                    if isinstance(test, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in test.ops):
                        new_text = (
                            "    count = 0\n"
                            "    for i in possible_birthdays:\n"
                            "        if month in i:\n"
                            "            count += 1\n"
                            "    if count == 1:\n"
                            "        return True\n"
                            "    else:\n"
                            "        return False"
                        )
                        lines = source.splitlines(True)
                        body_start = node.body[0].lineno - 1
                        body_end = node.body[-1].end_lineno
                        out.append("".join(lines[:body_start]) + new_text + "\n" + "".join(lines[body_end:]))
                        return
            if node.name == "contains_unique_day":
                # Replace a bare function-object check with an actual call over matching birthdays
                for stmt in node.body:
                    if isinstance(stmt, ast.If):
                        src_if = ast.get_source_segment(source, stmt)
                        if src_if and ("not unique_day" in src_if or "not unique_month" in src_if):
                            new_text = (
                                "    for i in possible_birthdays:\n"
                                "        if month in i:\n"
                                "            if unique_day(i[1], possible_birthdays):\n"
                                "                return True\n"
                                "        else:\n"
                                "            continue\n"
                                "    return False"
                            )
                            lines = source.splitlines(True)
                            body_start = stmt.lineno - 1
                            body_end = node.body[-1].end_lineno
                            out.append("".join(lines[:body_start]) + new_text + "\n" + "".join(lines[body_end:]))
                            return
            self.generic_visit(node)

    Fixer().visit(tree)
    return out

LEARNED.append(Rule("count_duplicates_for_uniqueness", _learned_count_duplicates_for_uniqueness, symptoms=('wrong')))
