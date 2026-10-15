from src.core.repair import Rule
LEARNED = []


def _learned_count_threshold_inverted(source):
    """Treats 'exactly one occurrence' as 'count > 1 -> False else True' instead of 'count == 1 -> True else False'.
    This produces wrong results when count == 0, since the two forms are not equivalent there."""
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
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)):
            continue
        comparator = test.comparators[0]
        if not (isinstance(comparator, ast.Constant) and comparator.value == 1):
            continue
        if len(node.body) != 1 or len(node.orelse) != 1:
            continue
        body_stmt = node.body[0]
        else_stmt = node.orelse[0]
        if not (isinstance(body_stmt, ast.Assign) and isinstance(else_stmt, ast.Assign)):
            continue
        if len(body_stmt.targets) != 1 or len(else_stmt.targets) != 1:
            continue
        if not (isinstance(body_stmt.targets[0], ast.Name) and isinstance(else_stmt.targets[0], ast.Name)):
            continue
        if body_stmt.targets[0].id != else_stmt.targets[0].id:
            continue
        body_val = body_stmt.value
        else_val = else_stmt.value
        if not (isinstance(body_val, ast.Constant) and isinstance(else_val, ast.Constant)):
            continue
        if not (isinstance(body_val.value, bool) and isinstance(else_val.value, bool)):
            continue
        if not (body_val.value is False and else_val.value is True):
            continue

        # Found the misconception pattern: if X > 1: var = False else: var = True
        var_name = body_stmt.targets[0].id
        left_src = ast.get_source_segment(source, test.left)
        if left_src is None:
            continue

        indent = ' ' * node.col_offset
        inner_indent = ' ' * (node.body[0].col_offset)
        replacement = (
            f"if {left_src}==1:\n"
            f"{inner_indent}{var_name}=True\n"
            f"{indent}else:\n"
            f"{inner_indent}{var_name}=False"
        )

        start, end = get_span(node)
        new_source = source[:start] + replacement + source[end:]
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("count_threshold_inverted", _learned_count_threshold_inverted, symptoms=('wrong')))
