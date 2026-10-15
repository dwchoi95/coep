from src.core.repair import Rule
LEARNED = []


def _learned_fix_uniqueness_count_comparison(source):
    """Misconception: testing `count > 1` (with swapped True/False branches)
    instead of `count == 1` when checking whether something occurs exactly
    once. Since count is always >= 1 in these "is this unique" helpers,
    `count > 1` combined with inverted branch values happens to look
    plausible but is semantically backwards; the correct test is
    `count == 1` with the matching True/False branch values."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)

    def offset(lineno, col):
        return sum(len(l) for l in lines[:lineno - 1]) + col

    def bool_value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return node.value
        return None

    def branch_value_span(stmts):
        # Expect a single Assign(... = True/False) or Return(True/False)
        if len(stmts) != 1:
            return None
        stmt = stmts[0]
        if isinstance(stmt, ast.Assign):
            val = stmt.value
        elif isinstance(stmt, ast.Return):
            val = stmt.value
        else:
            return None
        if val is None:
            return None
        bv = bool_value(val)
        if bv is None:
            return None
        start = offset(val.lineno, val.col_offset)
        end = offset(val.end_lineno, val.end_col_offset)
        return bv, start, end

    edits = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Gt):
            continue
        if len(test.comparators) != 1:
            continue
        comp = test.comparators[0]
        if not (isinstance(comp, ast.Constant) and comp.value == 1):
            continue

        body_info = branch_value_span(node.body)
        orelse_info = branch_value_span(node.orelse)
        if body_info is None or orelse_info is None:
            continue

        body_val, b_start, b_end = body_info
        orelse_val, o_start, o_end = orelse_info

        if body_val == orelse_val:
            continue  # not the inverted-boolean pattern

        # Fix the comparator: `> 1` -> `== 1`
        test_start = offset(test.lineno, test.col_offset)
        test_end = offset(test.end_lineno, test.end_col_offset)
        test_text = source[test_start:test_end]
        if '>' not in test_text:
            continue
        new_test_text = test_text.replace('>', '==', 1)
        edits.append((test_start, test_end, new_test_text))

        # Swap the True/False literals between the branches
        body_text = source[b_start:b_end]
        orelse_text = source[o_start:o_end]
        edits.append((b_start, b_end, orelse_text))
        edits.append((o_start, o_end, body_text))

    if not edits:
        return []

    # Apply edits from the end of the file backwards so offsets stay valid
    edits.sort(key=lambda e: e[0], reverse=True)
    new_source = source
    for start, end, text in edits:
        new_source = new_source[:start] + text + new_source[end:]

    if new_source == source:
        return []

    return [new_source]

LEARNED.append(Rule("fix_uniqueness_count_comparison", _learned_fix_uniqueness_count_comparison, symptoms=('wrong')))


def _learned_possible_birthdays_misuse(source):
    """Fixes the misconception that `possible_birthdays` is a fixed two-column
    structure to be indexed positionally (possible_birthdays[0]/[1]) instead of
    a list of (month, day) pairs to be scanned and counted, and the related
    misconception of using a function name as a truthy value (e.g. `not
    unique_day`) instead of calling it."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)

    def span(node):
        start = sum(len(l) for l in lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(l) for l in lines[:node.end_lineno - 1]) + node.end_col_offset
        return start, end

    out = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        # Pattern 1: unique_day / unique_month indexing possible_birthdays[0]/[1]
        if len(node.body) == 1 and isinstance(node.body[0], ast.If):
            test = node.body[0].test
            if (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.In)):
                right = test.comparators[0]
                if (isinstance(right, ast.Subscript)
                        and isinstance(right.slice, ast.Constant)
                        and isinstance(right.slice.value, int)):
                    args = [a.arg for a in node.args.args]
                    if len(args) == 2:
                        var_name, coll_name = args
                        fixed = (
                            f"def {node.name}({var_name}, {coll_name}):\n"
                            f"    count = 0\n"
                            f"    for i in {coll_name}:\n"
                            f"        if {var_name} in i:\n"
                            f"            count += 1\n"
                            f"    return count == 1\n"
                        )
                        start, end = span(node)
                        out.append(source[:start] + fixed.rstrip("\n") + source[end:])

        # Pattern 2: contains_unique_day using `not unique_day and not unique_month`
        if node.name == "contains_unique_day" and len(node.body) == 1 and isinstance(node.body[0], ast.If):
            test = node.body[0].test
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
                names = []
                for v in test.values:
                    if (isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.Not)
                            and isinstance(v.operand, ast.Name)):
                        names.append(v.operand.id)
                if set(names) == {"unique_day", "unique_month"}:
                    args = [a.arg for a in node.args.args]
                    if len(args) == 2:
                        month_name, coll_name = args
                        fixed = (
                            f"def {node.name}({month_name}, {coll_name}):\n"
                            f"    for i in {coll_name}:\n"
                            f"        if {month_name} in i:\n"
                            f"            if unique_day(i[1], {coll_name}):\n"
                            f"                return True\n"
                            f"    return False\n"
                        )
                        start, end = span(node)
                        out.append(source[:start] + fixed.rstrip("\n") + source[end:])

    return out

