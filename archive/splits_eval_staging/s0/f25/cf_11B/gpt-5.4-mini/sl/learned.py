from src.core.repair import Rule
LEARNED = []


def _learned_absify_magnitude(source):
    """Treat symmetric distance-to-target problems as depending on |x|, not the signed input, before applying the jump-parity loop."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class V(ast.NodeVisitor):
        def visit_Assign(self, node):
            # Match: n, i = int(input()), 0
            if (
                isinstance(node.targets, list)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Tuple)
                and len(node.targets[0].elts) >= 1
            ):
                first = node.targets[0].elts[0]
                if isinstance(first, ast.Name):
                    value = node.value
                    # Allow tuple/list with first element int(input()) or similar
                    if isinstance(value, ast.Tuple) and value.elts:
                        first_val = value.elts[0]
                        if (
                            isinstance(first_val, ast.Call)
                            and isinstance(first_val.func, ast.Name)
                            and first_val.func.id == "int"
                            and len(first_val.args) == 1
                            and isinstance(first_val.args[0], ast.Call)
                            and isinstance(first_val.args[0].func, ast.Name)
                            and first_val.args[0].func.id == "input"
                        ):
                            repl = f"abs(int(input()))"
                            start = first_val.lineno, first_val.col_offset
                            end = first_val.end_lineno, first_val.end_col_offset
                            lines = source.splitlines(True)
                            sidx = sum(len(l) for l in lines[: start[0] - 1]) + start[1]
                            eidx = sum(len(l) for l in lines[: end[0] - 1]) + end[1]
                            out.append(source[:sidx] + repl + source[eidx:])
            self.generic_visit(node)

    V().visit(tree)
    return out

LEARNED.append(Rule("absify_magnitude", _learned_absify_magnitude, symptoms=('wrong')))


def _learned_normalize_target_to_absolute_value(source):
    """Handles signed targets on a symmetric number line by normalizing x to |x| before applying the jump-sum/parity logic."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.candidates = []

        def visit_Assign(self, node):
            if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == 'x' and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == 'int'
                and len(node.value.args) == 1):
                arg = node.value.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'input':
                    self.candidates.append(node)
            self.generic_visit(node)

    finder = Finder()
    finder.visit(tree)

    for node in finder.candidates:
        if not (hasattr(node, "lineno") and hasattr(node, "end_lineno")):
            continue
        lines = source.splitlines(keepends=True)
        start = sum(len(lines[i]) for i in range(node.lineno - 1)) + node.col_offset
        end = sum(len(lines[i]) for i in range(node.end_lineno - 1)) + node.end_col_offset
        out.append(source[:start] + "x = abs(int(input()))" + source[end:])

    return out

LEARNED.append(Rule("normalize_target_to_absolute_value", _learned_normalize_target_to_absolute_value, symptoms=('wrong')))


