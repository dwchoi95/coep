from src.core.repair import Rule
LEARNED = []


def _learned_jump_parity_simulation(source):
    """Greedy step-by-step simulation of a target-seeking cumulative sum
    (e.g. minimal jumps to reach x) that never accounts for sign/parity:
    it should instead walk only in the positive direction and stop once the
    running total both reaches and matches the parity of abs(target)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        # looking for: while <num> != <x>  (simulation loop driven by inequality)
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.NotEq)
                and isinstance(test.left, ast.Name)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Name)):
            continue

        num_name = test.left.id
        x_name = test.comparators[0].id

        # body should look like an if/elif structure incrementing a counter
        # and conditionally adding/subtracting it from num
        body_src = ast.dump(node)
        if 'If' not in body_src:
            continue

        # try to find the counter variable (the thing incremented by 1)
        ans_name = None
        for sub in ast.walk(node):
            if (isinstance(sub, ast.AugAssign) and isinstance(sub.op, ast.Add)
                    and isinstance(sub.target, ast.Name)
                    and isinstance(sub.value, ast.Constant) and sub.value.value == 1):
                ans_name = sub.target.id
                break
        if ans_name is None:
            continue

        lines = source.splitlines(keepends=True)
        start = node.lineno - 1
        end = node.end_lineno - 1

        # figure indentation of the while statement
        first_line = lines[start]
        indent = first_line[:len(first_line) - len(first_line.lstrip())]

        abs_stmt = f"{indent}{x_name} = abs({x_name})\n"
        new_while = (
            f"{indent}while {num_name} < {x_name} or ({num_name} - {x_name}) % 2 != 0:\n"
            f"{indent}    {ans_name} += 1\n"
            f"{indent}    {num_name} += {ans_name}\n"
        )

        new_lines = lines[:start] + [abs_stmt, new_while] + lines[end + 1:]
        new_source = "".join(new_lines)
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("jump_parity_simulation", _learned_jump_parity_simulation, symptoms=('wrong')))


def _learned_min_steps_parity_search(source):
    """Misconception: computing the minimal n with triangular(n)>=|x| via a
    loop and then patching the remainder with ad-hoc arithmetic, instead of
    continuing the loop until the parity condition (triangular(n)-|x|) % 2==0
    also holds. Fix: take abs(x), loop incrementing n and the running sum
    while sum < target OR the parity condition fails, then print n directly."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        whiles = [n for n in ast.walk(node) if isinstance(n, ast.While)]
        if len(whiles) != 1:
            continue
        w = whiles[0]
        # condition must be a simple "num <= something" / "num < something"
        if not isinstance(w.test, ast.Compare):
            continue
        if len(w.test.ops) != 1 or not isinstance(w.test.ops[0], (ast.LtE, ast.Lt)):
            continue

        # find accumulator variable name (left side of compare)
        left = w.test.left
        if not isinstance(left, ast.Name):
            continue
        acc_name = left.id

        # find increment variable name used inside the loop body (the step counter)
        step_name = None
        for stmt in w.body:
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                if stmt.target.id != acc_name:
                    step_name = stmt.target.id

        if step_name is None:
            continue

        func_name = node.name
        # find the parameter name
        if not node.args.args:
            continue
        param_name = node.args.args[0].arg

        start, end = node.col_offset, node.end_col_offset
        start_line, end_line = node.lineno, node.end_lineno

        lines = source.splitlines(keepends=True)
        # reconstruct full span text to replace
        before = "".join(lines[:start_line - 1])
        after = "".join(lines[end_line:])

        indent = " " * node.col_offset
        body_indent = indent + "    "

        new_func = (
            f"{indent}def {func_name}({param_name}):\n"
            f"{body_indent}{param_name} = abs({param_name})\n"
            f"{body_indent}{step_name} = 0\n"
            f"{body_indent}{acc_name} = 0\n"
            f"{body_indent}while {acc_name} < {param_name} or ({acc_name} - {param_name}) % 2 != 0:\n"
            f"{body_indent}    {step_name} += 1\n"
            f"{body_indent}    {acc_name} += {step_name}\n"
            f"{body_indent}print({step_name})\n"
        )

        new_source = before + new_func + after
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("min_steps_parity_search", _learned_min_steps_parity_search, symptoms=('wrong',)))


