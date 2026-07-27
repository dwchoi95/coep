from src.core.repair import Rule
LEARNED = []


def _learned_exactly_one_for_unique(source):
    """Treat uniqueness checks as requiring exactly one match, not merely more than one; also fix membership-style helpers to count matches against the intended paired field."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def span(node):
        return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

    lines = source.splitlines(keepends=True)

    def replace_first_exact(src, old, new):
        idx = src.find(old)
        if idx == -1:
            return None
        return src[:idx] + new + src[idx + len(old):]

    # Local operator fix: > 1  ->  != 1 in uniqueness counters.
    changed = source
    if "if counter > 1:" in changed:
        changed = replace_first_exact(changed, "if counter > 1:", "if counter != 1:")
    if "if counter > 1:" in changed:
        changed = replace_first_exact(changed, "if counter > 1:", "if counter != 1:")

    # More substantial local fix for contains_unique_day: compare the day field to the day field.
    # Only apply when the buggy structure is present.
    if "for i in range(16,20):" in changed and "if i[1] == j:" in changed:
        old = """def contains_unique_day(month, possible_birthdays):
    list_d = ()
    for i in range(16,20):
        i_string = str(i)
        if unique_day(i_string, possible_birthdays) is True:
            list_d = list_d + (str(i),)
    for i in possible_birthdays:
        for j in list_d:
            if i[1] == j:
                if i[0] == month:
                    return True
    return False
"""
        new = """def contains_unique_day(month, possible_birthdays):
    list_d = ()
    list_m = ()
    for i in possible_birthdays:
        if i[0] == month:
            list_m = list_m + (i,)
        else:
            list_d = list_d + (i,)
    for i in list_m:
        counter = 0
        for j in list_d:
            if i[1] == j[1]:
                counter = counter + 1
        if counter == 0:
            return True
    return False
"""
        idx = changed.find(old)
        if idx != -1:
            changed = changed[:idx] + new + changed[idx + len(old):]

    if changed != source:
        out.append(changed)
    return out

LEARNED.append(Rule("exactly_one_for_unique", _learned_exactly_one_for_unique, symptoms=('wrong')))


def _learned_fix_wrong_index_in_month_check(source):
    """Fix a mistaken index in a membership/counting check: compare the first tuple element to the month variable instead of an undefined/incorrect name."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class _Fixer(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node.name != "unique_month":
                return
            for stmt in node.body:
                if isinstance(stmt, ast.For):
                    for inner in stmt.body:
                        if isinstance(inner, ast.If):
                            test = inner.test
                            if (
                                isinstance(test, ast.Compare)
                                and isinstance(test.left, ast.Subscript)
                                and isinstance(test.left.slice, ast.Constant)
                                and test.left.slice.value == 1
                                and len(test.ops) == 1
                                and isinstance(test.ops[0], ast.Eq)
                                and len(test.comparators) == 1
                                and isinstance(test.comparators[0], ast.Name)
                                and test.comparators[0].id != "month"
                            ):
                                start = test.comparators[0].col_offset
                                end = test.comparators[0].end_col_offset
                                lines = source.splitlines(True)
                                line = lines[test.comparators[0].lineno - 1]
                                new_line = line[:start] + "month" + line[end:]
                                lines[test.comparators[0].lineno - 1] = new_line
                                out.append("".join(lines))
                                return

    _Fixer().visit(tree)
    return out

LEARNED.append(Rule("fix_wrong_index_in_month_check", _learned_fix_wrong_index_in_month_check, symptoms=('err:NameError')))


def _learned_count_equals_one(source):
    """Treat uniqueness checks as exactly-one counts, not greater-than-one counts."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Visitor(ast.NodeVisitor):
        def visit_Compare(self, node):
            # Match: count > 1  -> count != 1
            if (len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt)
                    and len(node.comparators) == 1
                    and isinstance(node.comparators[0], ast.Constant)
                    and node.comparators[0].value == 1):
                seg = ast.get_source_segment(source, node)
                if seg is not None:
                    new = seg.replace('>', '!=', 1)
                    if new != seg:
                        out.append(source[:node.col_offset] if False else None)
            self.generic_visit(node)

    # Direct span-based replacement on the original source.
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Gt)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == 1):
            start = node.lineno, node.col_offset
            end = node.end_lineno, node.end_col_offset
            lines = source.splitlines(keepends=True)
            sidx = sum(len(lines[i]) for i in range(start[0] - 1)) + start[1]
            eidx = sum(len(lines[i]) for i in range(end[0] - 1)) + end[1]
            out.append(source[:sidx] + source[sidx:eidx].replace('>', '!=', 1) + source[eidx:])

    return out

LEARNED.append(Rule("count_equals_one", _learned_count_equals_one, symptoms=('wrong')))
