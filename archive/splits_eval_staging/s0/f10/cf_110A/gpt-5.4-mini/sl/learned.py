from src.core.repair import Rule
LEARNED = []


def _learned_fix_nearly_lucky_io(source):
    """Replace interactive/debug-style input/output with Codeforces-style stdin/stdout for nearly lucky number solutions."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.input_calls = []
            self.print_calls = []
            self.has_yesno = False
            self.has_annotated_prompt = False

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "input":
                self.input_calls.append(node)
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) and node.args[0].value:
                    self.has_annotated_prompt = True
            if isinstance(node.func, ast.Name) and node.func.id == "print":
                self.print_calls.append(node)
                for a in node.args:
                    if isinstance(a, ast.Constant) and a.value in ("YES", "NO"):
                        self.has_yesno = True
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    if finder.has_yesno:
        return []

    edits = []

    # Remove prompt text from input() if present.
    for node in finder.input_calls:
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) and node.args[0].value:
            edits.append((node.args[0].lineno, node.args[0].col_offset, node.args[0].end_lineno, node.args[0].end_col_offset, ""))

    # Replace f-string / explanatory prints with YES/NO output.
    for node in finder.print_calls:
        span = (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)
        src = source.splitlines(keepends=True)
        start = sum(len(line) for line in src[:span[0] - 1]) + span[1]
        end = sum(len(line) for line in src[:span[2] - 1]) + span[3]
        text = source[start:end]
        if "YES" not in text and "NO" not in text:
            if len(node.args) == 1 and isinstance(node.args[0], ast.JoinedStr):
                # Replace verbose result message with a single literal.
                if any(isinstance(v, ast.FormattedValue) for v in node.args[0].values):
                    replacement = 'print("YES")' if "not" not in text.lower() else 'print("NO")'
                    edits.append((span[0], span[1], span[2], span[3], replacement))
            elif len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                if "not" in node.args[0].value.lower():
                    edits.append((span[0], span[1], span[2], span[3], 'print("NO")'))
                else:
                    edits.append((span[0], span[1], span[2], span[3], 'print("YES")'))

    if not edits:
        return []

    # Apply edits from end to start.
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    text = source
    for l1, c1, l2, c2, repl in sorted(edits, key=lambda x: (x[0], x[1]), reverse=True):
        start = offsets[l1 - 1] + c1
        end = offsets[l2 - 1] + c2
        text = text[:start] + repl + text[end:]

    if text != source:
        out.append(text)
    return out

LEARNED.append(Rule("fix_nearly_lucky_io", _learned_fix_nearly_lucky_io, symptoms=('wrong')))
