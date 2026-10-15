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
            Rule(
                name="fix_recursive_call_name_typo",
                apply=self._fix_recursive_call_name_typo,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="remove_inner_remove_append_in_loop",
                apply=self._remove_inner_remove_append_in_loop,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="fix_topk_return_false_on_large_k",
                apply=self._fix_topk_return_false_on_large_k,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_topk_k_equals_one_return_input",
                apply=self._fix_topk_k_equals_one_return_input,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_topk_unused_recursive_result",
                apply=self._fix_topk_unused_recursive_result,
                symptoms=("wrong",),
            ),
        ]

    def _fix_recursive_call_name_typo(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "top_k":
                if len(node.args) >= 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.Name) and arg.id == "new_lst":
                        s, e = _span(source, arg)
                        out.append(source[:s] + "new_list" + source[e:])
        return out

    def _remove_inner_remove_append_in_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if len(node.body) >= 2:
                    first = node.body[0]
                    second = node.body[1]
                    if isinstance(first, ast.Assign) and isinstance(second, ast.If):
                        if any(isinstance(n, ast.Remove) for n in ast.walk(second)) or any(
                            isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Attribute)
                            and n.func.attr == "remove"
                            for n in ast.walk(second)
                        ):
                            if any(
                                isinstance(n, ast.Call)
                                and isinstance(n.func, ast.Attribute)
                                and n.func.attr == "append"
                                for n in ast.walk(second)
                            ):
                                new_body = [ast.unparse(first)] if hasattr(ast, "unparse") else None
                                if new_body is not None:
                                    s1, e2 = _span(source, first)
                                    s2, e3 = _span(source, second)
                                    replacement = source[s1:e2] + "\n"
                                    out.append(source[:s2] + replacement + source[e3:])
        return out

    def _fix_topk_return_false_on_large_k(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                    op = node.test.ops[0]
                    if isinstance(op, ast.Gt):
                        if any(isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and n.value.value is False for n in ast.walk(node)):
                            new_test = source[_span(source, node.test.left)[0]:_span(source, node.test.comparators[0])[1]]
                            new_test = new_test.replace(">", "<=")
                            out.append(_splice(source, node.test, new_test))
        return out

    def _fix_topk_k_equals_one_return_input(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
                    if isinstance(node.test.ops[0], ast.Eq):
                        if any(isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id == "lst" for n in ast.walk(node)):
                            for n in ast.walk(node):
                                if isinstance(n, ast.Return) and isinstance(n.value, ast.Name) and n.value.id == "lst":
                                    out.append(_splice(source, n.value, "l"))
        return out

    def _fix_topk_unused_recursive_result(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == "top_k":
                    s, e = _span(source, node)
                    out.append(source[:s] + "        l += top_k(lst, k-1)\n" + source[e:])
                    out.append(source[:s] + "        return top_k(lst, k-1)\n" + source[e:])
        return out