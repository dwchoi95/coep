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


def _replace_node(source, old, new_text):
    s, e = _span(source, old)
    return source[:s] + new_text + source[e:]


class Fixer:
    def rules(self):
        return [
            Rule(name="increase_binary_search_upper_bound",
                 apply=self._increase_binary_search_upper_bound,
                 symptoms=("wrong", "timeout")),
            Rule(name="reset_accumulator_inside_loop",
                 apply=self._reset_accumulator_inside_loop,
                 symptoms=("wrong",)),
            Rule(name="fix_binary_search_end_condition",
                 apply=self._fix_binary_search_end_condition,
                 symptoms=("wrong",)),
            Rule(name="range_upper_bound_off_by_one",
                 apply=self._range_upper_bound_off_by_one,
                 symptoms=("wrong",)),
            Rule(name="division_loop_bound_off_by_one",
                 apply=self._division_loop_bound_off_by_one,
                 symptoms=("wrong",)),
        ]

    def _increase_binary_search_upper_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                t = node.targets[0]
                if isinstance(t, ast.Name) and t.id in {"r", "R", "hi", "high", "end"}:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int) and node.value.value <= 1000:
                        out.append(_replace_node(source, node.value, "100000"))
        return out

    def _reset_accumulator_inside_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                body = node.body
                for i, stmt in enumerate(body):
                    if isinstance(stmt, ast.For):
                        prev = body[:i]
                        for p in prev:
                            if isinstance(p, ast.Assign) and len(p.targets) == 1 and isinstance(p.targets[0], ast.Name) and p.targets[0].id in {"s", "k", "cnt", "sum", "total"}:
                                if isinstance(p.value, ast.Constant) and p.value.value == 0:
                                    break
                        else:
                            for inner in stmt.body:
                                if isinstance(inner, ast.AugAssign) and isinstance(inner.target, ast.Name) and inner.target.id in {"s", "k", "cnt", "sum", "total"}:
                                    assign_text = f"{inner.target.id} = 0\n"
                                    out.append(_splice(source, stmt, assign_text + source[_span(source, stmt)[0]:_span(source, stmt)[1]]))
                                    break
        return out

    def _fix_binary_search_end_condition(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                test = node.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Gt):
                    left, right = test.left, test.comparators[0]
                    out.append(_replace_node(source, test, f"{source[_span(source, left)[0]:_span(source, left)[1]]} - {source[_span(source, right)[0]:_span(source, right)[1]]} > 1"))
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.GtE):
                    left, right = test.left, test.comparators[0]
                    out.append(_replace_node(source, test, f"{source[_span(source, left)[0]:_span(source, left)[1]]} - {source[_span(source, right)[0]:_span(source, right)[1]]} > 1"))
        return out

    def _range_upper_bound_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 2:
                    a2 = node.args[1]
                    if isinstance(a2, ast.BinOp) and isinstance(a2.op, ast.Add) and isinstance(a2.right, ast.Constant) and a2.right.value == 1:
                        return out
                    if isinstance(a2, ast.Name):
                        out.append(_replace_node(source, a2, f"{source[_span(source, a2)[0]:_span(source, a2)[1]]} + 1"))
                elif len(node.args) == 1:
                    a1 = node.args[0]
                    if isinstance(a1, ast.Name):
                        out.append(_replace_node(source, a1, f"{source[_span(source, a1)[0]:_span(source, a1)[1]]} + 1"))
        return out

    def _division_loop_bound_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 2:
                    start, end = node.args
                    if isinstance(start, ast.Constant) and start.value == 1 and isinstance(end, ast.BinOp) and isinstance(end.op, ast.FloorDiv):
                        if isinstance(end.right, ast.Name):
                            out.append(_replace_node(source, end, f"{source[_span(source, end)[0]:_span(source, end)[1]]} + 1"))
        return out