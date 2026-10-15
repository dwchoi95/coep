from src.core.repair import Rule
LEARNED = []


def _learned_bool_flag_return_literal_true(source):
    """Detects functions that use a boolean flag (initialized False, flipped to
    True inside a loop to signal 'found/unique') but then unconditionally
    `return True` at the end instead of returning the flag variable itself,
    so the function always reports success even when the flag never flipped."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    edits = []  # (start_offset, end_offset, replacement_text)
    lines = source.splitlines(keepends=True)

    def offset_of(lineno, col):
        return sum(len(l) for l in lines[:lineno - 1]) + col

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        # find a top-level flag variable initialized to False
        flag_name = None
        for stmt in node.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is False):
                flag_name = stmt.targets[0].id
                break
        if flag_name is None:
            continue

        # check the flag gets set True somewhere inside a loop in this function
        flipped_in_loop = False
        for stmt in node.body:
            if isinstance(stmt, (ast.For, ast.While)):
                for sub in ast.walk(stmt):
                    if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                            and isinstance(sub.targets[0], ast.Name)
                            and sub.targets[0].id == flag_name
                            and isinstance(sub.value, ast.Constant)
                            and sub.value.value is True):
                        flipped_in_loop = True
                        break
            if flipped_in_loop:
                break
        if not flipped_in_loop:
            continue

        # last statement must be `return True` (literal)
        last = node.body[-1]
        if (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            start = offset_of(last.lineno, last.col_offset)
            end = offset_of(last.end_lineno, last.end_col_offset)
            edits.append((start, end, f"return {flag_name}"))

    if not edits:
        return []

    # apply from last to first so earlier offsets stay valid
    edits.sort(key=lambda e: e[0], reverse=True)
    new_source = source
    for start, end, repl in edits:
        new_source = new_source[:start] + repl + new_source[end:]

    if new_source == source:
        return []
    return [new_source]

LEARNED.append(Rule("bool_flag_return_literal_true", _learned_bool_flag_return_literal_true, symptoms=('wrong')))


def _learned_uniqueness_count_gt1(source):
    """Detects the 'exists-at-least-one-duplicate' misconception: using
    `if count>1: X=False else: X=True` to decide uniqueness, which wrongly
    treats a zero-count case as unique. The correct test is `count==1`."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.matches = []

        def visit_If(self, node):
            test = node.test
            if (isinstance(test, ast.Compare) and len(test.ops) == 1 and
                    isinstance(test.ops[0], ast.Gt) and
                    isinstance(test.comparators[0], ast.Constant) and
                    test.comparators[0].value == 1):
                # body should be single assign to False
                if (len(node.body) == 1 and isinstance(node.body[0], ast.Assign) and
                        isinstance(node.body[0].value, ast.Constant) and
                        node.body[0].value.value is False and
                        len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Assign) and
                        isinstance(node.orelse[0].value, ast.Constant) and
                        node.orelse[0].value.value is True):
                    target_names_body = [t.id for t in node.body[0].targets if isinstance(t, ast.Name)]
                    target_names_else = [t.id for t in node.orelse[0].targets if isinstance(t, ast.Name)]
                    if target_names_body == target_names_else and len(target_names_body) == 1:
                        var_name = target_names_body[0]
                        count_expr = ast.unparse(test.left)
                        self.matches.append((node, var_name, count_expr))
            self.generic_visit(node)

    v = Visitor()
    v.visit(tree)
    if not v.matches:
        return []

    lines = source.splitlines(keepends=True)

    def get_span(node):
        start_line = node.lineno - 1
        start_col = node.col_offset
        end_line = node.end_lineno - 1
        end_col = node.end_col_offset
        return start_line, start_col, end_line, end_col

    for node, var_name, count_expr in v.matches:
        start_line, start_col, end_line, end_col = get_span(node)
        # Determine indentation from the original if statement
        indent = ' ' * start_col
        new_code = (
            f"if {count_expr}==1:\n"
            f"{indent}    {var_name}=True\n"
            f"{indent}else:\n"
            f"{indent}    {var_name}=False"
        )

        if start_line == end_line:
            orig_line = lines[start_line]
            new_line = orig_line[:start_col] + new_code + orig_line[end_col:]
            new_lines = lines[:start_line] + [new_line] + lines[start_line + 1:]
        else:
            first_line = lines[start_line][:start_col]
            last_line = lines[end_line][end_col:]
            new_lines = (
                lines[:start_line] +
                [first_line + new_code + last_line] +
                lines[end_line + 1:]
            )

        new_source = ''.join(new_lines)
        if new_source != source:
            out.append(new_source)

    return out


LEARNED.append(Rule("uniqueness_count_gt1", _learned_uniqueness_count_gt1, symptoms=('wrong')))


def _learned_counter_offby_one_threshold(source):
    """Misconception: a loop counts matching items into a counter
    initialized to 1 (instead of 0), and a later `if counter > N` check
    is used to decide 'uniqueness', returning False/True in the wrong
    branches. The counter should start at 0 and the uniqueness check
    should be `counter == 1` with the True/False branches swapped."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)

    def get_span(node):
        start = sum(len(l) for l in lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(l) for l in lines[:node.end_lineno - 1]) + node.end_col_offset
        return start, end

    def first_return(body):
        for b in body:
            if isinstance(b, ast.Return):
                return b
        return None

    edits = []
    changed = False

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for i, stmt in enumerate(func.body):
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value == 1):
                varname = stmt.targets[0].id
                for later in func.body[i + 1:]:
                    if (isinstance(later, ast.If)
                            and isinstance(later.test, ast.Compare)
                            and isinstance(later.test.left, ast.Name)
                            and later.test.left.id == varname
                            and len(later.test.ops) == 1
                            and isinstance(later.test.ops[0], ast.Gt)
                            and isinstance(later.test.comparators[0], ast.Constant)):
                        r_if = first_return(later.body)
                        r_else = first_return(later.orelse)
                        if r_if is None or r_else is None:
                            continue
                        changed = True
                        vs, ve = get_span(stmt.value)
                        edits.append((vs, ve, "0"))
                        ts, te = get_span(later.test)
                        edits.append((ts, te, f"{varname} == 1"))
                        s1, e1 = get_span(r_if.value)
                        s2, e2 = get_span(r_else.value)
                        v1 = source[s1:e1]
                        v2 = source[s2:e2]
                        edits.append((s1, e1, v2))
                        edits.append((s2, e2, v1))

    if not changed:
        return []

    edits.sort(key=lambda e: e[0], reverse=True)
    new_source = source
    for s, e, rep in edits:
        new_source = new_source[:s] + rep + new_source[e:]
    return [new_source]

LEARNED.append(Rule("counter_offby_one_threshold", _learned_counter_offby_one_threshold, symptoms=('wrong')))
