from src.core.repair import Rule
LEARNED = []


def _learned_return_accumulator_instead_of_constant_true(source):
    """Fix functions that track uniqueness with a boolean flag but incorrectly return a constant True instead of the accumulated flag."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def span(node):
        return (node.lineno - 1, node.col_offset, node.end_lineno - 1, node.end_col_offset)

    lines = source.splitlines(keepends=True)

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            # Look for: flag = False ... return True at end, and replace the final
            # `return True` with `return flag` when the function has a boolean accumulator.
            assigns = []
            return_nodes = []
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    if isinstance(stmt.value, ast.Constant) and stmt.value.value is False:
                        assigns.append(stmt.targets[0].id)
                if isinstance(stmt, ast.Return):
                    return_nodes.append(stmt)

            if not assigns or not return_nodes:
                return

            last_ret = return_nodes[-1]
            if not (isinstance(last_ret.value, ast.Constant) and last_ret.value.value is True):
                return

            # Prefer the most recently introduced boolean flag variable.
            flag_name = assigns[-1]
            sline, scol, eline, ecol = span(last_ret)
            new_lines = lines[:]
            if sline == eline:
                new_lines[sline] = new_lines[sline][:scol] + f"return {flag_name}" + new_lines[sline][ecol:]
            else:
                new_lines[sline] = new_lines[sline][:scol] + f"return {flag_name}" + new_lines[eline][ecol:]
                for i in range(sline + 1, eline + 1):
                    new_lines[i] = ""
            out.append("".join(new_lines))

    Visitor().visit(tree)
    return out

LEARNED.append(Rule("return_accumulator_instead_of_constant_true", _learned_return_accumulator_instead_of_constant_true, symptoms=('wrong')))