def _learned_offbyone_search_init(source):
    """Search loop that finds minimal n satisfying a condition starts counting
    at 1 instead of 0, skipping the valid zero case (classic off-by-one in
    'smallest n such that f(n) >= x' style loops)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.hits = []

        def visit_Module(self, node):
            self.scan(node.body)
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            self.scan(node.body)
            self.generic_visit(node)

        def scan(self, body):
            for i, stmt in enumerate(body):
                if (isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value == 1):
                    var = stmt.targets[0].id
                    # look ahead for a while loop using this var that
                    # increments it, i.e. a "search until condition" loop
                    for later in body[i + 1:]:
                        if isinstance(later, ast.While):
                            names_in_test = {
                                n.id for n in ast.walk(later.test)
                                if isinstance(n, ast.Name)
                            }
                            if var in names_in_test:
                                incremented = False
                                for b in later.body:
                                    if (isinstance(b, ast.AugAssign)
                                            and isinstance(b.target, ast.Name)
                                            and b.target.id == var
                                            and isinstance(b.op, ast.Add)):
                                        incremented = True
                                if incremented:
                                    self.hits.append(stmt)
                            break

    f = Finder()
    f.visit(tree)

    for stmt in f.hits:
        start = stmt.value.col_offset
        end = stmt.value.end_col_offset
        lineno = stmt.value.lineno

        lines = source.splitlines(keepends=True)
        # compute absolute offset of the constant within the source
        offset = sum(len(l) for l in lines[:lineno - 1]) + start
        offset_end = sum(len(l) for l in lines[:lineno - 1]) + end

        new_source = source[:offset] + "0" + source[offset_end:]
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("offbyone_search_init", _learned_offbyone_search_init, symptoms=('wrong',)))


def _learned_abs_input_for_symmetric_distance(source):
    """Target problems are symmetric about zero (e.g. distance/steps-to-reach-x
    problems that only use the magnitude of the input), but the code reads the
    raw signed integer from input() without taking its absolute value, so
    negative inputs produce wrong results (loops may not execute or terminate
    incorrectly). Fix: wrap the parsed integer with abs()."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.targets = []

        def visit_Call(self, node):
            if (isinstance(node.func, ast.Name) and node.func.id == 'int'
                    and len(node.args) == 1):
                arg = node.args[0]
                if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                        and arg.func.id == 'input'):
                    self.targets.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    for node in finder.targets:
        start = node.col_offset
        end = node.end_col_offset
        lineno = node.lineno

        lines = source.splitlines(keepends=True)
        line = lines[lineno - 1]
        original_segment = line[start:end]
        new_segment = f"abs({original_segment})"
        new_line = line[:start] + new_segment + line[end:]
        new_lines = lines[:lineno - 1] + [new_line] + lines[lineno:]
        new_source = ''.join(new_lines)
        out.append(new_source)

    return out

LEARNED.append(Rule("abs_input_for_symmetric_distance", _learned_abs_input_for_symmetric_distance, symptoms=('wrong')))


