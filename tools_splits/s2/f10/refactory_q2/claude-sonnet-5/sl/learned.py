from src.core.repair import Rule
LEARNED = []


def _learned_loop_accumulator_return_true(source):
    """Function accumulates matches in a loop (returning False on duplicates)
    but then unconditionally returns True at the end instead of checking
    that exactly one match was actually accumulated (len(acc) == 1)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)

    def get_span(node):
        start = sum(len(l) for l in lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(l) for l in lines[:node.end_lineno - 1]) + node.end_col_offset
        return start, end

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if not func.body:
            continue
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue

        # find an accumulator variable: one that is reassigned via AugAssign
        # (e.g. `days += (...)`) inside a loop in the function body
        acc_name = None
        for node in ast.walk(func):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                acc_name = node.target.id
                break

        if acc_name is None:
            continue

        start, end = get_span(last)
        replacement = f"return len({acc_name}) == 1"
        new_source = source[:start] + replacement + source[end:]
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("loop_accumulator_return_true", _learned_loop_accumulator_return_true, symptoms=('wrong')))


def _learned_count_threshold_polarity(source):
    """Fixes the 'off-by-reversal' pattern where uniqueness is checked via
    `if count > 1: check = False else: check = True` instead of the correct
    `if count == 1: check = True else: check = False`. The comparison
    operator/threshold and the True/False branches are both inverted from
    what's needed to express 'exactly one occurrence means unique'."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)

    def get_segment(node):
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1
        if start_line == end_line:
            return lines[start_line][node.col_offset:node.end_col_offset]
        seg = lines[start_line][node.col_offset:]
        for i in range(start_line + 1, end_line):
            seg += lines[i]
        seg += lines[end_line][:node.end_col_offset]
        return seg

    def offset_of(lineno, col):
        off = sum(len(l) for l in lines[:lineno - 1])
        return off + col

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Gt):
            continue
        comparator = test.comparators[0]
        if not (isinstance(comparator, ast.Constant) and comparator.value == 1):
            continue
        if len(node.body) != 1 or len(node.orelse) != 1:
            continue
        body_stmt = node.body[0]
        else_stmt = node.orelse[0]
        if not (isinstance(body_stmt, ast.Assign) and isinstance(else_stmt, ast.Assign)):
            continue
        if len(body_stmt.targets) != 1 or len(else_stmt.targets) != 1:
            continue
        bt, et = body_stmt.targets[0], else_stmt.targets[0]
        if not (isinstance(bt, ast.Name) and isinstance(et, ast.Name) and bt.id == et.id):
            continue
        bv, ev = body_stmt.value, else_stmt.value
        if not (isinstance(bv, ast.Constant) and isinstance(ev, ast.Constant)):
            continue
        if not (bv.value is False and ev.value is True):
            continue

        var_name = bt.id
        count_expr = get_segment(test.left)
        indent = " " * node.col_offset

        replacement = (
            f"if {count_expr} == 1:\n"
            f"{indent}    {var_name}=True\n"
            f"{indent}else:\n"
            f"{indent}    {var_name}=False"
        )

        start_off = offset_of(node.lineno, node.col_offset)
        end_off = offset_of(node.end_lineno, node.end_col_offset)
        new_source = source[:start_off] + replacement + source[end_off:]
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("count_threshold_polarity", _learned_count_threshold_polarity, symptoms=('wrong')))
