from src.core.repair import Rule
LEARNED = []


def _learned_counting_loop_fix(source):
    """Miscounting-loop idiom: a for-loop that counts matches by comparing
    `collection[i][k] == <wrong name>` (the counter itself, or a stray
    undefined/copy-pasted name) instead of the function's own parameter,
    combined with an increment statement that reads/writes a different
    (often misspelled) variable than the one that was initialized to 0 and
    checked afterwards. Also fixes the case where the counter variable was
    given the same name as the parameter (shadowing it) by renaming the
    counter consistently everywhere it is used."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines(keepends=True)
    line_starts = [0]
    for ln in lines:
        line_starts.append(line_starts[-1] + len(ln))

    def to_abs(lineno, col):
        return line_starts[lineno - 1] + col

    def span(node):
        return (to_abs(node.lineno, node.col_offset),
                to_abs(node.end_lineno, node.end_col_offset))

    edits = []      # (start, end, replacement)
    occupied = []   # (start, end) ranges already claimed by an edit

    def add_edit(node, repl):
        s, e = span(node)
        edits.append((s, e, repl))
        occupied.append((s, e))

    def covered(node):
        s, e = span(node)
        return any(s >= cs and e <= ce for cs, ce in occupied)

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        target_param = params[0]

        init_name = None
        init_stmt = None
        for stmt in func.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value == 0):
                init_name = stmt.targets[0].id
                init_stmt = stmt
                break
        if init_name is None:
            continue

        if init_name == target_param:
            final_name = init_name + 's' if not init_name.endswith('s') else init_name + '_count'
        else:
            final_name = init_name

        found_bug = False
        for node in ast.walk(func):
            if not isinstance(node, ast.For):
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.If):
                    continue
                test = sub.test
                if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                        and isinstance(test.ops[0], ast.Eq)
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Name)):
                    continue
                cmp_node = test.comparators[0]
                if cmp_node.id == target_param:
                    continue
                found_bug = True
                add_edit(cmp_node, target_param)
                for st in ast.walk(sub):
                    if (isinstance(st, ast.Assign) and len(st.targets) == 1
                            and isinstance(st.targets[0], ast.Name)
                            and isinstance(st.value, ast.BinOp)
                            and isinstance(st.value.op, ast.Add)
                            and isinstance(st.value.left, ast.Name)
                            and isinstance(st.value.right, ast.Constant)
                            and st.value.right.value == 1
                            and st.targets[0].id == st.value.left.id):
                        add_edit(st, f"{final_name} = {final_name} + 1")

        if not found_bug:
            continue

        # fix the post-loop sanity check: `if <wrong name> == 1:`
        for stmt in func.body:
            if (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare)
                    and len(stmt.test.ops) == 1 and isinstance(stmt.test.ops[0], ast.Eq)
                    and len(stmt.test.comparators) == 1
                    and isinstance(stmt.test.left, ast.Name)
                    and isinstance(stmt.test.comparators[0], ast.Constant)
                    and stmt.test.comparators[0].value == 1
                    and stmt.test.left.id != final_name):
                add_edit(stmt.test.left, final_name)

        # if the counter collided with the parameter name, rename every
        # remaining occurrence of the counter (not already edited) to final_name
        if final_name != init_name:
            for nm in ast.walk(func):
                if isinstance(nm, ast.Name) and nm.id == init_name and not covered(nm):
                    add_edit(nm, final_name)

    if not edits:
        return []

    edits.sort(key=lambda e: e[0], reverse=True)
    new_source = source
    for start, end, repl in edits:
        new_source = new_source[:start] + repl + new_source[end:]
    if new_source == source:
        return []
    return [new_source]

LEARNED.append(Rule("counting_loop_fix", _learned_counting_loop_fix, symptoms=('err:NameError', 'wrong')))


def _learned_count_leq_one_as_unique(source):
    """Detects 'if count > 1: return False / elif count <= 1: return True'
    with no final else. This conflates count==0 with count==1, wrongly
    treating 'no matching birthday' as 'unique'. Fix: split the elif into
    'count == 1: return True' plus an explicit 'else: return False'."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.matches = []

        def visit_If(self, node):
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                inner = node.orelse[0]
                if (
                    isinstance(inner.test, ast.Compare)
                    and len(inner.test.ops) == 1
                    and isinstance(inner.test.ops[0], ast.LtE)
                    and not inner.orelse
                ):
                    self.matches.append(inner)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    for inner in finder.matches:
        test = inner.test
        line_idx = test.lineno - 1
        start, end = test.col_offset, test.end_col_offset
        line = lines[line_idx]
        new_line = line[:start] + line[start:end].replace('<=', '==') + line[end:]
        new_lines = lines[:line_idx] + [new_line] + lines[line_idx + 1:]

        indent = ' ' * inner.col_offset
        else_block = f"{indent}else:\n{indent}    return False\n"
        insert_idx = inner.end_lineno  # 1-indexed end becomes insertion point
        new_source_lines = new_lines[:insert_idx] + [else_block] + new_lines[insert_idx:]
        out.append(''.join(new_source_lines))

    return out

LEARNED.append(Rule("count_leq_one_as_unique", _learned_count_leq_one_as_unique, symptoms=('wrong')))


def _learned_count_zero_as_unique(source):
    """Uniqueness-by-counting helpers that check `count > 1` to detect
    duplicates but forget that `count == 0` (the item never appears at
    all) should also disqualify it as "unique" -- a count of zero means
    the value isn't in the list, so it can't be the unique occurrence."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)

    def offset(lineno, col):
        # convert (lineno, col) 1-indexed line to absolute char offset
        return sum(len(l) for l in lines[:lineno - 1]) + col

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        # look for `count > 1` (a simple Compare: Name > Constant(1))
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Gt):
            continue
        if len(test.comparators) != 1:
            continue
        comp = test.comparators[0]
        if not (isinstance(comp, ast.Constant) and comp.value == 1):
            continue
        if not isinstance(test.left, ast.Name):
            continue
        var_name = test.left.id

        # skip if already guards against zero
        test_src = ast.get_source_segment(source, test) or ""
        if "== 0" in test_src or "==0" in test_src:
            continue

        start = offset(test.lineno, test.col_offset)
        end = offset(test.end_lineno, test.end_col_offset)

        new_source = (
            source[:start]
            + f"({test_src}) or {var_name} == 0"
            + source[end:]
        )
        out.append(new_source)

    return out

LEARNED.append(Rule("count_zero_as_unique", _learned_count_zero_as_unique, symptoms=('wrong',)))
