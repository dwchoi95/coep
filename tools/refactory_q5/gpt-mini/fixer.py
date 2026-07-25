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


def _replace_slice_with_expr(source, subnode, new_expr_text):
    s, e = _span(source, subnode)
    return source[:s] + new_expr_text + source[e:]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="slice_k_literal_to_variable",
                symptoms=("wrong",),
                apply=self._slice_k_literal_to_variable,
            ),
            Rule(
                name="return_lst_after_removal_should_return_result",
                symptoms=("wrong",),
                apply=self._return_lst_to_result,
            ),
            Rule(
                name="for_loop_includes_extra_iteration_fix",
                symptoms=("wrong",),
                apply=self._range_off_by_one,
            ),
            Rule(
                name="missing_break_after_pop_in_search_loop",
                symptoms=("wrong",),
                apply=self._insert_break_after_pop,
            ),
            Rule(
                name="while_counter_off_by_one_fix",
                symptoms=("wrong",),
                apply=self._while_counter_start_fix,
            ),
            Rule(
                name="while_bound_off_by_one_fix",
                symptoms=("wrong",),
                apply=self._while_condition_fix,
            ),
            Rule(
                name="k_zero_guard_for_topk",
                symptoms=("wrong",),
                apply=self._add_k_zero_guard,
            ),
        ]

    def _slice_k_literal_to_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if node.slice.value == 5:
                    out.append(_replace_slice_with_expr(source, node.slice, "k"))
        return out

    def _return_lst_to_result(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript):
                sub = node.value
                if isinstance(sub.value, ast.Name) and sub.value.id == "lst":
                    new_text = source[_span(source, sub.value)[0]:_span(source, sub.value)[1]].replace(
                        "lst", "result"
                    ) + source[_span(source, sub.slice)[0]:_span(source, sub.slice)[1]]
                    out.append(_splice(source, sub, "result[:k]"))
        return out

    def _range_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                    inner = node.args[0]
                    if isinstance(inner.func, ast.Name) and inner.func.id == "len":
                        out.append(_splice(source, node, "range(len(lst) - 1)"))
                if len(node.args) == 1 and isinstance(node.args[0], ast.UnaryOp):
                    pass
        return out

    def _insert_break_after_pop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                has_pop_append = False
                for stmt in node.body:
                    if isinstance(stmt, ast.If):
                        for inner in stmt.body:
                            if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Call):
                                call = inner.value
                                if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                                    has_pop_append = True
                if has_pop_append:
                    for stmt in node.body:
                        if isinstance(stmt, ast.If):
                            for inner in stmt.body:
                                if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Call):
                                    call = inner.value
                                    if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                                        out.append(_splice(source, stmt, source[_span(source, stmt)[0]:_span(source, stmt)[1]] + "\n                break"))
                                        return out
        return out

    def _while_counter_start_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                t = node.targets[0]
                if isinstance(t, ast.Name) and t.id == "counter":
                    if isinstance(node.value, ast.Constant) and node.value.value == 0:
                        out.append(_splice(source, node.value, "1"))
        return out

    def _while_condition_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
                cmp = node.test
                if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.LtE):
                    out.append(_splice(source, cmp.ops[0], "<"))
                elif len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.GtE):
                    out.append(_splice(source, cmp.ops[0], ">"))
        return out

    def _add_k_zero_guard(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                    cmp = node.test
                    if (
                        isinstance(cmp.left, ast.Name)
                        and cmp.left.id == "lst"
                        and isinstance(cmp.ops[0], ast.Eq)
                        and len(cmp.comparators) == 1
                        and isinstance(cmp.comparators[0], ast.List)
                        and cmp.comparators[0].elts == []
                    ):
                        out.append(_splice(source, cmp, "lst == [] or k == 0"))
        return out