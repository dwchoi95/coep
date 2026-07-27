from src.core.repair import Rule
LEARNED = []


def _learned_counter_var_name_confusion(source):
    """Fixes counting loops where (a) the running counter is compared against
    itself or an unrelated/undefined name instead of the function parameter,
    (b) the increment statement uses a mistyped/undefined variable instead of
    the counter, and (c) the counter's initialization is assigned to the wrong
    name (often shadowing the parameter) instead of the name actually used in
    the post-loop `if counter == 1` check."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    def get_span(node):
        return node.lineno, node.col_offset, node.end_lineno, node.end_col_offset

    def span_to_offsets(lines, lineno, col, end_lineno, end_col):
        start = sum(len(l) for l in lines[:lineno - 1]) + col
        end = sum(len(l) for l in lines[:end_lineno - 1]) + end_col
        return start, end

    lines = source.splitlines(keepends=True)
    edits = []  # (start, end, replacement)

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.args.args:
            continue
        param_name = func.args.args[0].arg

        # 1) Find the reliable counter name from a post-loop `if X == 1` check.
        counter_name = None
        for node in ast.walk(func):
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.Eq)
                    and isinstance(node.comparators[0], ast.Constant)
                    and node.comparators[0].value == 1
                    and isinstance(node.left, ast.Name)):
                counter_name = node.left.id
                break
        if not counter_name:
            continue

        # 2) Fix the initializer if it doesn't match the counter name.
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Constant)
                    and node.value.value == 0
                    and node.targets[0].id != counter_name):
                s, e = span_to_offsets(lines, *get_span(node.targets[0]))
                edits.append((s, e, counter_name))
                break  # only the first zero-init is the counter

        # 3) Within each for-loop, fix comparisons and increments.
        for forloop in ast.walk(func):
            if not isinstance(forloop, ast.For):
                continue
            for node in ast.walk(forloop):
                # comparison: `... == <Name>` where Name isn't the parameter
                if (isinstance(node, ast.Compare) and len(node.ops) == 1
                        and isinstance(node.ops[0], ast.Eq)
                        and isinstance(node.comparators[0], ast.Name)
                        and node.comparators[0].id != param_name):
                    right = node.comparators[0]
                    s, e = span_to_offsets(lines, *get_span(right))
                    edits.append((s, e, param_name))
                # increment: `X = X + 1` where X isn't the counter
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and isinstance(node.value, ast.BinOp)
                        and isinstance(node.value.op, ast.Add)
                        and isinstance(node.value.left, ast.Name)
                        and node.value.left.id == node.targets[0].id
                        and node.targets[0].id != counter_name):
                    tgt = node.targets[0]
                    left = node.value.left
                    s1, e1 = span_to_offsets(lines, *get_span(tgt))
                    s2, e2 = span_to_offsets(lines, *get_span(left))
                    edits.append((s1, e1, counter_name))
                    edits.append((s2, e2, counter_name))

    if not edits:
        return []

    edits.sort(key=lambda t: t[0], reverse=True)
    new_source = source
    for s, e, rep in edits:
        new_source = new_source[:s] + rep + new_source[e:]

    if new_source == source:
        return []
    return [new_source]

LEARNED.append(Rule("counter_var_name_confusion", _learned_counter_var_name_confusion, symptoms=('err:NameError', 'wrong')))


def _learned_uniqueness_off_by_zero(source):
    """count>1 miscoded as 'uniqueness' check; should be count!=1 (a count of 0 is not unique either)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    src_lines = source.splitlines(keepends=True)

    def get_span_text(node):
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1
        if start_line == end_line:
            return src_lines[start_line][node.col_offset:node.end_col_offset]
        text = src_lines[start_line][node.col_offset:]
        for ln in range(start_line + 1, end_line):
            text += src_lines[ln]
        text += src_lines[end_line][:node.end_col_offset]
        return text

    def replace_span(node, new_text):
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1
        new_lines = list(src_lines)
        if start_line == end_line:
            line = new_lines[start_line]
            new_lines[start_line] = line[:node.col_offset] + new_text + line[node.end_col_offset:]
        else:
            first = new_lines[start_line][:node.col_offset] + new_text
            last = new_lines[end_line][node.end_col_offset:]
            new_lines[start_line:end_line + 1] = [first + last]
        return "".join(new_lines)

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Gt):
                left = node.left
                right = node.comparators[0]
                is_count_var = isinstance(left, ast.Name) and 'count' in left.id.lower()
                is_one = isinstance(right, ast.Constant) and right.value == 1
                if is_count_var and is_one:
                    old_text = get_span_text(node)
                    left_text = get_span_text(left)
                    new_text = old_text.replace('>', '!=', 1) if '>' in old_text else f"{left_text}!=1"
                    new_source = replace_span(node, new_text)
                    if new_source != source:
                        out.append(new_source)
    return out

LEARNED.append(Rule("uniqueness_off_by_zero", _learned_uniqueness_off_by_zero, symptoms=('wrong')))


def _learned_count_threshold_inverted(source):
    """Fixes the 'off-by-one uniqueness check' misconception: counting
    occurrences and testing `if count > 1: return False else: return True`
    instead of the equivalent-when-count>=1 but wrong-when-count==0 form
    `if count == 1: return True else: return False`. Rewrites every such
    If node to compare with `==` and swap the True/False branches."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)

    def get_bool(node):
        # Return True/False if node is a literal boolean return value, else None
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return node.value
        # Python <3.8 style True/False as Name
        if isinstance(node, ast.NameConstant) and isinstance(node.value, bool):
            return node.value
        return None

    matches = []
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
        rhs = test.comparators[0]
        rhs_val = None
        if isinstance(rhs, ast.Constant) and isinstance(rhs.value, (int, float)):
            rhs_val = rhs.value
        if rhs_val is None:
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
            continue
        if len(node.orelse) != 1 or not isinstance(node.orelse[0], ast.Return):
            continue
        body_val = get_bool(node.body[0].value)
        else_val = get_bool(node.orelse[0].value)
        if body_val is None or else_val is None:
            continue
        # Pattern: if X > N: return False else: return True
        if body_val is False and else_val is True:
            matches.append((node, test.left, rhs_val))

    if not matches:
        return []

    # Apply edits from bottom to top so earlier spans remain valid
    matches.sort(key=lambda m: m[0].lineno, reverse=True)

    src = source
    for node, left_expr, rhs_val in matches:
        start_line = node.lineno
        end_line = node.end_lineno
        start_col = node.col_offset
        end_col = node.end_col_offset

        try:
            left_text = ast.get_source_segment(source, left_expr)
        except Exception:
            left_text = None
        if not left_text:
            continue

        indent = " " * start_col
        new_text = (
            f"if {left_text} == {rhs_val}:\n"
            f"{indent}    return True\n"
            f"{indent}else:\n"
            f"{indent}    return False"
        )

        src_lines = src.splitlines(keepends=True)
        before = "".join(src_lines[:start_line - 1])
        after = "".join(src_lines[end_line:])
        first_line = src_lines[start_line - 1]
        last_line = src_lines[end_line - 1]

        prefix = first_line[:start_col]
        suffix = last_line[end_col:]

        src = before + prefix + new_text + suffix + after

    if src == source:
        return []
    return [src]

LEARNED.append(Rule("count_threshold_inverted", _learned_count_threshold_inverted, symptoms=('wrong',)))
