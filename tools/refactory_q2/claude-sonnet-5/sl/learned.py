from src.core.repair import Rule
LEARNED = []


def _learned_counter_var_confusion(source):
    """In simple counting-loop functions (acc = 0; for ...: if x == wrong_var: wrong_target = wrong_target + 1;
    if acc == 1: ...), the student compares against the accumulator/itself (or shadows the
    parameter with the same-named accumulator) instead of the real parameter, and increments
    an unrelated/undefined variable instead of the accumulator. This rule locates that
    pattern and rewires the comparator, the increment statement, and the final check so they
    all refer to the correct names, renaming the accumulator when it shadows the parameter."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)
    cum = [0]
    for l in lines:
        cum.append(cum[-1] + len(l))

    def offset(lineno, col):
        return cum[lineno - 1] + col

    def span(node):
        return offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset)

    edits = []  # (start, end, text)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        params = [a.arg for a in node.args.args]
        if len(params) != 2:
            continue

        # find accumulator: first top-level `name = 0`
        acc_stmt = None
        for stmt in node.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant) and stmt.value.value == 0):
                acc_stmt = stmt
                break
        if acc_stmt is None:
            continue
        acc_name = acc_stmt.targets[0].id

        # find list_param via a For whose iter is range(len(Name))
        list_param = None
        for_node = None
        for sub in ast.walk(node):
            if isinstance(sub, ast.For) and isinstance(sub.iter, ast.Call):
                call = sub.iter
                if (isinstance(call.func, ast.Name) and call.func.id == 'range'
                        and call.args and isinstance(call.args[0], ast.Call)):
                    inner = call.args[0]
                    if (isinstance(inner.func, ast.Name) and inner.func.id == 'len'
                            and inner.args and isinstance(inner.args[0], ast.Name)):
                        list_param = inner.args[0].id
                        for_node = sub
                        break
        if for_node is None or list_param not in params:
            continue
        target_param = next((p for p in params if p != list_param), None)
        if target_param is None:
            continue

        # find nested if with Eq compare against a Name inside the for loop
        comp_if = None
        for sub in ast.walk(for_node):
            if (isinstance(sub, ast.If) and isinstance(sub.test, ast.Compare)
                    and len(sub.test.ops) == 1 and isinstance(sub.test.ops[0], ast.Eq)
                    and isinstance(sub.test.comparators[0], ast.Name)):
                comp_if = sub
                break
        if comp_if is None:
            continue
        comparator_node = comp_if.test.comparators[0]

        # find increment statement inside comp_if.body: target = target + 1 (any names)
        incr_stmt = None
        for st in comp_if.body:
            if (isinstance(st, ast.Assign) and len(st.targets) == 1
                    and isinstance(st.targets[0], ast.Name)
                    and isinstance(st.value, ast.BinOp) and isinstance(st.value.op, ast.Add)
                    and isinstance(st.value.left, ast.Name)
                    and isinstance(st.value.right, ast.Constant) and st.value.right.value == 1):
                incr_stmt = st
                break
        if incr_stmt is None:
            continue

        # find final if (top-level) comparing some Name == 1
        final_if = None
        for stmt in node.body:
            if (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare)
                    and len(stmt.test.ops) == 1 and isinstance(stmt.test.ops[0], ast.Eq)
                    and isinstance(stmt.test.left, ast.Name)
                    and isinstance(stmt.test.comparators[0], ast.Constant)
                    and stmt.test.comparators[0].value == 1):
                final_if = stmt
                break
        if final_if is None:
            continue
        final_name_node = final_if.test.left

        shadow = (target_param == acc_name)
        found_any = False

        if shadow:
            new_acc_name = acc_name + "_count"
            s, e = span(acc_stmt.targets[0])
            edits.append((s, e, new_acc_name))
            found_any = True
            s, e = span(incr_stmt.targets[0])
            edits.append((s, e, new_acc_name))
            s, e = span(incr_stmt.value.left)
            edits.append((s, e, new_acc_name))
            s, e = span(final_name_node)
            edits.append((s, e, new_acc_name))
        else:
            if comparator_node.id != target_param:
                s, e = span(comparator_node)
                edits.append((s, e, target_param))
                found_any = True
            if incr_stmt.targets[0].id != acc_name:
                s, e = span(incr_stmt.targets[0])
                edits.append((s, e, acc_name))
                s, e = span(incr_stmt.value.left)
                edits.append((s, e, acc_name))
                found_any = True
            if final_name_node.id != acc_name:
                s, e = span(final_name_node)
                edits.append((s, e, acc_name))
                found_any = True

    if not edits:
        return []

    edits.sort(key=lambda t: t[0], reverse=True)
    new_source = source
    for s, e, text in edits:
        new_source = new_source[:s] + text + new_source[e:]

    if new_source == source:
        return []
    return [new_source]


LEARNED.append(Rule("counter_var_confusion", _learned_counter_var_confusion, symptoms=('err:NameError', 'wrong')))


def _learned_uniqueness_count_gt1_to_neq1(source):
    """Off-by-logic: uniqueness check written as `count>1` (false for count==0)
    instead of `count!=1`, so a value absent from the list is wrongly
    considered unique."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    src_lines = source.splitlines(keepends=True)

    def get_span(node):
        start = sum(len(l) for l in src_lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(l) for l in src_lines[:node.end_lineno - 1]) + node.end_col_offset
        return start, end

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.matches = []

        def visit_Compare(self, node):
            if (len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt)
                    and len(node.comparators) == 1):
                right = node.comparators[0]
                if isinstance(right, ast.Constant) and right.value == 1:
                    self.matches.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    if not finder.matches:
        return []

    new_source = source
    # Apply edits from rightmost to leftmost to keep offsets valid
    for node in sorted(finder.matches, key=lambda n: n.col_offset, reverse=True):
        start, end = get_span(node)
        left_src = ast.get_source_segment(source, node.left) if hasattr(node, 'left') else None
        left_text = source[get_span(node.left)[0]:get_span(node.left)[1]]
        replacement = f"{left_text}!=1"
        new_source = new_source[:start] + replacement + new_source[end:]

    if new_source != source:
        out.append(new_source)
    return out

