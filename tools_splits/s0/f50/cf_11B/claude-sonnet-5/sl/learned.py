from src.core.repair import Rule
LEARNED = []


def _learned_jumpingjack_doubled_remainder(source):
    """Fixes the misconception of computing extra jumps by multiplying a
    remainder by 2 (lower_rem*2 / larger_rem*2) and taking a min() over
    several ad-hoc formulas, instead of correctly branching on the parity
    of (next_triangular - x) to decide between i, i+1, or i+2 extra jumps."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.body:
            seg = ast.get_source_segment(source, node)
            if not seg:
                continue
            if 'lower_rem' in seg and 'larger_rem' in seg and 'min(' in seg:
                lines = source.splitlines(keepends=True)
                body_start = node.body[0].lineno - 1
                body_end = node.body[-1].end_lineno
                indent = ' ' * node.body[0].col_offset
                replacement = (
                    f"{indent}larger_rem = csc[i] - x\n"
                    f"{indent}if larger_rem % 2 == 0:\n"
                    f"{indent}    return i\n"
                    f"{indent}elif (larger_rem + (i + 1)) % 2 == 0:\n"
                    f"{indent}    return i + 1\n"
                    f"{indent}else:\n"
                    f"{indent}    return i + 2\n"
                )
                new_source = ''.join(lines[:body_start]) + replacement + ''.join(lines[body_end:])
                out.append(new_source)
    return out

LEARNED.append(Rule("jumpingjack_doubled_remainder", _learned_jumpingjack_doubled_remainder, symptoms=('wrong')))


def _learned_loop_counter_as_target(source):
    """Fixes while-loops whose stopping condition erroneously compares an
    accumulator against the loop's own increment/counter variable instead of
    against the problem's actual target value (e.g. an input read via
    int(input()) stored in a variable/attribute). The counter variable is
    replaced in the condition by abs(target_variable)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.assigns = []   # names of vars/attrs assigned from int(input())
            self.whiles = []

        def visit_Assign(self, node):
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                    and val.func.id == 'int' and len(val.args) == 1):
                inner = val.args[0]
                if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                        and inner.func.id == 'input'):
                    for t in node.targets:
                        try:
                            self.assigns.append(ast.unparse(t))
                        except Exception:
                            pass
            self.generic_visit(node)

        def visit_While(self, node):
            self.whiles.append(node)
            self.generic_visit(node)

    f = Finder()
    f.visit(tree)
    if not f.assigns or not f.whiles:
        return []

    target_name = f.assigns[0]
    lines = source.splitlines(keepends=True)

    def pos_to_index(lineno, col):
        return sum(len(l) for l in lines[:lineno - 1]) + col

    for node in f.whiles:
        try:
            test_src = ast.unparse(node.test)
        except Exception:
            continue
        if target_name in test_src:
            continue  # already uses the real target

        for stmt in node.body:
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, (ast.Name, ast.Attribute)):
                try:
                    counter_name = ast.unparse(stmt.target)
                except Exception:
                    continue
                if counter_name == target_name:
                    continue
                if test_src.count(counter_name) >= 2:
                    new_test_src = test_src.replace(counter_name, f'abs({target_name})')
                    start_idx = pos_to_index(node.test.lineno, node.test.col_offset)
                    end_idx = pos_to_index(node.test.end_lineno, node.test.end_col_offset)
                    new_source = source[:start_idx] + new_test_src + source[end_idx:]
                    if new_source != source:
                        out.append(new_source)

    return out

LEARNED.append(Rule("loop_counter_as_target", _learned_loop_counter_as_target, symptoms=('wrong',)))
