from src.core.repair import Rule
import ast


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


def _replace_node(source, target, replacement):
    s, e = _span(source, target)
    return source[:s] + replacement + source[e:]


class Fixer:
    def rules(self):
        return [
            Rule(name="move_return_out_of_loop",
                 apply=self._move_return_out_of_loop,
                 symptoms=("wrong", "timeout")),
            Rule(name="wrong_return_value_or_type",
                 apply=self._wrong_return_value_or_type,
                 symptoms=("wrong",)),
            Rule(name="strict_lt_to_lte_in_search",
                 apply=self._strict_lt_to_lte_in_search,
                 symptoms=("wrong",)),
            Rule(name="strict_gt_to_gte_in_search",
                 apply=self._strict_gt_to_gte_in_search,
                 symptoms=("wrong",)),
            Rule(name="off_by_one_return_len_not_len_plus_one",
                 apply=self._off_by_one_return_len_not_len_plus_one,
                 symptoms=("wrong",)),
            Rule(name="replace_broken_index_return",
                 apply=self._replace_broken_index_return,
                 symptoms=("wrong",)),
            Rule(name="fix_empty_sequence_guard",
                 apply=self._fix_empty_sequence_guard,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="fix_broken_counting_return",
                 apply=self._fix_broken_counting_return,
                 symptoms=("wrong",)),
            Rule(name="fix_enumerate_compare_eq",
                 apply=self._fix_enumerate_compare_eq,
                 symptoms=("wrong",)),
        ]

    def _move_return_out_of_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                ret = node.body[0]
                if isinstance(ret.value, ast.Call) and getattr(ret.value.func, "id", None) == "len":
                    if ret.value.args and isinstance(ret.value.args[0], ast.Name):
                        if isinstance(node.parent, ast.For) if hasattr(node, "parent") else False:
                            pass
            if isinstance(node, ast.For) and len(node.body) == 1 and isinstance(node.body[0], ast.If):
                inner = node.body[0]
                if any(isinstance(stmt, ast.Return) for stmt in inner.body):
                    ret = next(stmt for stmt in inner.body if isinstance(stmt, ast.Return))
                    if ret.value is not None and isinstance(ret.value, ast.Call) and getattr(ret.value.func, "id", None) == "len":
                        if isinstance(ret.value.args[0], ast.Name):
                            if _span(source, ret)[0] > _span(source, node)[0]:
                                new = source[_span(source, node)[0]:_span(source, ret)[0]]
                                return [source[:_span(source, node)[0]] + source[_span(source, node)[0]:_span(source, inner)[0]] + source[_span(source, inner)[0]:_span(source, ret)[0]] + source[_span(source, ret)[1]:]]
        return []

    def _wrong_return_value_or_type(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                if isinstance(node.value, ast.Tuple) and len(node.value.elts) == 1:
                    out.append(_splice(source, node.value, "0"))
                elif isinstance(node.value, ast.List) and len(node.value.elts) == 1:
                    out.append(_splice(source, node.value, "0"))
                elif isinstance(node.value, ast.NameConstant) and node.value.value is False:
                    out.append(_splice(source, node.value, "0"))
                elif isinstance(node.value, ast.Constant) and node.value.value in ("empty", None, False):
                    out.append(_splice(source, node.value, "0"))
        return out

    def _strict_lt_to_lte_in_search(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                out.append(_splice(source, node, f"{left} <= {right}"))
        return out

    def _strict_gt_to_gte_in_search(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                out.append(_splice(source, node, f"{left} >= {right}"))
        return out

    def _off_by_one_return_len_not_len_plus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if isinstance(node.left, ast.Call) and getattr(node.left.func, "id", None) == "len":
                    if isinstance(node.right, ast.Constant) and node.right.value == 1:
                        out.append(_splice(source, node, source[_span(source, node.left)[0]:_span(source, node.left)[1]]))
        return out

    def _replace_broken_index_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "index":
                    out.append(_splice(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]]))
        return out

    def _fix_empty_sequence_guard(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and any(isinstance(op, ast.Eq) for op in node.ops):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if txt in ("seq == 0", "seq == ()", "seq == []", "len(seq)==0", "len(seq) == 0", "not seq"):
                    out.append(_splice(source, node, "len(seq) == 0"))
        return out

    def _fix_broken_counting_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                if node.value.id in {"x", "elem", "element", "i"}:
                    out.append(_splice(source, node.value, "counter"))
        return out

    def _fix_enumerate_compare_eq(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Lt):
                    left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                    out.append(_splice(source, node, f"{left} <= {right}"))
        return out