LEARNED.append(Rule("uniqueness_count_gt1_to_neq1", _learned_uniqueness_count_gt1_to_neq1, symptoms=('wrong')))


def _learned_index_vs_count_and_uncalled_bool(source):
    """Misconception: checking membership by indexing a birthdays collection
    with a literal position (e.g. possible_birthdays[0]/[1]) instead of
    counting matches across every birthday tuple, and testing helper
    functions as truthy objects (e.g. `if not unique_day and not
    unique_month:`) instead of actually calling them."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)

    def node_text(node):
        if node.lineno == node.end_lineno:
            return lines[node.lineno - 1][node.col_offset:node.end_col_offset]
        text = lines[node.lineno - 1][node.col_offset:]
        for ln in range(node.lineno, node.end_lineno - 1):
            text += lines[ln]
        text += lines[node.end_lineno - 1][:node.end_col_offset]
        return text

    def replace_node(node, new_text):
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1
        before = ''.join(lines[:start_line])
        after = ''.join(lines[end_line + 1:])
        if not new_text.endswith('\n'):
            new_text += '\n'
        return before + new_text + after

    func_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.If):
            continue
        if_node = node.body[0]
        test = if_node.test

        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.In)
                and isinstance(test.comparators[0], ast.Subscript)
                and isinstance(getattr(test.comparators[0], 'slice', None), ast.Constant)
                and isinstance(test.comparators[0].slice.value, int)
                and len(node.args.args) >= 2):
            cond_expr = node_text(test.left)
            coll_name = node.args.args[1].arg
            params = ', '.join(a.arg for a in node.args.args)
            indent = ' ' * node.col_offset
            new_func = (
                f"{indent}def {node.name}({params}):\n"
                f"{indent}    count = 0\n"
                f"{indent}    for i in {coll_name}:\n"
                f"{indent}        if {cond_expr} in i:\n"
                f"{indent}            count += 1\n"
                f"{indent}    return count == 1\n"
            )
            out.append(replace_node(node, new_func))
            continue

        if (isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And)
                and len(test.values) == 2
                and all(isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.Not)
                        and isinstance(v.operand, ast.Name) for v in test.values)
                and all(v.operand.id in func_names for v in test.values)
                and len(node.args.args) >= 2):
            f1 = test.values[0].operand.id
            params = [a.arg for a in node.args.args]
            month_p, coll_p = params[0], params[1]
            indent = ' ' * node.col_offset
            new_func = (
                f"{indent}def {node.name}({', '.join(params)}):\n"
                f"{indent}    for i in {coll_p}:\n"
                f"{indent}        if {month_p} in i:\n"
                f"{indent}            if {f1}(i[1], {coll_p}):\n"
                f"{indent}                return True\n"
                f"{indent}    return False\n"
            )
            out.append(replace_node(node, new_func))

    return out

LEARNED.append(Rule("index_vs_count_and_uncalled_bool", _learned_index_vs_count_and_uncalled_bool, symptoms=('wrong',)))


def _learned_missing_else_return_false(source):
    """Function checks a condition, returns True inside an `if` with no
    `else`/following `return`, so on the False path the function falls
    through and implicitly returns None instead of False."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = source.splitlines(keepends=True)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            if not body:
                continue
            last = body[-1]
            if isinstance(last, ast.If) and not last.orelse:
                returns_true = any(
                    isinstance(stmt, ast.Return)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is True
                    for stmt in ast.walk(last)
                )
                if returns_true:
                    indent = ' ' * last.col_offset
                    insertion_line = last.end_lineno  # 1-indexed, insert after block
                    new_line = f"{indent}return False\n"
                    new_lines = lines[:insertion_line] + [new_line] + lines[insertion_line:]
                    out.append(''.join(new_lines))
    return out

LEARNED.append(Rule("missing_else_false", _learned_missing_else_return_false, symptoms=('wrong')))
