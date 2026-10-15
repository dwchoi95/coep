from src.core.repair import Rule
LEARNED = []


def _learned_return_uniqueness_count(source):
    """Functions that track matching values in a local tuple/list but incorrectly return True after the loop instead of checking that exactly one match was found."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Finder(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if not node.body:
                return
            last = node.body[-1]
            if not isinstance(last, ast.Return):
                return
            if not isinstance(last.value, ast.Constant) or last.value.value is not True:
                return

            # Look for a local accumulator and a loop that appends matching items,
            # which indicates "unique if exactly one match" logic.
            assigns = []
            loop = None
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    assigns.append(stmt)
                if isinstance(stmt, ast.For):
                    loop = stmt

            if loop is None:
                return

            has_accumulator = False
            acc_name = None
            for a in assigns:
                if isinstance(a.value, ast.Tuple) and len(a.value.elts) == 0:
                    acc_name = a.targets[0].id
                    has_accumulator = True
                    break
                if isinstance(a.value, ast.List) and len(a.value.elts) == 0:
                    acc_name = a.targets[0].id
                    has_accumulator = True
                    break
            if not has_accumulator:
                return

            # Only fire when the loop contains an append/concatenation style update to the accumulator.
            class LoopShape(ast.NodeVisitor):
                found = False
                def visit_AugAssign(self, n):  # e.g. x += (...)
                    if isinstance(n.target, ast.Name) and n.target.id == acc_name:
                        self.found = True
                def visit_Assign(self, n):  # e.g. x = x + (...)
                    if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == acc_name:
                        if isinstance(n.value, ast.BinOp) and isinstance(n.value.left, ast.Name) and n.value.left.id == acc_name:
                            self.found = True

            shape = LoopShape()
            shape.visit(loop)
            if not shape.found:
                return

            # Replace the final unconditional True with a count-based uniqueness check.
            ret = last
            new_text = f"return len({acc_name}) == 1"
            out.append(source[:ret.col_offset + sum(len(line) for line in source.splitlines(True)[:ret.lineno - 1])] +
                       new_text +
                       source[(ret.end_col_offset + sum(len(line) for line in source.splitlines(True)[:ret.end_lineno - 1])):])
            # The above string slicing is line-based; if multiple matches exist we still only emit one edited program.
            raise StopIteration

    try:
        Finder().visit(tree)
    except StopIteration:
        return out
    return []

LEARNED.append(Rule("return_uniqueness_count", _learned_return_uniqueness_count, symptoms=('wrong')))


def _learned_count_exactly_once(source):
    """Fix uniqueness checks that use `> 1` when the intended condition is “appears exactly once”."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class Fixer(ast.NodeVisitor):
        def visit_Compare(self, node):
            if (
                isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Attribute)
                and node.left.func.attr == "count"
                and len(node.ops) == 1
                and len(node.comparators) == 1
                and isinstance(node.ops[0], ast.Gt)
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == 1
            ):
                start = node.left.end_col_offset
                # Replace only the operator/comparator text: `> 1` -> `!= 1`
                seg = ast.get_source_segment(source, node)
                if seg is None:
                    return
                prefix = source.splitlines(keepends=True)
                line = prefix[node.lineno - 1]
                # Compute absolute span
                lines = source.splitlines(keepends=True)
                abs_start = sum(len(lines[i]) for i in range(node.lineno - 1)) + node.left.end_col_offset
                abs_end = sum(len(lines[i]) for i in range(node.end_lineno - 1)) + node.end_col_offset
                edited = source[:abs_start] + " != 1" + source[abs_end:]
                out.append(edited)

    Fixer().visit(tree)
    return out

LEARNED.append(Rule("count_exactly_once", _learned_count_exactly_once, symptoms=('wrong')))
