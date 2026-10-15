from src.core.repair import Rule
LEARNED = []


def _learned_counting_loop_var_confusion(source):
    """Fixes counting-loop variable mix-ups: comparing a list item against
    the counter variable itself instead of the intended function parameter,
    incrementing an undefined/mismatched variable instead of the counter,
    using some other leftover/undefined variable name in a later check, and
    a counter variable that shadows the function's own parameter name."""
    import ast
    import builtins as _builtins
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)
    line_starts = [0]
    for ln in lines:
        line_starts.append(line_starts[-1] + len(ln))

    def span(node):
        start = line_starts[node.lineno - 1] + node.col_offset
        end = line_starts[node.end_lineno - 1] + node.end_col_offset
        return start, end

    edits = []
    changed = False
    builtin_names = set(vars(_builtins)) | {"True", "False", "None"}

    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = [a.arg for a in fn.args.args]
        if not params:
            continue
        param_name = params[0]

        counter_name = None
        counter_assign = None
        for stmt in fn.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value == 0):
                counter_name = stmt.targets[0].id
                counter_assign = stmt
                break
        if counter_name is None:
            continue

        shadow = counter_name == param_name
        final_name = ("_" + counter_name + "_count") if shadow else counter_name

        if shadow:
            s, e = span(counter_assign.targets[0])
            edits.append((s, e, final_name))
            changed = True

        assigned_names = set(params)
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                assigned_names.add(node.targets[0].id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                assigned_names.add(node.target.id)

        for node in ast.walk(fn):
            # comparing a list item to the counter itself instead of the parameter
            if isinstance(node, ast.Compare) and not shadow:
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Name) and comparator.id == counter_name:
                        s, e = span(comparator)
                        edits.append((s, e, param_name))
                        changed = True

            # incrementing a variable that doesn't match the counter
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.BinOp)
                    and isinstance(node.value.op, ast.Add)
                    and isinstance(node.value.left, ast.Name)
                    and node.targets[0].id == node.value.left.id
                    and node.targets[0].id != counter_name):
                s1, e1 = span(node.targets[0])
                s2, e2 = span(node.value.left)
                edits.append((s1, e1, final_name))
                edits.append((s2, e2, final_name))
                changed = True

            # a correctly-named counter occurrence that must follow the rename
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == counter_name
                    and node is not counter_assign):
                s, e = span(node.targets[0])
                edits.append((s, e, final_name))
                if (isinstance(node.value, ast.BinOp)
                        and isinstance(node.value.left, ast.Name)
                        and node.value.left.id == counter_name):
                    s2, e2 = span(node.value.left)
                    edits.append((s2, e2, final_name))
                changed = True

            # any other leftover/undefined variable reference -> the counter
            if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                    and node.id not in assigned_names
                    and node.id not in builtin_names
                    and node.id != param_name):
                s, e = span(node)
                edits.append((s, e, final_name))
                changed = True

    if not changed:
        return []

    edits.sort(key=lambda x: -x[0])
    out_source = source
    for s, e, repl in edits:
        out_source = out_source[:s] + repl + out_source[e:]
    return [out_source] if out_source != source else []


LEARNED.append(Rule("counting_loop_var_confusion", _learned_counting_loop_var_confusion, symptoms=('err:NameError', 'wrong')))


