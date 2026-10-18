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


def _abs_input_to_jump_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id in {"x", "a"}:
                val = node.value
                if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "int" and len(val.args) == 1:
                    inp = val.args[0]
                    if isinstance(inp, ast.Call) and isinstance(inp.func, ast.Name) and inp.func.id == "input":
                        new_assign = f"{tgt.id} = abs(int(input()))"
                        out.append(_splice(source, node, new_assign))
        if isinstance(node, ast.While):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.NotEq):
                left, right = test.left, test.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                    if left.id in {"s", "pos"} and right.id in {"x", "a"}:
                        body = node.body
                        if len(body) >= 2 and isinstance(body[0], ast.AugAssign) and isinstance(body[0].target, ast.Name):
                            aug = body[0]
                            if isinstance(aug.op, ast.Add) and isinstance(aug.target, ast.Name) and aug.target.id in {"n", "count", "jumps"}:
                                s1, e1 = _span(source, test)
                                new_test = f"{left.id} < {right.id} or ({left.id}-{right.id}) % 2 != 0"
                                out.append(_splice(source, test, new_test))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod):
                if isinstance(right, ast.Constant) and right.value == 0:
                    pass
    return out


def _map_input_to_int(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "map":
                if len(val.args) >= 2:
                    a0, a1 = val.args[0], val.args[1]
                    if isinstance(a0, ast.Name) and a0.id == "int" and isinstance(a1, ast.Call):
                        if isinstance(a1.func, ast.Name) and a1.func.id == "input":
                            tgt = node.targets[0]
                            if isinstance(tgt, ast.Name):
                                out.append(_splice(source, node, f"{tgt.id} = abs(int(input()))"))
    return out


def _fix_while_compare_not_eq(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.NotEq):
                left = node.test.left
                right = node.test.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                    if left.id in {"pos", "s"} and right.id in {"x", "a"}:
                        new_test = f"{left.id} < {right.id} or ({left.id}-{right.id}) % 2 != 0"
                        out.append(_splice(source, node.test, new_test))
    return out


def _fix_parity_formula(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            body = node.body
            if len(body) >= 2 and isinstance(body[0], ast.If):
                ifs = body[0]
                if isinstance(ifs.test, ast.Compare) and len(ifs.test.ops) == 1:
                    op = ifs.test.ops[0]
                    if isinstance(op, ast.Eq) and isinstance(ifs.test.left, ast.Name) and isinstance(ifs.test.comparators[0], ast.Constant):
                        if ifs.test.comparators[0].value == 0:
                            pass
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="input_needs_abs_and_jump_loop",
                apply=_abs_input_to_jump_loop,
                symptoms=("wrong", "err:ValueError"),
            ),
            Rule(
                name="map_input_should_parse_integer",
                apply=_map_input_to_int,
                symptoms=("wrong", "err:ValueError"),
            ),
            Rule(
                name="while_not_equal_should_use_parity_guard",
                apply=_fix_while_compare_not_eq,
                symptoms=("wrong",),
            ),
        ]