def _learned_jumping_jack_parity_fix(source):
    """Detects the 'scale the overshoot by multiplying the remainder by 2'
    misconception used when adjusting the minimal number of triangular-step
    jumps so that the parity of (closest_triangular_number - target) matches:
    the code does `idx + 1 + excess * 2` (or similar) instead of simply
    trying idx, idx+1, idx+2 (parity flips with each extra step). Replaces
    the offending `if x == arr[i]: ... elif x < arr[i]: ...` statement with
    the correct parity-walk logic."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    def has_mult_by_2(node):
        for sub in ast.walk(node):
            if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Mult):
                for operand in (sub.left, sub.right):
                    if isinstance(operand, ast.Constant) and operand.value == 2:
                        return True
        return False

    def get_subscript_names(side):
        if isinstance(side, ast.Subscript) and isinstance(side.value, ast.Name):
            arr = side.value.id
            sl = side.slice
            if isinstance(sl, ast.Name):
                return arr, sl.id
            if hasattr(ast, "Index") and isinstance(sl, ast.Index) and isinstance(sl.value, ast.Name):
                return arr, sl.value.id
        return None, None

    out = []
    lines = source.splitlines(keepends=True)

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq) and isinstance(test.left, ast.Name)):
            continue
        x_name = test.left.id
        arr_name, idx_name = get_subscript_names(test.comparators[0])
        if arr_name is None or idx_name is None:
            continue

        if len(node.orelse) != 1 or not isinstance(node.orelse[0], ast.If):
            continue
        elif_node = node.orelse[0]
        etest = elif_node.test
        if not (isinstance(etest, ast.Compare) and len(etest.ops) == 1
                and isinstance(etest.ops[0], ast.Lt)):
            continue

        if not any(has_mult_by_2(stmt) for stmt in elif_node.body):
            continue

        indent = ' ' * node.col_offset
        replacement = (
            f"{indent}if {arr_name}[{idx_name}] >= {x_name}:\n"
            f"{indent}    diff = {arr_name}[{idx_name}] - {x_name}\n"
            f"{indent}    if diff % 2 == 0:\n"
            f"{indent}        return {idx_name}\n"
            f"{indent}    else:\n"
            f"{indent}        diff2 = {arr_name}[{idx_name} + 1] - {x_name}\n"
            f"{indent}        if diff2 % 2 == 0:\n"
            f"{indent}            return {idx_name} + 1\n"
            f"{indent}        else:\n"
            f"{indent}            return {idx_name} + 2\n"
        )

        start_line = node.lineno - 1
        end_line = node.end_lineno
        new_lines = lines[:start_line] + [replacement] + lines[end_line:]
        out.append(''.join(new_lines))

    return out

LEARNED.append(Rule("jumping_jack_parity_fix", _learned_jumping_jack_parity_fix, symptoms=('wrong',)))


def _learned_greedy_triangular_parity_fix(source):
    """Detects the 'greedy triangular subtraction + ad-hoc 2*x fixup' misconception
    used for minimal-jumps-to-target problems: the correct approach is to find the
    smallest n with sum(1..n) >= x and (sum(1..n) - x) even, not to greedily
    subtract k from x and then patch with cc += 2*x."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []

    def is_name(node, name=None):
        return isinstance(node, ast.Name) and (name is None or node.id == name)

    def find_body_with_while(stmts):
        for i, stmt in enumerate(stmts):
            if isinstance(stmt, ast.While):
                yield stmts, i, stmt

    bodies = []
    for node in ast.walk(tree):
        if hasattr(node, "body") and isinstance(node.body, list):
            bodies.append(node.body)

    for body in bodies:
        for i, stmt in enumerate(body):
            if not isinstance(stmt, ast.While):
                continue
            w = stmt
            test = w.test
            # test: BinOp(Sub) >= 0  e.g. x - k >= 0
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], (ast.GtE, ast.Gt))):
                continue
            left = test.left
            comparators = test.comparators
            if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Sub)):
                continue
            if not (len(comparators) == 1 and isinstance(comparators[0], ast.Constant)
                    and comparators[0].value == 0):
                continue
            if not (isinstance(left.left, ast.Name) and isinstance(left.right, ast.Name)):
                continue
            target_var = left.left.id   # x
            counter_var = left.right.id  # k

            # body must contain: target -= counter, counter += 1, some cc += 1
            has_sub = False
            has_counter_inc = False
            cc_var = None
            for b in w.body:
                if (isinstance(b, ast.AugAssign) and isinstance(b.op, ast.Sub)
                        and is_name(b.target, target_var) and is_name(b.value, counter_var)):
                    has_sub = True
                elif (isinstance(b, ast.AugAssign) and isinstance(b.op, ast.Add)
                        and is_name(b.target, counter_var)
                        and isinstance(b.value, ast.Constant) and b.value.value == 1):
                    has_counter_inc = True
                elif (isinstance(b, ast.AugAssign) and isinstance(b.op, ast.Add)
                        and isinstance(b.target, ast.Name)
                        and isinstance(b.value, ast.Constant) and b.value.value == 1):
                    cc_var = b.target.id

            if not (has_sub and has_counter_inc and cc_var):
                continue

            # look for the following statement: cc += 2 * target_var
            if i + 1 >= len(body):
                continue
            nxt = body[i + 1]
            if not (isinstance(nxt, ast.AugAssign) and isinstance(nxt.op, ast.Add)
                    and is_name(nxt.target, cc_var)):
                continue
            val = nxt.value
            is_double_fix = (
                isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mult)
                and (
                    (isinstance(val.left, ast.Constant) and val.left.value == 2
                     and is_name(val.right, target_var))
                    or
                    (isinstance(val.right, ast.Constant) and val.right.value == 2
                     and is_name(val.left, target_var))
                )
            )
            if not is_double_fix:
                continue

            # Found the misconception pattern: splice in corrected logic.
            start = w.lineno
            start_col = w.col_offset
            end = nxt.end_lineno
            end_col = nxt.end_col_offset

            lines = source.splitlines(keepends=True)

            def offset(line, col):
                return sum(len(l) for l in lines[:line - 1]) + col

            start_off = offset(start, start_col)
            end_off = offset(end, end_col)

            # pick a sum-variable name that doesn't collide
            s_name = "s"
            suffix = 0
            used_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            while s_name in used_names:
                suffix += 1
                s_name = f"s{suffix}"

            indent = " " * start_col
            replacement = (
                f"{s_name} = 0\n"
                f"{indent}while {s_name} < {target_var} or ({s_name} - {target_var}) % 2 != 0:\n"
                f"{indent}    {s_name} += {counter_var}\n"
                f"{indent}    {counter_var} += 1\n"
                f"{indent}    {cc_var} += 1"
            )

            new_source = source[:start_off] + replacement + source[end_off:]
            if new_source != source:
                out.append(new_source)

    return out

