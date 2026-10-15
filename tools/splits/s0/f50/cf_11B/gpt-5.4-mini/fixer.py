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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


def _abs_input_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "int":
            if len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "input":
                    new_text = "abs(int(input()))"
                    out.append(_replace_node(source, node, new_text))
    return out


def _abs_assigned_input_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "int":
                if len(val.args) == 1 and isinstance(val.args[0], ast.Call):
                    inp = val.args[0]
                    if isinstance(inp.func, ast.Name) and inp.func.id == "input":
                        new_text = source[_span(source, node.targets[0])[0]:_span(source, node.targets[0])[1]] + " = abs(int(input()))"
                        out.append(_replace_node(source, node, new_text))
    return out


def _int_division_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = node.left
            right = node.right
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            new_text = source[ls:le] + " // " + source[rs:re]
            out.append(_replace_node(source, node, new_text))
    return out


def _lt_to_le_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_replace_node(source, node, source[ls:le] + " <= " + source[rs:re]))
    return out


def _gt_to_ge_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_replace_node(source, node, source[ls:le] + " >= " + source[rs:re]))
    return out


def _eq_to_ge_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_replace_node(source, node, source[ls:le] + " >= " + source[rs:re]))
    return out


def _while_ne_to_lt_rule(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
            cmp = node.test
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.NotEq):
                left, right = cmp.left, cmp.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                out.append(_replace_node(source, cmp, source[ls:le] + " < " + source[rs:re]))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="abs_input", apply=_abs_input_rule, symptoms=("wrong",)),
            Rule(name="abs_assigned_input", apply=_abs_assigned_input_rule, symptoms=("wrong",)),
            Rule(name="int_division", apply=_int_division_rule, symptoms=("wrong",)),
            Rule(name="lt_to_le", apply=_lt_to_le_rule, symptoms=("wrong",)),
            Rule(name="gt_to_ge", apply=_gt_to_ge_rule, symptoms=("wrong",)),
            Rule(name="eq_to_ge", apply=_eq_to_ge_rule, symptoms=("wrong",)),
            Rule(name="while_ne_to_lt", apply=_while_ne_to_lt_rule, symptoms=("wrong",)),
        ]