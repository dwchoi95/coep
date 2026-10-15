from src.core.repair import Rule
LEARNED = []


def _learned_judge_io_mismatch(source):
    """Script was written for interactive human use: input() calls carry a
    human-facing prompt string, and conditional branches print descriptive
    sentences instead of the exact tokens an automated judge expects
    (typically YES/NO). Strip input() prompts to bare input(), and collapse
    if/else blocks whose only statement in each branch is a print(...) call
    with a non-literal-YES/NO message into print("YES") / print("NO")."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    edits = []  # (lineno, col_offset, end_lineno, end_col_offset, replacement)

    # 1. input("prompt") -> input()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'input' and node.args):
            first, last = node.args[0], node.args[-1]
            edits.append((first.lineno, first.col_offset,
                          last.end_lineno, last.end_col_offset, ''))

    # 2. if/else with lone descriptive print() in each branch -> YES/NO
    def is_plain_yesno(args):
        return (len(args) == 1 and isinstance(args[0], ast.Constant)
                and isinstance(args[0].value, str)
                and args[0].value in ("YES", "NO"))

    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.orelse:
            if len(node.body) == 1 and len(node.orelse) == 1:
                b, o = node.body[0], node.orelse[0]
                if (isinstance(b, ast.Expr) and isinstance(b.value, ast.Call)
                        and isinstance(b.value.func, ast.Name) and b.value.func.id == 'print'
                        and isinstance(o, ast.Expr) and isinstance(o.value, ast.Call)
                        and isinstance(o.value.func, ast.Name) and o.value.func.id == 'print'):
                    b_args, o_args = b.value.args, o.value.args
                    if b_args and o_args and not (
                            is_plain_yesno(b_args) and is_plain_yesno(o_args)):
                        bf, bl = b_args[0], b_args[-1]
                        of, ol = o_args[0], o_args[-1]
                        edits.append((bf.lineno, bf.col_offset,
                                      bl.end_lineno, bl.end_col_offset, '"YES"'))
                        edits.append((of.lineno, of.col_offset,
                                      ol.end_lineno, ol.end_col_offset, '"NO"'))

    if not edits:
        return []

    # Map (lineno, col) -> absolute offset in source, then splice edits in
    # from the end of the file backwards so earlier offsets stay valid.
    lines = source.splitlines(keepends=True)
    line_start = [0]
    for line in lines:
        line_start.append(line_start[-1] + len(line))

    def abs_off(lineno, col):
        return line_start[lineno - 1] + col

    abs_edits = sorted(
        ((abs_off(sl, sc), abs_off(el, ec), repl)
         for sl, sc, el, ec, repl in edits),
        key=lambda x: x[0], reverse=True
    )

    new_source = source
    for start, end, repl in abs_edits:
        new_source = new_source[:start] + repl + new_source[end:]

    return [new_source]

LEARNED.append(Rule("judge_io_mismatch", _learned_judge_io_mismatch, symptoms=('wrong')))
