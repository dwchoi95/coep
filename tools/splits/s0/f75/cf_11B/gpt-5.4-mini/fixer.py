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


def _replace_node(source, target, replacement_src):
    return _splice(source, target, replacement_src)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="absolute_target_before_search",
                symptoms=("wrong",),
                apply=self._abs_target_rule,
            ),
            Rule(
                name="parity_check_before_sum_search",
                symptoms=("wrong",),
                apply=self._parity_sum_rule,
            ),
            Rule(
                name="division_should_be_floor_or_integer_in_jumps",
                symptoms=("wrong", "err:TypeError"),
                apply=self._float_division_rule,
            ),
            Rule(
                name="abs_negative_input_for_symmetric_problem",
                symptoms=("wrong",),
                apply=self._abs_input_rule,
            ),
            Rule(
                name="strict_inequality_to_non_strict",
                symptoms=("wrong",),
                apply=self._lt_to_le_rule,
            ),
        ]

    def _abs_input_rule(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                val = node.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "int":
                    if len(val.args) == 1 and isinstance(val.args[0], ast.Call):
                        inner = val.args[0]
                        if isinstance(inner.func, ast.Name) and inner.func.id == "input":
                            s, e = _span(source, val)
                            out.append(source[:s] + "abs(" + source[s:e] + ")" + source[e:])
        return out

    def _abs_target_rule(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.left, ast.Name) and len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant):
                    if node.comparators[0].value == 0 and isinstance(node.ops[0], (ast.Lt, ast.Gt, ast.LtE, ast.GtE)):
                        s, e = _span(source, node.left)
                        new_left = f"abs({source[s:e]})"
                        out.append(_splice(source, node.left, new_left))
        return out

    def _parity_sum_rule(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Div) and isinstance(left.left, ast.BinOp):
                    s, e = _span(source, node)
                    text = source[s:e]
                    if "/2" in text or " / 2" in text or ")/2" in text:
                        repl = text.replace("<", "<=").replace(">", ">=")
                        if repl != text:
                            out.append(_splice(source, node, repl))
        return out

    def _float_division_rule(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                s, e = _span(source, node)
                text = source[s:e]
                if "/" in text:
                    repl = text.replace("/", "//", 1)
                    if repl != text:
                        out.append(_splice(source, node, repl))
        return out

    def _lt_to_le_rule(self, source):
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