def _learned_count_gt1_misuse(source):
    """Detects 'if count > 1: x = False else: x = True' misuse (inverted uniqueness check).
    The correct logic for "is this value unique" is count == 1 -> True, else False.
    This rule rewrites the '> 1' comparison to '== 1' and swaps the True/False
    constants in the body/orelse branches accordingly."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    targets = []  # (test_node, body_assign_value, orelse_assign_value)
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            test = node.test
            if (len(test.ops) == 1 and isinstance(test.ops[0], ast.Gt) and
                    len(test.comparators) == 1 and
                    isinstance(test.comparators[0], ast.Constant) and
                    test.comparators[0].value == 1):
                if (len(node.body) == 1 and isinstance(node.body[0], ast.Assign) and
                        len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Assign)):
                    b_assign = node.body[0]
                    o_assign = node.orelse[0]
                    if (isinstance(b_assign.value, ast.Constant) and
                            isinstance(b_assign.value.value, bool) and
                            isinstance(o_assign.value, ast.Constant) and
                            isinstance(o_assign.value.value, bool) and
                            b_assign.value.value != o_assign.value.value):
                        targets.append((test, b_assign.value, o_assign.value))

    if not targets:
        return []

    lines = source.splitlines(keepends=True)
    line_starts = [0]
    for l in lines:
        line_starts.append(line_starts[-1] + len(l))

    def node_span(n):
        start = line_starts[n.lineno - 1] + n.col_offset
        end = line_starts[n.end_lineno - 1] + n.end_col_offset
        return start, end

    replacements = []
    for test, b_val, o_val in targets:
        start, end = node_span(test)
        left_text = ast.get_source_segment(source, test.left)
        new_text = f"{left_text}==1"
        replacements.append((start, end, new_text))

        b_start, b_end = node_span(b_val)
        o_start, o_end = node_span(o_val)
        b_text = 'True' if b_val.value else 'False'
        o_text = 'True' if o_val.value else 'False'
        # swap: body (previously for count>1) should now hold the orelse's old text, and vice versa
        replacements.append((b_start, b_end, o_text))
        replacements.append((o_start, o_end, b_text))

    replacements.sort(key=lambda x: x[0], reverse=True)
    new_source = source
    for start, end, text in replacements:
        new_source = new_source[:start] + text + new_source[end:]

    return [new_source]

LEARNED.append(Rule("count_gt1_misuse", _learned_count_gt1_misuse, symptoms=('wrong',)))


def _learned_offbyone_unique_counter(source):
    """Misconception: (1) a match-counter is seeded at 1 instead of 0 and
    then compared with an arbitrary threshold (e.g. `x > 2`) to decide
    uniqueness, instead of starting at 0 and checking `count == 1`; and
    (2) a "does any element satisfy this?" loop uses an `if/else` whose
    `else` branch returns immediately, so only the first list element is
    ever examined instead of scanning the whole collection before giving
    up and returning False."""
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

    edits = []

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        body = func.body

        # Pattern 1: counter seeded at 1, later compared with '>' threshold.
        for i, stmt in enumerate(body):
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value == 1):
                name = stmt.targets[0].id
                for later in body[i + 1:]:
                    if isinstance(later, ast.If):
                        test = later.test
                        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                                and isinstance(test.ops[0], ast.Gt)
                                and isinstance(test.left, ast.Name)
                                and test.left.id == name):
                            cs, ce = span(stmt.value)
                            edits.append((cs, ce, "0"))
                            s, e = span(later)
                            indent = ' ' * later.col_offset
                            new_if = (f"if {name} == 1:\n{indent}    return True\n"
                                      f"{indent}else:\n{indent}    return False")
                            edits.append((s, e, new_if))

        # Pattern 2: for-loop whose if/else returns after only the 1st element.
        for node in ast.walk(func):
            if isinstance(node, ast.For) and node.body:
                ifnode = node.body[0]
                if (isinstance(ifnode, ast.If) and ifnode.orelse
                        and len(ifnode.orelse) == 1
                        and isinstance(ifnode.orelse[0], ast.Return)):
                    orelse_ret = ifnode.orelse[0]
                    s, e = span(ifnode)
                    test_s, test_e = span(ifnode.test)
                    body_s, body_e = span(ifnode.body[0])
                    indent = ' ' * ifnode.col_offset
                    new_if = (f"if {source[test_s:test_e]}:\n"
                              f"{indent}    {source[body_s:body_e]}")
                    edits.append((s, e, new_if))
                    for_s, for_e = span(node)
                    ret_s, ret_e = span(orelse_ret)
                    for_indent = ' ' * node.col_offset
                    edits.append((for_e, for_e, f"\n{for_indent}{source[ret_s:ret_e]}"))

    if not edits:
        return []

    edits.sort(key=lambda t: t[0], reverse=True)
    new_source = source
    for s, e, rep in edits:
        new_source = new_source[:s] + rep + new_source[e:]
    return [new_source]

LEARNED.append(Rule("offbyone_unique_counter", _learned_offbyone_unique_counter, symptoms=('wrong',)))


def _learned_list_of_pairs_iteration(source):
    """Functions taking a `possible_birthdays`-style list-of-pairs parameter
    either (a) test membership by indexing a fixed slot of the list itself
    (e.g. `x in possible_birthdays[0]`) instead of iterating over each pair
    and counting matches, or (b) use undeclared placeholder names (e.g. `x`,
    `y`) in the boolean test instead of iterating over the pairs and
    checking membership. Both stem from never actually looping over the
    list-of-tuples structure; rewrite the offending `if` into the proper
    iterate-and-count / iterate-and-check form."""
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

    def indent_of(node):
        return " " * node.col_offset

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if "possible_birthdays" not in params:
            continue
        other_params = [p for p in params if p != "possible_birthdays"]
        if not other_params:
            continue
        var = other_params[0]

        for node in ast.walk(func):
            if not isinstance(node, ast.If):
                continue
            test = node.test

            # Pattern A: `x in possible_birthdays[N]` (direct slot index instead
            # of iterating over every pair)
            if (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.In)
                    and isinstance(test.comparators[0], ast.Subscript)):
                sub = test.comparators[0]
                if isinstance(sub.value, ast.Name) and sub.value.id == "possible_birthdays":
                    ind = indent_of(node)
                    new_code = (
                        f"count = 0\n"
                        f"{ind}for i in possible_birthdays:\n"
                        f"{ind}    if {var} in i:\n"
                        f"{ind}        count += 1\n"
                        f"{ind}if count == 1:\n"
                        f"{ind}    return True\n"
                        f"{ind}else:\n"
                        f"{ind}    return False"
                    )
                    start, end = get_span(node)
                    out.append(source[:start] + new_code + source[end:])
                    continue

            # Pattern B: boolean test referencing undeclared placeholder names
            names_used = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
            known = set(params) | {"True", "False"}
            if names_used and not names_used.issubset(known):
                ind = indent_of(node)
                new_code = (
                    f"for i in possible_birthdays:\n"
                    f"{ind}    if {var} in i:\n"
                    f"{ind}        if unique_day(i[1], possible_birthdays):\n"
                    f"{ind}            return True\n"
                    f"{ind}return False"
                )
                start, end = get_span(node)
                out.append(source[:start] + new_code + source[end:])

    return out

LEARNED.append(Rule("list_of_pairs_iteration", _learned_list_of_pairs_iteration, symptoms=('err:IndexError', 'err:NameError', 'wrong')))


def _learned_add_missing_return_false(source):
    """Boolean-returning function only returns True inside an if-branch (with
    no else) and otherwise falls through, implicitly returning None instead of
    an explicit False for the negative case."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)

    def contains_return_true(node):
        for n in ast.walk(node):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and n.value.value is True:
                return True
        return False

    def contains_return_false(node):
        for n in ast.walk(node):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and n.value.value is False:
                return True
        return False

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if not func.body:
            continue
        last = func.body[-1]
        if not isinstance(last, ast.If):
            continue
        if last.orelse:
            continue
        if not contains_return_true(last):
            continue
        if contains_return_false(last):
            continue
        # The if-branch returns True but there is no fallback return for the
        # False case anywhere else in the function -> function may return None.
        indent = ' ' * last.col_offset
        insert_idx = last.end_lineno  # 0-indexed position right after the if-block
        new_lines = list(lines)
        insertion = f"{indent}return False\n"
        new_lines.insert(insert_idx, insertion)
        candidate = ''.join(new_lines)
        if candidate != source:
            out.append(candidate)
    return out

