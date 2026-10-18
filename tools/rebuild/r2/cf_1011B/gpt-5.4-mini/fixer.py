import ast
from src.core.repair import Rule


def _span(source, node):
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
            Rule(name="increase_binary_search_upper_bound",
                 apply=self._increase_binary_search_upper_bound,
                 symptoms=("wrong",)),
            Rule(name="fix_count_division_lower_bound",
                 apply=self._fix_count_division_lower_bound,
                 symptoms=("wrong",)),
            Rule(name="strict_comparison_to_non_strict",
                 apply=self._strict_comparison_to_non_strict,
                 symptoms=("wrong",)),
        ]

    def _increase_binary_search_upper_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                if node.value.value == 100:
                    out.append(_splice(source, node.value, "100000"))
        return out

    def _fix_count_division_lower_bound(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.GtE):
                if isinstance(node.left, ast.Name) and node.left.id in {"k", "to", "cnt", "count", "days"}:
                    if len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Name):
                        left_src = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                        right_src = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                        new_cmp = f"{left_src} > {right_src}"
                        out.append(_splice(source, node, new_cmp))
        return out

    def _strict_comparison_to_non_strict(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, ast.Lt):
                    left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                    out.append(_splice(source, node, f"{left} <= {right}"))
                elif isinstance(op, ast.Gt):
                    left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                    out.append(_splice(source, node, f"{left} >= {right}"))
        return out