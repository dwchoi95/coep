from src.core.repair import Rule
LEARNED = []


def _learned_binarysearch_zero_exit(source):
    """Binary search for the maximal value satisfying a monotone predicate that
    terminates on 'if left == right or res == 0: return mid' (an exact-match /
    left==right escape) instead of the standard 'while left <= right' loop that
    tracks the best feasible 'ans' and updates the bounds with 'res >= 0'.
    Also fixes the paired base case that returns 0 (a "feasible" sentinel)
    instead of a negative/"infeasible" sentinel when the search parameter is 0."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.While):
                continue
            test = node.test
            is_infinite = isinstance(test, ast.Constant) and test.value is True
            if not is_infinite:
                continue

            mid_name = None
            res_name = None
            bad_if = None
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name):
                    tgt = stmt.targets[0].id
                    if 'mid' in tgt:
                        mid_name = tgt
                    elif tgt.startswith('res'):
                        res_name = tgt
                if isinstance(stmt, ast.If):
                    try:
                        cond_src = ast.unparse(stmt.test)
                    except Exception:
                        cond_src = ''
                    has_return = any(isinstance(s, ast.Return) for s in stmt.body)
                    if has_return and ('== 0' in cond_src or 'right' in cond_src):
                        bad_if = stmt

            if bad_if is None or mid_name is None or res_name is None:
                continue

            # locate the call expression assigned to res_name (the predicate call)
            call_expr = None
            for stmt in node.body:
                if (isinstance(stmt, ast.Assign)
                        and isinstance(stmt.targets[0], ast.Name)
                        and stmt.targets[0].id == res_name):
                    try:
                        call_expr = ast.unparse(stmt.value)
                    except Exception:
                        call_expr = None

            if call_expr is None:
                continue

            start = node.col_offset
            end = node.end_col_offset
            lineno = node.lineno
            end_lineno = node.end_lineno

            lines = source.splitlines(keepends=True)
            indent = ' ' * node.col_offset

            replacement = (
                f"ans = 0\n"
                f"{indent}while left <= right:\n"
                f"{indent}    {mid_name} = (left + right) // 2\n"
                f"{indent}    {res_name} = {call_expr}\n"
                f"{indent}    if {res_name} >= 0:\n"
                f"{indent}        ans = {mid_name}\n"
                f"{indent}        left = {mid_name} + 1\n"
                f"{indent}    else:\n"
                f"{indent}        right = {mid_name} - 1\n"
                f"{indent}return ans"
            )

            # splice the replacement in place of the original while-loop text
            full_start = sum(len(l) for l in lines[:lineno - 1]) + start
            full_end = sum(len(l) for l in lines[:end_lineno - 1]) + end
            new_source = source[:full_start] + replacement + source[full_end:]

            # also fix a paired base-case "if <param> == 0: return 0" inside the
            # same function (the false "feasible" sentinel bug)
            for inner in ast.walk(func):
                if isinstance(inner, ast.If):
                    try:
                        icond = ast.unparse(inner.test)
                    except Exception:
                        icond = ''
                    if '== 0' in icond and len(inner.body) == 1 and isinstance(inner.body[0], ast.Return):
                        try:
                            rv = ast.unparse(inner.body[0].value)
                        except Exception:
                            rv = None
                        if rv == '0':
                            old_ret = "return 0"
                            new_ret = "return -1"
                            if old_ret in new_source:
                                new_source = new_source.replace(old_ret, new_ret, 1)

            if new_source != source:
                out.append(new_source)

    return out

LEARNED.append(Rule("binarysearch_zero_exit", _learned_binarysearch_zero_exit, symptoms=('wrong',)))
