from src.core.repair import Rule
LEARNED = []


def _learned_unique_day_calls_helper(source):
    """Fix comparisons that mistakenly compare a helper function object instead of calling it, and repair trivial stubbed returns in related uniqueness checks."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Fixer(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            # unique_day(date, possible_birthdays): if count_dates == 0: ...
            if node.name == "unique_day":
                for stmt in node.body:
                    if isinstance(stmt, ast.If):
                        test = stmt.test
                        if (
                            isinstance(test, ast.Compare)
                            and isinstance(test.left, ast.Name)
                            and test.left.id == "count_dates"
                            and len(test.ops) == 1
                            and isinstance(test.ops[0], (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE))
                            and len(test.comparators) == 1
                            and isinstance(test.comparators[0], ast.Constant)
                            and test.comparators[0].value == 0
                        ):
                            # Replace with: count_dates(date, possible_birthdays) == 1
                            new_test = "count_dates(date, possible_birthdays) == 1"
                            start = test.lineno, test.col_offset
                            end = test.end_lineno, test.end_col_offset
                            self._replace(start, end, new_test)

            # unique_month(month, possible_birthdays): return -> count occurrences of month
            if node.name == "unique_month":
                if len(node.body) == 1 and isinstance(node.body[0], ast.Return) and node.body[0].value is None:
                    # Replace stub with local counting logic
                    repl = (
                        "count = 0\n"
                        "    for i in possible_birthdays:\n"
                        "        if i[0] == month:\n"
                        "            count += 1\n"
                        "    if count == 1:\n"
                        "        return True\n"
                        "    else:\n"
                        "        return False"
                    )
                    stmt = node.body[0]
                    self._replace((stmt.lineno, stmt.col_offset), (stmt.end_lineno, stmt.end_col_offset), repl)

            # contains_unique_day(month, possible_birthdays): return -> search for any unique day in month
            if node.name == "contains_unique_day":
                if len(node.body) == 1 and isinstance(node.body[0], ast.Return) and node.body[0].value is None:
                    repl = (
                        "for i in possible_birthdays:\n"
                        "        if i[0] == month:\n"
                        "            if unique_day(i[1], possible_birthdays):\n"
                        "                return True\n"
                        "    return False"
                    )
                    stmt = node.body[0]
                    self._replace((stmt.lineno, stmt.col_offset), (stmt.end_lineno, stmt.end_col_offset), repl)

        def _replace(self, start, end, new_text):
            self._edits.append((start, end, new_text))

    fixer = Fixer()
    fixer._edits = []
    fixer.visit(tree)

    if not fixer._edits:
        return []

    # Apply edits from the end of source backward using original character spans.
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln))

    def abspos(loc):
        lineno, col = loc
        return offsets[lineno - 1] + col

    edited = source
    for start, end, new_text in sorted(fixer._edits, key=lambda e: (e[0], e[1]), reverse=True):
        s = abspos(start)
        e = abspos(end)
        edited = edited[:s] + new_text + edited[e:]

    if edited != source:
        out.append(edited)
    return out

LEARNED.append(Rule("unique_day_calls_helper", _learned_unique_day_calls_helper, symptoms=('wrong')))


def _learned_misused_uniqueness_count(source):
    """Misapplies a helper name as a bare value or compares unique counts against the wrong constant instead of calling the helper with arguments and testing for exactly one match."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Fixer(ast.NodeVisitor):
        def visit_Compare(self, node):
            # unique_day / similar patterns: count_dates == 2 -> count_dates(date, possible_birthdays) == 1
            if (
                isinstance(node.left, ast.Name)
                and node.left.id == "count_dates"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value != 1
            ):
                self.target = node

    fixer = Fixer()
    fixer.target = None
    fixer.visit(tree)

    def span(node):
        return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

    def to_index(lines, lineno, col):
        return sum(len(lines[i]) for i in range(lineno - 1)) + col

    if fixer.target is not None:
        node = fixer.target
        lines = source.splitlines(True)
        start = to_index(lines, node.lineno, node.col_offset)
        end = to_index(lines, node.end_lineno, node.end_col_offset)
        replacement = "count_dates(date, possible_birthdays) == 1"
        out.append(source[:start] + replacement + source[end:])
        return out

    # Fix unique_month if it returns nothing / placeholder by counting matching months.
    class MonthFixer(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node.name == "unique_month":
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    self.target = node.body[0]

    mfix = MonthFixer()
    mfix.target = None
    mfix.visit(tree)
    if mfix.target is not None:
        node = mfix.target
        lines = source.splitlines(True)
        start = to_index(lines, node.lineno, node.col_offset)
        end = to_index(lines, node.end_lineno, node.end_col_offset)
        replacement = (
            "count = 0\n"
            "    for i in possible_birthdays:\n"
            "        if i[0] == month:\n"
            "            count += 1\n"
            "    return count == 1"
        )
        out.append(source[:start] + replacement + source[end:])
        return out

    # Fix contains_unique_day returning nothing / placeholder.
    class ContainsFixer(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node.name == "contains_unique_day":
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    self.target = node.body[0]

    cfix = ContainsFixer()
    cfix.target = None
    cfix.visit(tree)
    if cfix.target is not None:
        node = cfix.target
        lines = source.splitlines(True)
        start = to_index(lines, node.lineno, node.col_offset)
        end = to_index(lines, node.end_lineno, node.end_col_offset)
        replacement = (
            "for i in possible_birthdays:\n"
            "        if i[0] == month and unique_day(i[1], possible_birthdays):\n"
            "            return True\n"
            "    return False"
        )
        out.append(source[:start] + replacement + source[end:])
        return out

    return []

LEARNED.append(Rule("misused_uniqueness_count", _learned_misused_uniqueness_count, symptoms=('wrong')))


def _learned_count_equals_one(source):
    """Fix uniqueness checks that incorrectly test count > 1 / else True instead of exactly one occurrence."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def visit_If(self, node):
            # Match: if count > 1: return False else: return True
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                op = node.test.ops[0]
                if isinstance(op, ast.Gt):
                    if (
                        isinstance(node.test.left, ast.Name)
                        and node.test.left.id == "count"
                        and len(node.test.comparators) == 1
                        and isinstance(node.test.comparators[0], ast.Constant)
                        and node.test.comparators[0].value == 1
                    ):
                        if (
                            len(node.body) == 1
                            and isinstance(node.body[0], ast.Return)
                            and isinstance(node.body[0].value, ast.Constant)
                            and node.body[0].value.value is False
                            and len(node.orelse) == 1
                            and isinstance(node.orelse[0], ast.Return)
                            and isinstance(node.orelse[0].value, ast.Constant)
                            and node.orelse[0].value.value is True
                        ):
                            test_span = (node.test.lineno, node.test.col_offset, node.test.end_lineno, node.test.end_col_offset)
                            body_span = (node.body[0].lineno, node.body[0].col_offset, node.body[0].end_lineno, node.body[0].end_col_offset)
                            orelse_span = (node.orelse[0].lineno, node.orelse[0].col_offset, node.orelse[0].end_lineno, node.orelse[0].end_col_offset)
                            out.append((test_span, body_span, orelse_span))
            self.generic_visit(node)

    Finder().visit(tree)
    if not out:
        return []

    lines = source.splitlines(keepends=True)

    def offset(lineno, col):
        return sum(len(lines[i]) for i in range(lineno - 1)) + col

    edits = []
    for test_span, body_span, orelse_span in out:
        t0, tc0, t1, tc1 = test_span
        b0, bc0, b1, bc1 = body_span
        o0, oc0, o1, oc1 = orelse_span

        test_src = source[offset(t0, tc0):offset(t1, tc1)]
        body_src = source[offset(b0, bc0):offset(b1, bc1)]
        orelse_src = source[offset(o0, oc0):offset(o1, oc1)]

        new = test_src.replace("> 1", "== 1").replace(">1", "== 1")
        new_body = orelse_src
        new_orelse = body_src

        edits.append((offset(t0, tc0), offset(t1, tc1), new))
        edits.append((offset(b0, bc0), offset(b1, bc1), new_body))
        edits.append((offset(o0, oc0), offset(o1, oc1), new_orelse))

    # Apply edits in reverse order
    edited = source
    for start, end, repl in sorted(edits, key=lambda x: x[0], reverse=True):
        edited = edited[:start] + repl + edited[end:]

    return [edited]

LEARNED.append(Rule("count_equals_one", _learned_count_equals_one, symptoms=('wrong')))


def _learned_exactly_one_unique_match(source):
    """Fix mistaken uniqueness checks that use count>=2 / count!=1 instead of count==1, and complete a missing contains_unique_day by checking for any month-day pair whose day is unique."""
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

    # Fix count-based uniqueness checks in unique_day / unique_month:
    # if count >= 2: return False else: return True  ->  if count == 1: return True else: return False
    class CountCheckFix(ast.NodeTransformer):
        def visit_If(self, node):
            self.generic_visit(node)
            if (
                isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], (ast.GtE, ast.NotEq))
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "count"
                and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == 2
            ):
                # Only target the exact buggy pattern with return False/True branches.
                if (
                    len(node.body) == 1
                    and isinstance(node.body[0], ast.Return)
                    and isinstance(node.body[0].value, ast.Constant)
                    and node.body[0].value.value is False
                    and len(node.orelse) == 1
                    and isinstance(node.orelse[0], ast.Return)
                    and isinstance(node.orelse[0].value, ast.Constant)
                    and node.orelse[0].value.value is True
                ):
                    new = (
                        "if count == 1:\n"
                        "        return True\n"
                        "    else:\n"
                        "        return False"
                    )
                    out.append(replace_node(node, new))
            return node

    CountCheckFix().visit(tree)

    # Fix empty contains_unique_day by replacing a bare return or pass-only body
    # with a local scan for a unique day in the requested month.
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "contains_unique_day":
            # Match the buggy minimal body (e.g. `return` or `pass`).
            if len(node.body) == 1 and isinstance(node.body[0], ast.Return) and node.body[0].value is None:
                new = (
                    "for item in possible_birthdays:\n"
                    "        if item[0] == month:\n"
                    "            if unique_day(item[1], possible_birthdays):\n"
                    "                return True\n"
                    "    return False"
                )
                out.append(replace_node(node.body[0], new))
            elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                new = (
                    "for item in possible_birthdays:\n"
                    "        if item[0] == month:\n"
                    "            if unique_day(item[1], possible_birthdays):\n"
                    "                return True\n"
                    "    return False"
                )
                out.append(replace_node(node.body[0], new))

    return out

LEARNED.append(Rule("exactly_one_unique_match", _learned_exactly_one_unique_match, symptoms=('wrong')))