LEARNED.append(Rule("add_missing_return_false", _learned_add_missing_return_false, symptoms=('wrong', 'err:None')))


def _learned_uniqueness_fix(source):
    """Misconception: treating a "no matches" count as acceptable by using
    `> 1` instead of `!= 1` when checking that something occurs exactly once,
    and forgetting to initialize an accumulator/result variable before a
    for-loop whose body (not guaranteed to execute) is the only place that
    assigns it, which raises UnboundLocalError when the loop runs zero times."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    edits = []  # list of (node, kind)

    # Pattern 1: `X > 1` -> `X != 1`
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            comparator = node.comparators[0]
            if isinstance(comparator, ast.Constant) and comparator.value == 1:
                edits.append((node, 'gt_to_ne'))

    # Pattern 2: a name assigned only inside a for-loop's branches, used after
    # the loop, never assigned earlier in the function -> needs init before loop.
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        body = func.body
        for idx, stmt in enumerate(body):
            if not isinstance(stmt, ast.For):
                continue
            assigned_names = set()
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            assigned_names.add(t.id)
            if not assigned_names:
                continue
            prior_assigned = set()
            for prev in body[:idx]:
                for sub in ast.walk(prev):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                prior_assigned.add(t.id)
            used_after = set()
            for after in body[idx + 1:]:
                for sub in ast.walk(after):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        used_after.add(sub.id)
            missing = (assigned_names - prior_assigned) & used_after
            for name in missing:
                edits.append((stmt, ('init_before_loop', name)))

    if not edits:
        return []

    lines = source.splitlines(keepends=True)

    def node_span(node):
        start = sum(len(l) for l in lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(l) for l in lines[:node.end_lineno - 1]) + node.end_col_offset
        return start, end

    all_edits = []  # (start, end, replacement)
    for node, kind in edits:
        if kind == 'gt_to_ne':
            start, end = node_span(node)
            old_text = source[start:end]
            new_text = old_text.replace('>', '!=', 1)
            if new_text != old_text:
                all_edits.append((start, end, new_text))
        else:
            _, name = kind
            start, _ = node_span(node)
            line_start = source.rfind('\n', 0, start) + 1
            raw_indent = source[line_start:start]
            indent = raw_indent[:len(raw_indent) - len(raw_indent.lstrip())]
            insert_text = f"{indent}{name} = False\n"
            all_edits.append((line_start, line_start, insert_text))

    if not all_edits:
        return []

    all_edits.sort(key=lambda x: x[0], reverse=True)

    new_src = source
    for start, end, repl in all_edits:
        new_src = new_src[:start] + repl + new_src[end:]

    if new_src == source:
        return []
    return [new_src]

LEARNED.append(Rule("uniqueness_fix", _learned_uniqueness_fix, symptoms=('err:UnboundLocalError', 'wrong')))