def _learned_triangle_discriminant_and_division(source):
    """Fix triangular-number formulas that use 1+4*x instead of 1+8*x, and use integer division for triangular sums."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    edits = []

    def span(node):
        return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

    def abs_pos(lines, lineno, col):
        return sum(len(lines[i]) for i in range(lineno - 1)) + col

    lines = source.splitlines(True)

    class Visitor(ast.NodeVisitor):
        def visit_BinOp(self, node):
            # Fix sqrt(1 + 4*x) used for triangular numbers: discriminant should be 1 + 8*x
            if isinstance(node.op, ast.Add):
                left_ok = isinstance(node.left, ast.Constant) and node.left.value == 1
                right_ok = (
                    isinstance(node.right, ast.BinOp) and isinstance(node.right.op, ast.Mult) and
                    (
                        (isinstance(node.right.left, ast.Constant) and node.right.left.value == 4) or
                        (isinstance(node.right.right, ast.Constant) and node.right.right.value == 4)
                    )
                )
                if left_ok and right_ok:
                    s = abs_pos(lines, node.lineno, node.col_offset)
                    e = abs_pos(lines, node.end_lineno, node.end_col_offset)
                    edits.append(source[:s] + "1+8*x" + source[e:])

            # Fix floating division in triangular number computation: use //
            if isinstance(node.op, ast.Div):
                # match i*(i+1)/2
                if isinstance(node.right, ast.Constant) and node.right.value == 2:
                    left = node.left
                    if (
                        isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mult) and
                        isinstance(left.left, ast.Name) and
                        isinstance(left.right, ast.BinOp) and isinstance(left.right.op, ast.Add) and
                        isinstance(left.right.left, ast.Name) and left.right.left.id == left.left.id and
                        isinstance(left.right.right, ast.Constant) and left.right.right.value == 1
                    ):
                        s = abs_pos(lines, node.lineno, node.col_offset)
                        e = abs_pos(lines, node.end_lineno, node.end_col_offset)
                        edits.append(source[:s] + f"{source[s:e].replace('/', '//', 1)}" + source[e:])

            self.generic_visit(node)

    Visitor().visit(tree)

    # de-duplicate and preserve order
    seen = set()
    out = []
    for edit in edits:
        if edit != source and edit not in seen:
            seen.add(edit)
            out.append(edit)
    return out

LEARNED.append(Rule("triangle_discriminant_and_division", _learned_triangle_discriminant_and_division, symptoms=('wrong')))


def _learned_absolute_distance_and_parity_jumps(source):
    """Targets the misconception that the target position can be handled without taking its absolute value, and that parity can be checked after the loop instead of being part of the loop condition."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def span(node):
        return (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)

    lines = source.splitlines(keepends=True)

    def offset(lineno, col):
        return sum(len(lines[i]) for i in range(lineno - 1)) + col

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.assign = None
            self.while_node = None
            self.if_node = None

        def visit_Assign(self, node):
            if self.assign is None and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "position":
                self.assign = node
            self.generic_visit(node)

        def visit_While(self, node):
            if self.while_node is None:
                self.while_node = node
            self.generic_visit(node)

        def visit_If(self, node):
            if self.if_node is None:
                self.if_node = node
            self.generic_visit(node)

    f = Finder()
    f.visit(tree)

    # Fix 1: wrap input in abs() for symmetric reachability on the number line.
    if f.assign and isinstance(f.assign.value, ast.Call) and isinstance(f.assign.value.func, ast.Name) and f.assign.value.func.id == "int":
        a = f.assign.value.args
        if len(a) == 1:
            start = offset(f.assign.value.lineno, f.assign.value.col_offset)
            end = offset(f.assign.value.end_lineno, f.assign.value.end_col_offset)
            new = "abs(" + source[start:end] + ")"
            out.append(source[:start] + new + source[end:])

    # Fix 2: if the loop only checks triangle sum, strengthen it to also check parity;
    # and if there is a post-loop parity if/else, remove it and print ind directly.
    if f.while_node and isinstance(f.while_node.test, ast.Compare):
        test_src_start = offset(f.while_node.test.lineno, f.while_node.test.col_offset)
        test_src_end = offset(f.while_node.test.end_lineno, f.while_node.test.end_col_offset)
        test_src = source[test_src_start:test_src_end]
        if "somme(ind) < position" in test_src and "or" not in test_src:
            new_test = f"({test_src}) or ((somme(ind) - position) % 2 != 0)"
            out.append(source[:test_src_start] + new_test + source[test_src_end:])

    if f.if_node and isinstance(f.if_node.test, ast.Compare):
        test_src_start = offset(f.if_node.test.lineno, f.if_node.test.col_offset)
        test_src_end = offset(f.if_node.end_lineno, f.if_node.end_col_offset)
        if "somme(ind) - position" in source[test_src_start:test_src_end]:
            # remove the whole if statement
            out.append(source[:offset(f.if_node.lineno, f.if_node.col_offset)] +
                       "print(ind)\n" +
                       source[offset(f.if_node.end_lineno, f.if_node.end_col_offset):])

    return list(dict.fromkeys(out))

LEARNED.append(Rule("absolute_distance_and_parity_jumps", _learned_absolute_distance_and_parity_jumps, symptoms=('wrong')))
