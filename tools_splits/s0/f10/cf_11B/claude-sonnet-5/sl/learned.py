from src.core.repair import Rule
LEARNED = []


def _learned_abs_symmetric_reachability(source):
    """Simulates a symmetric left/right reachability walk (e.g. 'jumping to x')
    using a while-loop with ad-hoc if/elif branching and a `!=` termination
    test, without first normalizing a possibly-negative target via abs() and
    without using the closed-form parity condition. This can loop forever or
    give wrong answers for negative targets. Fix: take abs(target) right
    after it is read, and replace the ad-hoc while-loop with the canonical
    monotone loop `while num < x or (num - x) % 2 != 0: ans += 1; num += ans`."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def char_offset(lineno, col):
        lines = source.splitlines(keepends=True)
        return sum(len(l) for l in lines[:lineno - 1]) + col

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.found = []

        def visit_While(self, node):
            test = node.test
            if (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.NotEq)
                    and isinstance(test.left, ast.Name)
                    and isinstance(test.comparators[0], ast.Name)):
                self.found.append((node, test.left.id, test.comparators[0].id))
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)
    if not finder.found:
        return []

    for node, numvar, xvar in finder.found:
        assign_node = None
        for n in ast.walk(tree):
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id == xvar
                    and isinstance(n.value, ast.Call)):
                assign_node = n

        if assign_node is None:
            continue

        assign_indent = ' ' * assign_node.col_offset
        assign_end = char_offset(assign_node.end_lineno, assign_node.end_col_offset)
        insert_text = f"\n{assign_indent}{xvar} = abs({xvar})"

        while_indent = ' ' * node.col_offset
        while_start = char_offset(node.lineno, node.col_offset)
        while_end = char_offset(node.end_lineno, node.end_col_offset)

        new_while_block = (
            f"while {numvar} < {xvar} or ({numvar} - {xvar}) % 2 != 0:\n"
            f"{while_indent}    ans += 1\n"
            f"{while_indent}    {numvar} += ans"
        )

        if while_start < assign_end:
            # the while loop appears before the assignment textually; skip
            continue

        new_source = (
            source[:assign_end]
            + insert_text
            + source[assign_end:while_start]
            + new_while_block
            + source[while_end:]
        )
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("abs_symmetric_reachability", _learned_abs_symmetric_reachability, symptoms=('wrong',)))


def _learned_triangular_offbyone(source):
    """Misconception: when counting jumps via triangular numbers csc[i]=i*(i+1)//2,
    the code treats index i as needing i+1 jumps (off-by-one) for an exact match,
    and when x falls between two triangular numbers it tries to "fix" parity by
    multiplying the remaining gap by 2 instead of checking the parity of the
    difference and of the next index to decide whether 1 or 2 extra jumps are
    needed."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.found = []

        def visit_If(self, node):
            # Look for: if x == csc[i]: return i + 1
            if (isinstance(node.test, ast.Compare)
                    and len(node.test.ops) == 1
                    and isinstance(node.test.ops[0], ast.Eq)
                    and isinstance(node.test.comparators[0], ast.Subscript)):
                subscript = node.test.comparators[0]
                # get array name and index name
                arr_name = None
                if isinstance(subscript.value, ast.Name):
                    arr_name = subscript.value.id
                idx = subscript.slice
                if isinstance(idx, ast.Index):  # py<3.9
                    idx = idx.value
                if isinstance(idx, ast.Name) and arr_name:
                    loop_var = idx.id
                    x_name = None
                    left = node.test.left
                    if isinstance(left, ast.Name):
                        x_name = left.id
                    # check body: single return of form `i + 1`
                    if (len(node.body) == 1
                            and isinstance(node.body[0], ast.Return)
                            and isinstance(node.body[0].value, ast.BinOp)
                            and isinstance(node.body[0].value.op, ast.Add)
                            and isinstance(node.body[0].value.left, ast.Name)
                            and node.body[0].value.left.id == loop_var):
                        # check there's an elif chain (orelse contains an If)
                        has_elif = (len(node.orelse) == 1
                                    and isinstance(node.orelse[0], ast.If))
                        if has_elif and x_name:
                            self.found.append((node, loop_var, arr_name, x_name))
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    if not finder.found:
        return []

    for node, loop_var, arr_name, x_name in finder.found:
        indent = ' ' * node.col_offset
        start = node.lineno
        end = node.end_lineno
        lines = source.splitlines(keepends=True)
        start_line = sum(len(l) for l in lines[:start - 1])
        start_col = node.col_offset
        start_pos = start_line + start_col
        end_line = sum(len(l) for l in lines[:end - 1])
        end_pos = end_line + node.end_col_offset

        replacement = (
            f"if {x_name} == {arr_name}[{loop_var}]:\n"
            f"{indent}    return {loop_var}\n"
            f"{indent}elif {x_name} < {arr_name}[{loop_var}]:\n"
            f"{indent}    diff = {arr_name}[{loop_var}] - {x_name}\n"
            f"{indent}    if diff % 2 == 0:\n"
            f"{indent}        return {loop_var}\n"
            f"{indent}    elif ({loop_var} + 1) % 2 == 1:\n"
            f"{indent}        return {loop_var} + 1\n"
            f"{indent}    else:\n"
            f"{indent}        return {loop_var} + 2"
        )

        new_source = source[:start_pos] + replacement + source[end_pos:]
        out.append(new_source)

    return out