LEARNED.append(Rule("possible_birthdays_misuse", _learned_possible_birthdays_misuse, symptoms=('wrong')))


def _learned_unique_count_misconception(source):
    """Detects the 'subscript/slice membership' and 'uncalled function truthiness'
    misconceptions: checking uniqueness via `x in possible_birthdays[0]` or
    `x in possible_birthdays[1:]` instead of counting occurrences across all
    birthday pairs, and testing `not unique_day` / `not unique_month` (the
    function object itself, always truthy) instead of calling the function
    with arguments."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)

    def get_span(node):
        start = sum(len(lines[i]) for i in range(node.lineno - 1)) + node.col_offset
        end = sum(len(lines[i]) for i in range(node.end_lineno - 1)) + node.end_col_offset
        return start, end

    # Pattern 1: unique_day/unique_month indexing/slicing possible_birthdays
    # instead of counting matches across every entry.
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("unique_day", "unique_month"):
            found_bad = any(
                isinstance(n, ast.Subscript)
                and isinstance(n.value, ast.Name)
                and n.value.id == "possible_birthdays"
                for n in ast.walk(node)
            )
            if found_bad and node.args.args:
                params = [a.arg for a in node.args.args]
                target = params[0]
                new_func = (
                    f"def {node.name}({', '.join(params)}):\n"
                    f"    count = 0\n"
                    f"    for i in possible_birthdays:\n"
                    f"        if {target} in i:\n"
                    f"            count += 1\n"
                    f"    return count == 1\n"
                )
                start, end = get_span(node)
                out.append(source[:start] + new_func + source[end:])

    # Pattern 2: contains_unique_day (or similar) testing `not unique_day`
    # i.e. truthiness of the function object instead of calling it.
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            bad_unaryop = None
            for n in ast.walk(node):
                if (
                    isinstance(n, ast.UnaryOp)
                    and isinstance(n.op, ast.Not)
                    and isinstance(n.operand, ast.Name)
                    and n.operand.id in ("unique_day", "unique_month")
                ):
                    bad_unaryop = n
                    break
            if bad_unaryop is not None and node.args.args:
                params = [a.arg for a in node.args.args]
                month_param = params[0]
                new_func = (
                    f"def {node.name}({', '.join(params)}):\n"
                    f"    for i in possible_birthdays:\n"
                    f"        if {month_param} in i:\n"
                    f"            if unique_day(i[1], possible_birthdays):\n"
                    f"                return True\n"
                    f"    return False\n"
                )
                start, end = get_span(node)
                out.append(source[:start] + new_func + source[end:])

    return out

LEARNED.append(Rule("unique_count_misconception", _learned_unique_count_misconception, symptoms=('wrong')))