LEARNED.append(Rule("greedy_triangular_parity_fix", _learned_greedy_triangular_parity_fix, symptoms=('wrong',)))


def _learned_missing_output_computation(source):
    """Program reads input but never computes/prints a result (stub solution with no output)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    has_print = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print'
        for node in ast.walk(tree)
    )
    if has_print:
        return []

    # find the variable assigned from int(input())
    target_var = None
    last_stmt_end = None
    for stmt in tree.body:
        last_stmt_end = stmt.end_lineno, stmt.end_col_offset
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == 'int'
                and len(stmt.value.args) == 1
                and isinstance(stmt.value.args[0], ast.Call)
                and isinstance(stmt.value.args[0].func, ast.Name)
                and stmt.value.args[0].func.id == 'input'):
            target_var = stmt.targets[0].id

    if target_var is None or last_stmt_end is None:
        return []

    lines = source.splitlines(keepends=True)
    # reconstruct full source up to the end of the last top-level statement
    end_line, end_col = last_stmt_end
    offset = 0
    for i in range(end_line - 1):
        offset += len(lines[i])
    offset += end_col

    prefix = source[:offset]
    suffix = source[offset:]

    patch = (
        f"\n{target_var} = abs({target_var})\n"
        f"n = 0\n"
        f"s = 0\n"
        f"while s < {target_var} or (s - {target_var}) % 2 != 0:\n"
        f"    n += 1\n"
        f"    s += n\n"
        f"print(n)\n"
    )

    fixed = prefix + patch + suffix
    return [fixed]

LEARNED.append(Rule("missing_output_computation", _learned_missing_output_computation, symptoms=('wrong')))
