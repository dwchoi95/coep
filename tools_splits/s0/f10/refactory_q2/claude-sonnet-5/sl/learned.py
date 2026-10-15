from src.core.repair import Rule
LEARNED = []


def _learned_if_else_both_return_true(source):
    """In an if/else inside a loop, both branches return True (loop body is
    vacuous/tautological) - typically caused by negating the if-condition
    incorrectly and then duplicating the 'return True' in the else branch.
    Fix: turn it into 'if <original condition without the bad negation>:
    return True' followed by a loop-trailing 'return False', dropping the
    else branch entirely."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.hits = []

        def visit_For(self, node):
            self._check_loop(node)
            self.generic_visit(node)

        def visit_While(self, node):
            self._check_loop(node)
            self.generic_visit(node)

        def _check_loop(self, loop_node):
            for stmt in loop_node.body:
                if (isinstance(stmt, ast.If) and stmt.orelse and
                        len(stmt.body) == 1 and len(stmt.orelse) == 1 and
                        isinstance(stmt.body[0], ast.Return) and
                        isinstance(stmt.orelse[0], ast.Return)):
                    b = stmt.body[0].value
                    e = stmt.orelse[0].value
                    if (isinstance(b, ast.Constant) and b.value is True and
                            isinstance(e, ast.Constant) and e.value is True):
                        self.hits.append((loop_node, stmt))

    finder = Finder()
    finder.visit(tree)
    if not finder.hits:
        return []

    lines = source.splitlines(keepends=True)

    def get_span(node):
        start = sum(len(l) for l in lines[:node.lineno - 1]) + node.col_offset
        end = sum(len(l) for l in lines[:node.end_lineno - 1]) + node.end_col_offset
        return start, end

    for loop_node, if_stmt in finder.hits:
        start, end = get_span(if_stmt)
        indent = ' ' * if_stmt.col_offset
        cond_src = ast.get_source_segment(source, if_stmt.test)
        if cond_src is None:
            continue
        new_if = f"if {cond_src}:\n{indent}    return True\n"
        new_src = source[:start] + new_if + source[end:]

        loop_end_line = loop_node.end_lineno
        offset_lines = new_src.splitlines(keepends=True)
        insertion_line_idx = None
        cum = 0
        for idx, l in enumerate(offset_lines):
            cum += len(l)
            if idx + 1 == loop_end_line:
                insertion_line_idx = idx
                break
        if insertion_line_idx is not None:
            loop_indent = ' ' * loop_node.col_offset
            offset_lines.insert(insertion_line_idx + 1, f"{loop_indent}return False\n")
            new_src = ''.join(offset_lines)

        out.append(new_src)

    return out

LEARNED.append(Rule("if_else_both_return_true", _learned_if_else_both_return_true, symptoms=('wrong',)))


def _learned_exact_one_count_check(source):
    """Fixes the 'count > 1 / count <= 1' uniqueness check, which wrongly
    treats count == 0 as unique. The correct check is count == 1."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    lines = source.splitlines(keepends=True)

    def get_segment(node):
        start_line = node.lineno - 1
        start_col = node.col_offset
        end_line = node.end_lineno - 1
        end_col = node.end_col_offset
        if start_line == end_line:
            return lines[start_line][start_col:end_col]
        else:
            seg = lines[start_line][start_col:]
            for i in range(start_line + 1, end_line):
                seg += lines[i]
            seg += lines[end_line][:end_col]
            return seg

    def is_return_bool(stmts, value):
        return (
            len(stmts) == 1
            and isinstance(stmts[0], ast.Return)
            and isinstance(stmts[0].value, ast.Constant)
            and stmts[0].value.value is value
        )

    class Finder(ast.NodeVisitor):
        def visit_If(self, node):
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == 1
                and is_return_bool(node.body, False)
                and len(node.orelse) == 1
                and isinstance(node.orelse[0], ast.If)
            ):
                elif_node = node.orelse[0]
                etest = elif_node.test
                if (
                    isinstance(etest, ast.Compare)
                    and len(etest.ops) == 1
                    and isinstance(etest.ops[0], (ast.LtE, ast.Lt))
                    and isinstance(etest.comparators[0], ast.Constant)
                    and etest.comparators[0].value in (1, 2)
                    and is_return_bool(elif_node.body, True)
                    and not elif_node.orelse
                ):
                    var_src = get_segment(test.left)
                    indent = ' ' * node.col_offset
                    replacement = (
                        f"if {var_src} == 1:\n"
                        f"{indent}    return True\n"
                        f"{indent}else:\n"
                        f"{indent}    return False"
                    )
                    out.append((node, replacement))
            self.generic_visit(node)

    Finder().visit(tree)

    results = []
    for node, replacement in out:
        start_line = node.lineno - 1
        start_col = node.col_offset
        end_line = node.end_lineno - 1
        end_col = node.end_col_offset

        new_lines = list(lines)
        if start_line == end_line:
            orig = new_lines[start_line]
            new_lines[start_line] = (
                orig[:start_col] + replacement + orig[end_col:]
            )
        else:
            first = new_lines[start_line][:start_col] + replacement
            last = new_lines[end_line][end_col:]
            new_lines[start_line:end_line + 1] = [first + last]

        results.append(''.join(new_lines))

    return results


LEARNED.append(Rule("exact_one_count_check", _learned_exact_one_count_check, symptoms=('wrong')))
