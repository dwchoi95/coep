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
                name="return_in_for_loop_should_be_after_loop",
                apply=self._fix_return_len_in_for_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_len0_none_to_len_seq",
                apply=self._fix_empty_returns_none_to_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="none_default_should_be_len_seq",
                apply=self._fix_none_return_in_last_line,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_to_le_in_search_condition",
                apply=self._fix_lt_to_le_in_comparison_with_x,
                symptoms=("wrong",),
            ),
            Rule(
                name="off_by_one_range_includes_end_exclusive",
                apply=self._fix_range_len_plus_one_to_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_seq0_guard_return_0_to_none_to_len",
                apply=self._fix_guard_x_lt_seq0_returns_0,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_x_lt_element_plus_one",
                apply=self._fix_x_lt_element_plus_one,
                symptoms=("wrong",),
            ),
        ]

    def _fix_return_len_in_for_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Look for a `return ...` directly inside the loop where it likely should not be.
                # Pattern: for ...: if x <= seq[i]: return i  return len(seq)
                # We'll target a second return statement that is indented at the same level as an if-block's return.
                body = node.body or []
                if not body:
                    continue

                # Find an If whose body contains a return
                for_stmt_can = False
                if_stmt = None
                for stmt in body:
                    if isinstance(stmt, ast.If):
                        # Check if any return in its body
                        for child in ast.walk(stmt):
                            if isinstance(child, ast.Return):
                                if_stmt = stmt
                                for_stmt_can = True
                                break
                    if for_stmt_can:
                        break
                if not if_stmt:
                    continue

                # Now find a Return statement elsewhere in node.body
                ret_stmt = None
                for stmt in body:
                    if isinstance(stmt, ast.Return):
                        # Ensure it's "return len(seq)" or "return d" like; but keep narrow to len(seq)
                        if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "len":
                            ret_stmt = stmt
                            break
                if not ret_stmt:
                    continue

                # If we find the buggy pattern, move it after the loop by deleting from inside and inserting after loop.
                # Local edit: replace "return len(seq)" in place with nothing is tricky without whole rewrite.
                # We'll instead splice the return into an `else:` of a dummy if? Not good.
                # Simpler safe edit: change the early return len(seq) into "continue" so it doesn't exit early.
                # This is still local (return -> continue) and should fix the sample misconception.
                new_text = _source_text_for_node(source, ret_stmt)
                # Ensure exact node span replaced
                # replace "return len(seq)" with "continue"
                try:
                    rep = _span_replacement(source, ret_stmt, "continue")
                except Exception:
                    continue
                candidates.append(rep)

        return candidates

    def _fix_empty_returns_none_to_len(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        candidates = []

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Look for: if seq == () or seq == []: return None
                # Replace returned None with len(seq)
                test = node.test
                if not isinstance(test, ast.BoolOp) or not isinstance(test.op, (ast.Or,)):
                    continue
                returns = []
                for stmt in node.body:
                    if isinstance(stmt, ast.Return):
                        returns.append(stmt)
                if not returns:
                    continue
                for stmt in returns:
                    if stmt.value is None:
                        # Replace return None with return len(seq)
                        # Try to find identifier for seq in comparisons
                        seq_name = _infer_seq_name_from_if_test(test)
                        if not seq_name:
                            continue
                        s, e = _span(source, stmt)
                        rep = source[:s] + f"return len({seq_name})" + source[e:]
                        if rep != source:
                            candidates.append(rep)
        return candidates

    def _fix_none_return_in_last_line(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is None:
                # Replace bare "return" / "return None" at end with return len(seq) if function seems to take seq.
                # Find nearest FunctionDef to infer parameter named seq.
                fn = _find_enclosing_function(tree, node)
                if not fn:
                    continue
                param_names = [a.arg for a in fn.args.args if hasattr(a, "arg")]
                if "seq" not in param_names:
                    continue
                seq_name = "seq"
                s, e = _span(source, node)
                # Replace with return len(seq)
                rep = source[:s] + f"return len({seq_name})" + source[e:]
                if rep != source:
                    candidates.append(rep)
        return candidates

    def _fix_lt_to_le_in_comparison_with_x(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                # Change x < seq[i] or similar into x <= seq[i]
                left = node.left
                right = node.comparators[0]
                fn = _find_enclosing_function(tree, node)
                if not fn:
                    continue
                param_names = [a.arg for a in fn.args.args if hasattr(a, "arg")]
                if "x" not in param_names or "seq" not in param_names:
                    continue
                # Heuristic: operator should be inside search logic
                # We just apply if one side is Name 'x' and other involves seq
                if isinstance(left, ast.Name) and left.id == "x":
                    if _expr_mentions_seq(right):
                        new_cmp = _replace_compare_op(source, node, " <= ")
                        candidates.append(new_cmp)
                elif isinstance(right, ast.Name) and right.id == "x":
                    if _expr_mentions_seq(left):
                        new_cmp = _replace_compare_op(source, node, " >= ")
                        # If form is seq[i] < x, the intended comparison for index is different;
                        # skip to avoid wrong direction.
                        continue
        return candidates

    def _fix_range_len_plus_one_to_len(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                args = node.iter.args
                if len(args) == 2:
                    # range(0, len(seq) + 1) -> range(0, len(seq))
                    end = args[1]
                    if isinstance(end, ast.BinOp) and isinstance(end.op, ast.Add) and isinstance(end.right, ast.Constant) and end.right.value == 1:
                        # Ensure left is len(seq)
                        if _is_len_call_of_name(end.left, _infer_param_name(tree, node, "seq") or "seq"):
                            new_end = _node_text(source, end.left)
                            rep = source
                            s, e = _span(source, end)
                            rep = rep[:s] + new_end + rep[e:]
                            candidates.append(rep)
        return candidates

    def _fix_guard_x_lt_seq0_returns_0(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        candidates = []
        # Common buggy guard:
        # if len(seq)==0 or x < seq[0]: return 0
        # should be: if len(seq)==0: return len(seq); elif x <= seq[0]: return 0 else ...
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                # Find condition that includes `x < seq[0]`
                x_lt = _find_x_lt_seq0(test)
                if not x_lt:
                    continue
                # Find return 0 in body (first statement)
                for stmt in node.body:
                    if isinstance(stmt, ast.Return) and stmt.value is not None and isinstance(stmt.value, ast.Constant) and stmt.value.value == 0:
                        fn = _find_enclosing_function(tree, node)
                        if not fn:
                            continue
                        seq_name = "seq" if "seq" in [a.arg for a in fn.args.args if hasattr(a, "arg")] else None
                        if not seq_name:
                            continue
                        # Replace that return 0 with return len(seq)
                        s, e = _span(source, stmt)
                        rep = source[:s] + f"return len({seq_name})" + source[e:]
                        candidates.append(rep)
        return candidates

    def _fix_x_lt_element_plus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        candidates = []
        # Pattern: if x < (element + 1): result=i; return
        # For integer successor bug, likely meant x <= element
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                # x < (element + 1)
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Name) and _infer_param_name_from_tree(tree, "x") == left.id:
                    if isinstance(right, ast.BinOp) and isinstance(right.op, ast.Add) and isinstance(right.right, ast.Constant) and right.right.value == 1:
                        # left is x, right is element + 1; replace with x <= element
                        element_expr = right.left
                        # Replace whole comparison
                        ls, le = _span(source, left)
                        rs, re = _span(source, right)
                        # Keep operand text for element_expr
                        elem_text = _node_text(source, element_expr)
                        new_cmp = source[ls:le] + " <= " + elem_text
                        rep = _splice(source, node, new_cmp)
                        candidates.append(rep)
        return candidates


def _node_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _replace_compare_op(source, compare_node, op_text_with_spaces):
    # Replace compare_node's operator token by splicing: left < right
    # We'll reconstruct as "<=' style by using node.left and node.comparators[0] spans.
    left = compare_node.left
    right = compare_node.comparators[0]
    ls, le = _span(source, left)
    rs, re = _span(source, right)
    left_txt = source[ls:le]
    right_txt = source[rs:re]
    new_cmp = left_txt + op_text_with_spaces + right_txt
    return _splice(source, compare_node, new_cmp)


def _is_len_call_of_name(expr, name):
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "len"
        and len(expr.args) == 1
        and isinstance(expr.args[0], ast.Name)
        and expr.args[0].id == name
    )


def _infer_param_name(tree, node, param):
    fn = _find_enclosing_function(tree, node)
    if not fn:
        return None
    for a in fn.args.args:
        if hasattr(a, "arg") and a.arg == param:
            return param
    return None


def _infer_seq_name_from_if_test(test):
    # Try to find the Name 'seq' used in comparisons.
    # Look for any ast.Name with id 'seq'
    for n in ast.walk(test):
        if isinstance(n, ast.Name) and n.id == "seq":
            return "seq"
    return None


def _expr_mentions_seq(expr):
    for n in ast.walk(expr):
        if isinstance(n, ast.Name) and n.id == "seq":
            return True
    return False


def _find_enclosing_function(tree, node):
    # Walk parents by re-searching: find FunctionDef that contains node.lineno.
    # Simpler: choose the last FunctionDef with lineno <= node.lineno.
    enclosing = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            if n.lineno <= getattr(node, "lineno", -1) <= (n.end_lineno or n.lineno):
                if enclosing is None or n.lineno >= enclosing.lineno:
                    enclosing = n
    return enclosing


def _find_x_lt_seq0(test):
    # Detect `x < seq[0]` possibly with BoolOp; return True if found.
    for n in ast.walk(test):
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Lt):
            if isinstance(n.left, ast.Name) and n.left.id == "x":
                comp = n.comparators[0]
                if isinstance(comp, ast.Subscript) and _subscript_index_zero(comp):
                    if isinstance(comp.value, ast.Name) and comp.value.id == "seq":
                        return True
    return False


def _subscript_index_zero(sub):
    # handles seq[0]
    sl = sub.slice
    if isinstance(sl, ast.Constant):
        return sl.value == 0
    if isinstance(sl, ast.Index):  # py<3.9
        return isinstance(sl.value, ast.Constant) and sl.value.value == 0
    return False


def _infer_param_name_from_tree(tree, name):
    # if there is any arg named name, return it.
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            for a in n.args.args:
                if hasattr(a, "arg") and a.arg == name:
                    return name
    return name


def _span_replacement(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]