from src.core.repair import Rule
LEARNED = []


def _learned_uniqueness_threshold(source):
    """Detects the 'off-by-one/boundary' uniqueness-check misconception: testing
    `if count > 1: flag = False else: flag = True` (treating "more than one
    occurrence" as the boundary, which incorrectly treats a zero-count as
    unique) instead of the correct `if count == 1: flag = True else: flag =
    False`. Rewrites the comparison to `== 1` and swaps the True/False
    literals in the two branches accordingly."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    matches = []

    class Visitor(ast.NodeVisitor):
        def visit_If(self, node):
            test = node.test
            if (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Gt)
                    and len(test.comparators) == 1
                    and isinstance(test.comparators[0], ast.Constant)
                    and test.comparators[0].value == 1):

                def single_bool_assign(stmts, value):
                    return (len(stmts) == 1 and isinstance(stmts[0], ast.Assign)
                            and isinstance(stmts[0].value, ast.Constant)
                            and stmts[0].value.value is value)

                if single_bool_assign(node.body, False) and single_bool_assign(node.orelse, True):
                    matches.append((node, node.body[0].value, node.orelse[0].value))
            self.generic_visit(node)

    Visitor().visit(tree)
    if not matches:
        return []

    def offset(line, col):
        lines = source.splitlines(keepends=True)
        return sum(len(l) for l in lines[:line - 1]) + col

    edits = []
    for node, body_val, orelse_val in matches:
        test = node.test
        left_src = ast.get_source_segment(source, test.left)
        s = offset(test.lineno, test.col_offset)
        e = offset(test.end_lineno, test.end_col_offset)
        edits.append((s, e, f"{left_src} == 1"))

        s = offset(body_val.lineno, body_val.col_offset)
        e = offset(body_val.end_lineno, body_val.end_col_offset)
        edits.append((s, e, "True"))

        s = offset(orelse_val.lineno, orelse_val.col_offset)
        e = offset(orelse_val.end_lineno, orelse_val.end_col_offset)
        edits.append((s, e, "False"))

    edits.sort(key=lambda t: t[0], reverse=True)
    new_source = source
    for s, e, repl in edits:
        new_source = new_source[:s] + repl + new_source[e:]

    return [new_source]


LEARNED.append(Rule("uniqueness_threshold", _learned_uniqueness_threshold, symptoms=('wrong')))


def _learned_count_leq_one_missing_else(source):
    """elif <var> <= 1: return True (with no else) wrongly maps count==0 to True;
    should be elif <var> == 1: return True else: return False."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and len(node.orelse) == 1
                and isinstance(node.orelse[0], ast.If)):
            continue
        elif_node = node.orelse[0]
        if elif_node.orelse:
            continue  # already has an else/elif chain
        test = elif_node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.LtE)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == 1):
            continue
        start_line = test.lineno - 1
        end_line = test.end_lineno - 1
        if start_line != end_line:
            continue  # keep edit local/simple
        start_col = test.col_offset
        end_col = test.end_col_offset

        new_lines = lines[:]
        segment = new_lines[start_line]
        before, target, after = segment[:start_col], segment[start_col:end_col], segment[end_col:]
        if '<=' not in target:
            continue
        target = target.replace('<=', '==', 1)
        new_lines[start_line] = before + target + after

        last_stmt = elif_node.body[-1]
        insert_line = last_stmt.end_lineno  # insert right after this line (1-indexed -> index == after)
        indent = ' ' * elif_node.col_offset
        else_block = f"{indent}else:\n{indent}    return False\n"
        new_lines.insert(insert_line, else_block)
        out.append(''.join(new_lines))
    return out

LEARNED.append(Rule("count_leq_one_missing_else", _learned_count_leq_one_missing_else, symptoms=('wrong',)))