LEARNED.append(Rule("triangular_offbyone", _learned_triangular_offbyone, symptoms=('wrong')))


def _learned_jump_parity(source):
    """While-loop sums 1+2+...+n until it reaches/exceeds |x|, then a separate
    post-loop 'if x < 0: ans += 1' is used to patch parity instead of folding
    the parity check into the loop condition itself. The correct fix is to
    keep looping while the remaining distance is positive OR odd, and drop the
    separate post-loop patch entirely."""
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

    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if not (isinstance(a, ast.While) and isinstance(b, ast.If)):
                continue
            t = a.test
            if not (isinstance(t, ast.Compare) and len(t.ops) == 1
                    and isinstance(t.ops[0], ast.Gt)
                    and isinstance(t.left, ast.Name)
                    and isinstance(t.comparators[0], ast.Constant)
                    and t.comparators[0].value == 0):
                continue
            xname = t.left.id
            bt = b.test
            if not (isinstance(bt, ast.Compare) and len(bt.ops) == 1
                    and isinstance(bt.ops[0], ast.Lt)
                    and isinstance(bt.left, ast.Name) and bt.left.id == xname
                    and isinstance(bt.comparators[0], ast.Constant)
                    and bt.comparators[0].value == 0):
                continue
            if b.orelse:
                continue

            w_start, w_end = get_span(a.test)
            if_start, if_end = get_span(b)
            new_src = (source[:w_start]
                       + f"{xname} > 0 or (-{xname}) % 2 != 0"
                       + source[w_end:if_start]
                       + source[if_end:])
            out.append(new_src)
    return out

LEARNED.append(Rule("jump_parity", _learned_jump_parity, symptoms=('wrong',)))


