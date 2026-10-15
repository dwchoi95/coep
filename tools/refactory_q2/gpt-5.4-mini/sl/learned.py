from src.core.repair import Rule
LEARNED = []


def _learned_missing_call_and_predicate_fix(source):
    """Misuses a function object instead of calling it, and leaves simple uniqueness checks/stub returns unimplemented."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    lines = source.splitlines(keepends=True)

    def span_text(node):
        start = sum(len(lines[i]) for i in range(node.lineno - 1)) + node.col_offset
        end = sum(len(lines[i]) for i in range(node.end_lineno - 1)) + node.end_col_offset
        return start, end, source[start:end]

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.unique_day = None
            self.unique_month = None
            self.contains_unique_day = None
            self.count_dates = None

        def visit_FunctionDef(self, node):
            if node.name == "count_dates":
                self.count_dates = node
            elif node.name == "unique_day":
                self.unique_day = node
            elif node.name == "unique_month":
                self.unique_month = node
            elif node.name == "contains_unique_day":
                self.contains_unique_day = node
            self.generic_visit(node)

    f = Finder()
    f.visit(tree)

    # Fix 1: count_dates(...) must be called in unique_day and compared to 1.
    if f.unique_day:
        target = None
        for n in ast.walk(f.unique_day):
            if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == "count_dates":
                target = n
                break
        if target is not None:
            s, e, txt = span_text(target)
            new = "count_dates(date, possible_birthdays) == 1"
            if txt != new:
                out.append(source[:s] + new + source[e:])

    # Fix 2: replace stub "return" in unique_month with local counting logic.
    if f.unique_month:
        for n in ast.walk(f.unique_month):
            if isinstance(n, ast.Return) and n.value is None:
                s, e, txt = span_text(n)
                indent = source[s - (len(source[:s].splitlines()[-1]) - len(source[:s].splitlines()[-1].lstrip())):s] if False else "    "
                # compute indentation from line start
                line_start = source.rfind("\n", 0, s) + 1
                indent = source[line_start:s]
                repl = (
                    "count = 0\n"
                    f"{indent}for i in possible_birthdays:\n"
                    f"{indent}    if i[0] == month:\n"
                    f"{indent}        count += 1\n"
                    f"{indent}return count == 1"
                )
                out.append(source[:s] + repl + source[e:])
                break

    # Fix 3: replace stub "return" in contains_unique_day with a search over matching month.
    if f.contains_unique_day:
        for n in ast.walk(f.contains_unique_day):
            if isinstance(n, ast.Return) and n.value is None:
                s, e, txt = span_text(n)
                line_start = source.rfind("\n", 0, s) + 1
                indent = source[line_start:s]
                repl = (
                    f"for i in possible_birthdays:\n"
                    f"{indent}    if i[0] == month and unique_day(i[1], possible_birthdays):\n"
                    f"{indent}        return True\n"
                    f"{indent}return False"
                )
                out.append(source[:s] + repl + source[e:])
                break

    return out

LEARNED.append(Rule("missing_call_and_predicate_fix", _learned_missing_call_and_predicate_fix, symptoms=('wrong')))


def _learned_count_uniqueness_instead_of_direct_membership(source):
    """Misuses direct membership or fixed indexing to test uniqueness; repair by counting matches across all candidates and comparing to 1."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def span(node):
        return (node.lineno - 1, node.col_offset, node.end_lineno - 1, node.end_col_offset)

    lines = source.splitlines(keepends=True)

    def replace(node, new_text):
        sl, sc, el, ec = span(node)
        start = sum(len(l) for l in lines[:sl]) + sc
        end = sum(len(l) for l in lines[:el]) + ec
        return source[:start] + new_text + source[end:]

    class Finder(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node.name in ("unique_day", "unique_month"):
                if len(node.body) == 1 and isinstance(node.body[0], ast.If):
                    ifnode = node.body[0]
                    test = ifnode.test
                    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.In):
                        lhs = ast.get_source_segment(source, test.left)
                        rhs = ast.get_source_segment(source, test.comparators[0])
                        if lhs and rhs:
                            param = node.args.args[0].arg if node.args.args else None
                            if param and lhs.strip() == param:
                                new_body = (
                                    "    count = 0\n"
                                    "    for i in possible_birthdays:\n"
                                    f"        if {lhs.strip()} in i:\n"
                                    "            count += 1\n"
                                    "    if count == 1:\n"
                                    "        return True\n"
                                    "    else:\n"
                                    "        return False\n"
                                )
                                out.append(replace(node, f"def {node.name}({param}, possible_birthdays):\n{new_body}"))
            elif node.name == "contains_unique_day":
                if len(node.body) == 1 and isinstance(node.body[0], ast.If):
                    ifnode = node.body[0]
                    test = ifnode.test
                    if (
                        isinstance(test, ast.BoolOp)
                        and isinstance(test.op, ast.And)
                        and len(test.values) == 2
                    ):
                        new_body = (
                            "    for i in possible_birthdays:\n"
                            "        if month in i:\n"
                            "            if unique_day(i[1], possible_birthdays):\n"
                            "                return True\n"
                            "    return False\n"
                        )
                        out.append(replace(node, f"def contains_unique_day(month, possible_birthdays):\n{new_body}"))
            self.generic_visit(node)

    Finder().visit(tree)
    return out

LEARNED.append(Rule("count_uniqueness_instead_of_direct_membership", _learned_count_uniqueness_instead_of_direct_membership, symptoms=('wrong')))


def _learned_count_equality_for_uniqueness(source):
    """Mistakenly treats uniqueness as count >= 2 or count > 1 instead of exactly one occurrence."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Fixer(ast.NodeVisitor):
        def visit_If(self, node):
            # Match: if count >= 2: return False else: return True
            # or same logic expressed with >= / > and True/False branches.
            if (
                isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], (ast.GtE, ast.Gt))
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "count"
                and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == 2
                and len(node.body) == 1
                and len(node.orelse) == 1
                and isinstance(node.body[0], ast.Return)
                and isinstance(node.orelse[0], ast.Return)
            ):
                b = node.body[0]
                o = node.orelse[0]
                if (
                    isinstance(b.value, ast.Constant)
                    and isinstance(o.value, ast.Constant)
                    and b.value.value is False
                    and o.value.value is True
                ):
                    # Replace the whole if/else with:
                    # if count == 1:
                    #     return True
                    # else:
                    #     return False
                    new_text = (
                        "if count == 1:\n"
                        "        return True\n"
                        "    else:\n"
                        "        return False"
                    )
                    start = node.lineno, node.col_offset
                    end = node.end_lineno, node.end_col_offset
                    lines = source.splitlines(keepends=True)
                    idx0 = sum(len(lines[i]) for i in range(start[0] - 1)) + start[1]
                    idx1 = sum(len(lines[i]) for i in range(end[0] - 1)) + end[1]
                    out.append(source[:idx0] + new_text + source[idx1:])
            self.generic_visit(node)

    Fixer().visit(tree)
    return out

LEARNED.append(Rule("count_equality_for_uniqueness", _learned_count_equality_for_uniqueness, symptoms=('wrong')))
