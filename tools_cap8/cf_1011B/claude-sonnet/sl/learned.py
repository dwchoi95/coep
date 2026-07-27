from src.core.repair import Rule
LEARNED = []


def _learned_binary_search_true_loop(source):
    """Manual binary search implemented as `while True:` that decides the
    midpoint with plain int((left+right)/2) and only terminates on an exact
    `res == 0` / `left == right` condition. This can infinite-loop or miss
    the true boundary because it never converges monotonically and never
    rounds the midpoint upward. Rewrite to the canonical, always-terminating
    `while left < right` binary-search skeleton: mid = (left+right+1)//2,
    move `left` up when the predicate still holds (res >= 0), otherwise
    shrink `right`, and return `left` once the loop ends."""
    import ast
    import re
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.matches = []

        def visit_While(self, node):
            is_true = (
                (isinstance(node.test, ast.Constant) and node.test.value is True)
                or (isinstance(node.test, ast.NameConstant) and node.test.value is True)
            )
            if is_true:
                has_eq_return = False
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.If):
                        has_return = any(isinstance(s, ast.Return) for s in ast.walk(stmt))
                        has_eq = any(
                            isinstance(c, ast.Compare) and any(isinstance(op, ast.Eq) for op in c.ops)
                            for c in ast.walk(stmt.test)
                        )
                        if has_return and has_eq:
                            has_eq_return = True
                            break
                if has_eq_return:
                    self.matches.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)
    if not finder.matches:
        return []

    lines = source.splitlines(keepends=True)
    for node in finder.matches:
        start, end = node.lineno, node.end_lineno
        loop_src = ''.join(lines[start - 1:end])
        indent = loop_src[:len(loop_src) - len(loop_src.lstrip())]

        if not ('left' in loop_src and 'right' in loop_src and 'mid' in loop_src):
            continue

        new_loop = re.sub(r'while\s+True\s*:', 'while left < right:', loop_src)
        new_loop = re.sub(
            r'mid\s*=\s*int\(\(\s*left\s*\+\s*right\s*\)\s*/\s*2\)',
            'mid = (left + right + 1) // 2',
            new_loop,
        )
        new_loop = re.sub(
            r'[ \t]*if\s+left\s*==\s*right\s+or\s+\w+\s*==\s*0\s*:\s*\n[ \t]*return\s+mid\s*\n',
            '',
            new_loop,
        )
        new_loop = re.sub(
            r'if\s+(\w+)\s*>\s*0\s*:\s*\n([ \t]*)left\s*=\s*mid\s*\+\s*1\s*\n[ \t]*else\s*:\s*\n[ \t]*right\s*=\s*mid\s*-\s*1',
            lambda m: f'if {m.group(1)} >= 0:\n{m.group(2)}left = mid\n{m.group(2)[:-4]}else:\n{m.group(2)}right = mid - 1',
            new_loop,
        )
        new_loop = new_loop.rstrip('\n') + f'\n{indent}return left\n'

        new_source = ''.join(lines[:start - 1]) + new_loop + ''.join(lines[end:])
        if new_source != source:
            out.append(new_source)

    return out

LEARNED.append(Rule("binary_search_true_loop", _learned_binary_search_true_loop, symptoms=('wrong')))