def _learned_jumpingjack_parity(source):
    """Greedy "walk down to zero remainder, then add 2*remainder" loops for
    the Jumping Jack minimal-jumps problem ignore the parity condition
    (the triangular sum must equal or exceed x with matching parity);
    replace with a parity-checked while loop."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.found = None
        def visit_Module(self, node):
            body = node.body
            for i, stmt in enumerate(body):
                if isinstance(stmt, ast.While):
                    test = stmt.test
                    if (isinstance(test, ast.Compare) and len(test.ops) == 1 and
                        isinstance(test.ops[0], ast.GtE) and
                        isinstance(test.comparators[0], ast.Constant) and
                        test.comparators[0].value == 0 and
                        isinstance(test.left, ast.BinOp) and
                        isinstance(test.left.op, ast.Sub) and
                        isinstance(test.left.left, ast.Name) and
                        isinstance(test.left.right, ast.Name)):
                        x_var = test.left.left.id
                        k_var = test.left.right.id
                        for j in range(i + 1, len(body)):
                            nxt = body[j]
                            if (isinstance(nxt, ast.AugAssign) and
                                isinstance(nxt.op, ast.Add) and
                                isinstance(nxt.value, ast.BinOp) and
                                isinstance(nxt.value.op, ast.Mult) and
                                isinstance(nxt.target, ast.Name)):
                                mul = nxt.value
                                const_side = None
                                if (isinstance(mul.left, ast.Constant) and mul.left.value == 2
                                        and isinstance(mul.right, ast.Name) and mul.right.id == x_var):
                                    const_side = mul.left
                                elif (isinstance(mul.right, ast.Constant) and mul.right.value == 2
                                        and isinstance(mul.left, ast.Name) and mul.left.id == x_var):
                                    const_side = mul.right
                                if const_side is not None:
                                    cc_var = nxt.target.id
                                    for m in range(j + 1, len(body)):
                                        st = body[m]
                                        if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and
                                            isinstance(st.value.func, ast.Name) and st.value.func.id == 'print' and
                                            len(st.value.args) == 1 and isinstance(st.value.args[0], ast.Name) and
                                            st.value.args[0].id == cc_var):
                                            self.found = (stmt, st, x_var, k_var, cc_var)
                                            return
    f = Finder()
    f.visit(tree)
    if f.found is None:
        return []

    while_node, print_node, x_var, k_var, cc_var = f.found

    lines = source.splitlines(keepends=True)

    def offset(line_idx, col):
        return sum(len(l) for l in lines[:line_idx]) + col

    start_off = offset(while_node.lineno - 1, while_node.col_offset)
    end_off = offset(print_node.end_lineno - 1, print_node.end_col_offset)

    replacement = (
        f"{k_var} = 0\n"
        f"_s = 0\n"
        f"while _s < {x_var} or (_s - {x_var}) % 2 != 0:\n"
        f"    {k_var} += 1\n"
        f"    _s += {k_var}\n"
        f"print({k_var})"
    )

    new_source = source[:start_off] + replacement + source[end_off:]
    return [new_source]

LEARNED.append(Rule("jumpingjack_parity", _learned_jumpingjack_parity, symptoms=('wrong',)))


def _learned_fix_self_referential_loop_condition(source):
    """Loop terminates by comparing its accumulator against its OWN counter
    attribute (e.g. `while tong < self.dem`) instead of against the actual
    input value that was read earlier (e.g. `self.x`). Fix: bind the input
    value into a local `x = abs(self.<input_attr>)` right before the loop,
    and rewrite the loop test to compare against `x` instead of the
    self-referential counter attribute."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue

        # Attributes incremented inside this loop's body (the counters).
        incremented_attrs = set()
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Attribute):
                incremented_attrs.add(stmt.target.attr)
        if not incremented_attrs:
            continue

        test_src = ast.get_source_segment(source, node.test)
        if test_src is None:
            continue

        bad_attr = None
        for attr in incremented_attrs:
            if f"self.{attr}" in test_src:
                bad_attr = attr
                break
        if bad_attr is None:
            continue

        # Find an attribute elsewhere in the module that holds parsed input,
        # e.g. `self.x = int(input())`, distinct from the loop's own counter.
        input_attr = None
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
                func = n.value.func
                if isinstance(func, ast.Name) and func.id == "int":
                    args = n.value.args
                    if args and isinstance(args[0], ast.Call) and isinstance(args[0].func, ast.Name) \
                            and args[0].func.id == "input":
                        for t in n.targets:
                            if isinstance(t, ast.Attribute) and t.attr != bad_attr:
                                input_attr = t.attr
        if input_attr is None:
            continue

        lines = source.splitlines(keepends=True)

        def offset(lineno, col):
            return sum(len(l) for l in lines[:lineno - 1]) + col

        # Splice 1: rewrite the test expression, self.<bad_attr> -> x
        t_start = offset(node.test.lineno, node.test.col_offset)
        t_end = offset(node.test.end_lineno, node.test.end_col_offset)
        new_test = test_src.replace(f"self.{bad_attr}", "x")

        new_source = source[:t_start] + new_test + source[t_end:]

        # Splice 2: insert `x = abs(self.<input_attr>);` right before the
        # while statement, matching its indentation.
        w_start = offset(node.lineno, node.col_offset)
        indent = " " * node.col_offset
        insertion = f"x = abs(self.{input_attr});\n{indent}"
        new_source = new_source[:w_start] + insertion + new_source[w_start:]

        if new_source != source:
            out.append(new_source)

    return out


LEARNED.append(Rule(
    "fix_self_referential_loop_condition",
    _learned_fix_self_referential_loop_condition,
    symptoms=('wrong',),
))


def _learned_missing_core_logic(source):
    """Detects a program that reads x via `var = int(input())` but never
    computes anything or calls print() — i.e. it has no solution logic at
    all. Inserts the minimal-jumps algorithm (and wraps the read value in
    abs()) right after the input assignment, mirroring the accepted fix."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    has_print = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print'
        for node in ast.walk(tree)
    )
    if has_print:
        return []

    assign_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == 'int' and len(node.value.args) == 1:
                inner = node.value.args[0]
                if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                        and inner.func.id == 'input'
                        and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)):
                    assign_node = node
                    break
    if assign_node is None:
        return []

    var = assign_node.targets[0].id
    lines = source.splitlines(keepends=True)
    start_line = assign_node.lineno - 1
    end_line = assign_node.end_lineno - 1
    start_col = assign_node.col_offset
    end_col = assign_node.end_col_offset

    before = ''.join(lines[:start_line]) + lines[start_line][:start_col]
    after = lines[end_line][end_col:] + ''.join(lines[end_line + 1:])

    new_assign = f"{var} = abs(int(input()))"
    algo = (
        f"\nn = 0\n"
        f"s = 0\n"
        f"while s < {var} or (s - {var}) % 2 != 0:\n"
        f"    n += 1\n"
        f"    s += n\n"
        f"print(n)\n"
    )

    new_source = before + new_assign + after + algo
    out.append(new_source)
    return out

LEARNED.append(Rule("missing_core_logic", _learned_missing_core_logic, symptoms=('wrong',)))
