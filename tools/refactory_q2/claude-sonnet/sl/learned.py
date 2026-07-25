from src.core.repair import Rule
LEARNED = []


def _learned_uniqueness_count_gt1(source):
    """Uniqueness check uses `count > 1` instead of `count != 1`, so a count
    of 0 (item not present at all) is incorrectly treated as unique/True."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    src = source
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            left = node.left
            right = node.comparators[0]
            if (isinstance(op, ast.Gt) and isinstance(right, ast.Constant)
                    and right.value == 1):
                start = node.left.col_offset
                end = right.end_col_offset
                lineno = node.lineno
                end_lineno = node.end_lineno
                if lineno == end_lineno:
                    edits.append((node.lineno, node.col_offset, node.end_col_offset))
    if not edits:
        return []
    lines = src.splitlines(keepends=True)
    for lineno, col_offset, end_col_offset in edits:
        line = lines[lineno - 1]
        old = line[col_offset:end_col_offset]
        new = old.replace('> 1', '!= 1') if '> 1' in old else old.replace('>1', '!=1')
        if new == old:
            continue
        new_line = line[:col_offset] + new + line[end_col_offset:]
        new_lines = lines[:lineno - 1] + [new_line] + lines[lineno:]
        out.append(''.join(new_lines))
    return out

LEARNED.append(Rule("uniqueness_count_gt1", _learned_uniqueness_count_gt1, symptoms=('wrong')))


def _learned_count_ge2_uniqueness(source):
    """Fixes the misconception that 'count >= 2' (with True/False branches swapped)
    correctly captures uniqueness; the real uniqueness condition is 'count == 1',
    since a count of 0 means the value never occurred and should not be reported
    as unique."""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.hits = []

        def visit_If(self, node):
            test = node.test
            # look for: count >= 2  or  count > 1
            is_ge2 = (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and len(test.comparators) == 1
                and (
                    (isinstance(test.ops[0], ast.GtE)
                     and isinstance(test.comparators[0], ast.Constant)
                     and test.comparators[0].value == 2)
                    or
                    (isinstance(test.ops[0], ast.Gt)
                     and isinstance(test.comparators[0], ast.Constant)
                     and test.comparators[0].value == 1)
                )
            )
            if is_ge2:
                def is_single_return(stmts, value):
                    return (
                        len(stmts) == 1
                        and isinstance(stmts[0], ast.Return)
                        and isinstance(stmts[0].value, ast.Constant)
                        and stmts[0].value.value is value
                    )
                if is_single_return(node.body, False) and is_single_return(node.orelse, True):
                    self.hits.append((node, test))
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    if not finder.hits:
        return []

    lines = source.splitlines(keepends=True)

    def get_span(node):
        start_line = node.lineno - 1
        start_col = node.col_offset
        end_line = node.end_lineno - 1
        end_col = node.end_col_offset
        return start_line, start_col, end_line, end_col

    def build_offset_table(lines):
        offsets = [0]
        total = 0
        for line in lines:
            total += len(line)
            offsets.append(total)
        return offsets

    offsets = build_offset_table(lines)

    def node_to_source_span(node):
        sl, sc, el, ec = get_span(node)
        start = offsets[sl] + sc
        end = offsets[el] + ec
        return start, end

    for node, test in finder.hits:
        # rebuild the source with just this If's test/body/orelse fixed
        var_src = None
        try:
            var_src = ast.unparse(test.left)
        except Exception:
            var_src = None
        if var_src is None:
            continue

        start, end = node_to_source_span(node)
        indent = " " * node.col_offset
        new_if = (
            f"if {var_src} == 1:\n"
            f"{indent}    return True\n"
            f"{indent}else:\n"
            f"{indent}    return False"
        )
        new_source = source[:start] + new_if + source[end:]
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("count_ge2_uniqueness", _learned_count_ge2_uniqueness, symptoms=('wrong',)))
