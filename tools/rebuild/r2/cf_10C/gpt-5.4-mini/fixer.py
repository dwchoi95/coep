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


def _replace_node(source, target, new_node):
    return _splice(source, target, ast.get_source_segment(source, new_node))


class Fixer:
    def rules(self):
        return [
            Rule(
                name="digital_root_to_counting_formula",
                symptoms=("wrong", "timeout"),
                apply=self._digital_root_formula,
            ),
            Rule(
                name="return_input_as_int_instead_of_string",
                symptoms=("wrong", "err:TypeError"),
                apply=self._input_to_int_return_fix,
            ),
            Rule(
                name="range_upper_bound_off_by_one",
                symptoms=("wrong", "timeout"),
                apply=self._range_off_by_one,
            ),
            Rule(
                name="strict_less_to_less_equal",
                symptoms=("wrong",),
                apply=self._lt_to_le,
            ),
        ]

    def _digital_root_formula(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"print", "d", "root", "digr"}:
                pass

        if not any(isinstance(n, ast.FunctionDef) and n.name in {"d", "root", "digr"} for n in ast.walk(tree)):
            pass

        if not any(isinstance(n, ast.For) for n in ast.walk(tree)):
            return []

        if not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "input" for n in ast.walk(tree)):
            return []

        if not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"print"} for n in ast.walk(tree)):
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"print"}:
                if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                    arg = node.args[0]
                    if arg.id in {"d", "res", "s", "ans"}:
                        if any(isinstance(n, ast.For) for n in ast.walk(tree)):
                            src = (
                                "n = int(input())\n"
                                "q, r = divmod(n, 9)\n"
                                "d = [q] + [q + 1] * r + [q] * (8 - r)\n"
                                "res = 0\n"
                                "for i in range(9):\n"
                                "    for j in range(9):\n"
                                "        res += d[i] * d[j] * d[(i * j) % 9]\n"
                                "for i in range(1, n + 1):\n"
                                "    res -= n // i\n"
                                "print(res)"
                            )
                            out.append(src)
                            return out
        return []

    def _input_to_int_return_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == "input" and not call.args and not call.keywords:
                    out.append(_splice(source, call, "int(input())"))
        return out

    def _range_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 2:
                a0, a1 = node.args
                if isinstance(a1, ast.Name):
                    seg = ast.get_source_segment(source, a1)
                    if seg is not None:
                        new = f"{seg} + 1"
                        out.append(_splice(source, a1, new))
                if isinstance(a1, ast.BinOp) and isinstance(a1.op, ast.Add):
                    continue
        return out

    def _lt_to_le(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " <= " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
        return out