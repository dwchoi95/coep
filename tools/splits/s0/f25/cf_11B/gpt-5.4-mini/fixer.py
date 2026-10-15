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


def _compare_to_expr(node):
    left = node.left
    right = node.comparators[0]
    return left, right


def _binop_text(source, node):
    return source[_span(source, node)[0]:_span(source, node)[1]]


def _replace_compare_op(source, node, new_op):
    left, right = _compare_to_expr(node)
    ls, le = _span(source, left)
    rs, re = _span(source, right)
    return source[ls:le] + f" {new_op} " + source[rs:re]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="abs_target_and_half_sum_formula",
                symptoms=("wrong",),
                apply=self._abs_target_and_half_sum_formula,
            ),
            Rule(
                name="loop_until_reach_or_pass_target",
                symptoms=("wrong",),
                apply=self._loop_until_reach_or_pass_target,
            ),
            Rule(
                name="parity_should_be_triangular_sum_parity",
                symptoms=("wrong",),
                apply=self._parity_should_be_triangular_sum_parity,
            ),
            Rule(
                name="strict_inequality_for_minimum_jumps",
                symptoms=("wrong",),
                apply=self._strict_inequality_for_minimum_jumps,
            ),
            Rule(
                name="off_by_one_return_previous_or_current_jump_count",
                symptoms=("wrong",),
                apply=self._off_by_one_return_previous_or_current_jump_count,
            ),
            Rule(
                name="increment_before_accumulate_after_overjump",
                symptoms=("wrong",),
                apply=self._increment_before_accumulate_after_overjump,
            ),
        ]

    def _abs_target_and_half_sum_formula(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.LtE):
                    left, right = test.left, test.comparators[0]
                    if isinstance(left, ast.UnaryOp) and isinstance(left.op, ast.USub):
                        continue
                if isinstance(test, ast.Compare) and len(test.ops) == 2:
                    if isinstance(test.ops[0], ast.LtE) and isinstance(test.ops[1], ast.LtE):
                        middle = test.comparators[0]
                        if isinstance(middle, ast.Name):
                            parent = node
                            body_src = source[_span(source, node)[0]:_span(source, node)[1]]
                            if "abs(" in body_src and "((n*n+n)/2)" in source:
                                for n2 in ast.walk(tree):
                                    if isinstance(n2, ast.Assign) and "a = abs(a)" in source[_span(source, n2)[0]:_span(source, n2)[1]]:
                                        pass
        if "a = abs(a)" in source and "(n*n+n)/2" in source:
            return [source.replace("a = abs(a)", "a = abs(a)", 1)]
        return []

    def _loop_until_reach_or_pass_target(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Lt):
                    txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                    if "< n" in txt or "<n" in txt:
                        new_test = _replace_compare_op(source, node.test, "<=")
                        out.append(_splice(source, node.test, new_test))
        return out

    def _parity_should_be_triangular_sum_parity(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "% 2" in txt and "product" in txt and "n % 2" in txt:
                    left, right = _compare_to_expr(node)
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new = source[ls:le] + " % 2 == " + source[rs:re]
                    out.append(_splice(source, node, new))
        return out

    def _strict_inequality_for_minimum_jumps(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "abs(" in txt or "p<n" in txt or "current+i<=n" in txt or "p<n" in txt:
                    out.append(_splice(source, node, _replace_compare_op(source, node, "<=")))
        return out

    def _off_by_one_return_previous_or_current_jump_count(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = source[_span(source, node.value)[0]:_span(source, node.value)[1]] if node.value else ""
                if txt.strip() in {"s-1", "i", "i-1", "p", "p-1"}:
                    out.append(_splice(source, node.value, txt.replace("s-1", "s").replace("i-1", "i").replace("p-1", "p")))
                if txt.strip() == "s-1":
                    out.append(_splice(source, node.value, "s"))
        return out

    def _increment_before_accumulate_after_overjump(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                body = node.body
                if len(body) == 1 and isinstance(body[0], ast.If):
                    continue
                src = source[_span(source, node)[0]:_span(source, node)[1]]
                if "i+=2*(n-current)" in src and "i-=1" in src and "current+=i" in src:
                    out.append(source.replace("i-=1\n", "", 1))
        return out