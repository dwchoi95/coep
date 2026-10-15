from src.core.repair import Rule
LEARNED = []


def _learned_count_threshold_uniqueness(source):
    """Misconception: treating 'unique' (count == 1) as count <= 1,
    using an inverted/overlapping threshold check (count > 1 / count <= 1)
    instead of an exact equality check (count == 1)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def is_count_gt1_false(node, count_name):
        # if <count_name> > 1: return False
        if not isinstance(node, ast.If):
            return False
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)):
            return False
        left = test.left
        comp = test.comparators[0]
        if not (isinstance(left, ast.Name) and left.id == count_name):
            return False
        if not (isinstance(comp, ast.Constant) and comp.value == 1):
            return False
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
            return False
        ret_val = node.body[0].value
        if not (isinstance(ret_val, ast.Constant) and ret_val.value is False):
            return False
        return True

    def is_count_lte1_true(node, count_name):
        # elif <count_name> <= 1: return True   (represented as orelse -> If)
        if not isinstance(node, ast.If):
            return False
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.LtE)):
            return False
        left = test.left
        comp = test.comparators[0]
        if not (isinstance(left, ast.Name) and left.id == count_name):
            return False
        if not (isinstance(comp, ast.Constant) and comp.value == 1):
            return False
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
            return False
        ret_val = node.body[0].value
        if not (isinstance(ret_val, ast.Constant) and ret_val.value is True):
            return False
        return True

    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Gt)):
                continue
            left = test.left
            if not isinstance(left, ast.Name):
                continue
            count_name = left.id
            if not is_count_gt1_false(node, count_name):
                continue
            # orelse should be a single If (elif) matching the lte1 pattern
            if len(node.orelse) != 1:
                continue
            elif_node = node.orelse[0]
            if not is_count_lte1_true(elif_node, count_name):
                continue

            # Found the pattern; splice replacement into original source
            lines = source.splitlines(keepends=True)
            start_line = node.lineno - 1
            start_col = node.col_offset
            end_line = node.end_lineno - 1
            end_col = node.end_col_offset

            indent = " " * node.col_offset
            replacement = (
                f"if {count_name} == 1:\n"
                f"{indent}    return True\n"
                f"{indent}else:\n"
                f"{indent}    return False"
            )

            if start_line == end_line:
                line = lines[start_line]
                new_line = line[:start_col] + replacement + line[end_col:]
                new_lines = lines[:start_line] + [new_line] + lines[end_line + 1:]
            else:
                first_line = lines[start_line][:start_col] + replacement
                new_lines = lines[:start_line] + [first_line + "\n"] + lines[end_line + 1:]
                # handle trailing text after the if-block on end_line, if any
                tail = lines[end_line][end_col:]
                if tail.strip():
                    new_lines.insert(start_line + 1, tail)

            new_source = "".join(new_lines)
            if new_source != source:
                out.append(new_source)

    return out

LEARNED.append(Rule("count_threshold_uniqueness", _learned_count_threshold_uniqueness, symptoms=('wrong',)))
