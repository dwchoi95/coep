import ast
from src.core.repair import Rule


def _span(source, node):
    """(start, end) char offsets of node in source."""
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="check_against_wrong_list",
                apply=self._check_against_wrong_list,
                symptoms=("wrong",),
            ),
            Rule(
                name="check_membership_in_original_instead_of_seen",
                apply=self._check_membership_in_original_instead_of_seen,
                symptoms=("wrong",),
            ),
            Rule(
                name="concatenate_element_not_list",
                apply=self._concatenate_element_not_list,
                symptoms=("err:TypeError",),
            ),
            Rule(
                name="append_returns_none",
                apply=self._append_returns_none,
                symptoms=("err:TypeError", "err:AttributeError"),
            ),
            Rule(
                name="wrong_variable_name_in_loop",
                apply=self._wrong_variable_name_in_loop,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="missing_import_ordered_dict",
                apply=self._missing_import_ordered_dict,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="for_loop_missing_increment",
                apply=self._for_loop_missing_increment,
                symptoms=("timeout",),
            ),
        ]

    def _check_against_wrong_list(self, source):
        """Fix: if i not in lst should be if i not in output/new_lst/etc."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.NotIn):
                    # Check if comparing against 'lst' (the parameter)
                    if isinstance(node.comparators[0], ast.Name):
                        comp_name = node.comparators[0].id
                        if comp_name == "lst":
                            # Find the accumulator variable
                            for parent_node in ast.walk(tree):
                                if isinstance(parent_node, ast.FunctionDef):
                                    accum_var = None
                                    for stmt in ast.walk(parent_node):
                                        if isinstance(stmt, ast.Assign):
                                            for target in stmt.targets:
                                                if isinstance(target, ast.Name):
                                                    accum_var = target.id
                                    if accum_var and accum_var != "lst":
                                        # Replace comparators[0] name from lst to accum_var
                                        new_comp = source[
                                            :_span(source, node.comparators[0])[0]
                                        ] + accum_var + source[
                                            _span(source, node.comparators[0])[1] :
                                        ]
                                        out.append(new_comp)
                                        break
        return out

    def _check_membership_in_original_instead_of_seen(self, source):
        """Fix: check membership in accumulator, not in original lst."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.NotIn):
                    if isinstance(node.comparators[0], ast.Name):
                        comp_name = node.comparators[0].id
                        if comp_name == "lst":
                            # Find what the accumulator is
                            accum = None
                            for stmt in ast.walk(tree):
                                if isinstance(stmt, ast.Assign):
                                    for target in stmt.targets:
                                        if isinstance(target, ast.Name):
                                            accum = target.id
                            if accum and accum != "lst":
                                s, e = _span(source, node.comparators[0])
                                out.append(source[:s] + accum + source[e:])
        return out

    def _concatenate_element_not_list(self, source):
        """Fix: new_lst + i should be new_lst + [i]."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                # Check if right side is a Name (bare variable, not a list)
                if isinstance(node.right, ast.Name):
                    # and left looks like a list accumulator
                    if isinstance(node.left, ast.Name):
                        s, e = _span(source, node.right)
                        wrapped = "[" + source[s:e] + "]"
                        out.append(source[:s] + wrapped + source[e:])
        return out

    def _append_returns_none(self, source):
        """Fix: newlst = newlst.append(i) should be newlst.append(i)."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Attribute):
                        if node.value.func.attr == "append":
                            # This is an assignment of an append call
                            # Replace with just the call statement
                            call_source = source[
                                _span(source, node.value)[0] : _span(
                                    source, node.value
                                )[1]
                            ]
                            new_stmt = call_source
                            out.append(_splice(source, node, new_stmt))
        return out

    def _wrong_variable_name_in_loop(self, source):
        """Fix: for item in list should be for item in lst."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Name):
                    if node.iter.id == "list":
                        # Replace with 'lst'
                        s, e = _span(source, node.iter)
                        out.append(source[:s] + "lst" + source[e:])
        return out

    def _missing_import_ordered_dict(self, source):
        """Fix: add missing import for OrderedDict."""
        if "OrderedDict" in source and "from collections import OrderedDict" not in source:
            # Add import at the top
            lines = source.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("def "):
                    insert_idx = i
                    break
            new_lines = (
                lines[:insert_idx]
                + ["from collections import OrderedDict"]
                + lines[insert_idx:]
            )
            return ["\n".join(new_lines)]
        return []

    def _for_loop_missing_increment(self, source):
        """Fix: for loop with early removal needs proper increment management."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check if body has a comparison and removal pattern
                has_removal = False
                for stmt in node.body:
                    if isinstance(stmt, ast.If):
                        if isinstance(stmt.body[0], ast.Assign):
                            # This looks like: lst = lst[:j] + lst[j+1:]
                            has_removal = True
                            break

                if has_removal:
                    # Replace for loop with while loop that manages j properly
                    # This is a structural change, but targeted
                    try:
                        # Find the outer while loop and inner for loop
                        for parent in ast.walk(tree):
                            if isinstance(parent, ast.While):
                                if isinstance(parent.body[0], ast.For):
                                    inner_for = parent.body[0]
                                    # Convert to while with proper j increment
                                    s, e = _span(source, inner_for)
                                    # Extract variable names
                                    if isinstance(inner_for.iter, ast.Call):
                                        if isinstance(inner_for.iter.func, ast.Name):
                                            if inner_for.iter.func.id == "range":
                                                # This is: for j in range(i+1, len(lst))
                                                loop_var = inner_for.target.id
                                                start_expr = source[
                                                    _span(source, inner_for.iter.args[0])[
                                                        0
                                                    ] : _span(source, inner_for.iter.args[0])[
                                                        1
                                                    ]
                                                ]
                                                end_expr = source[
                                                    _span(source, inner_for.iter.args[1])[
                                                        0
                                                    ] : _span(source, inner_for.iter.args[1])[
                                                        1
                                                    ]
                                                ]

                                                # Build new while loop
                                                body_lines = []
                                                for body_stmt in inner_for.body:
                                                    body_start, body_end = _span(
                                                        source, body_stmt
                                                    )
                                                    body_lines.append(
                                                        source[body_start:body_end]
                                                    )

                                                new_while = (
                                                    f"{loop_var} = {start_expr}\n"
                                                    f"        while {loop_var} < {end_expr}:\n"
                                                )
                                                for bline in body_lines:
                                                    new_while += "            " + bline + "\n"
                                                new_while += (
                                                    f"            else:\n"
                                                    f"                {loop_var} += 1"
                                                )

                                                out.append(_splice(source, inner_for, new_while))
                    except:
                        pass

        return out