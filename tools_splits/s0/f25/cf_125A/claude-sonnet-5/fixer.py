from src.core.repair import Rule
import ast

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


def _float_div_vars(tree):
    """Collect names of variables that get turned into floats via /=k or x = x/k."""
    div_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div) \
           and isinstance(node.target, ast.Name):
            div_vars.add(node.target.id)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.BinOp) \
           and isinstance(node.value.op, ast.Div):
            left = node.value.left
            if isinstance(left, ast.Name) and left.id == node.targets[0].id:
                div_vars.add(node.targets[0].id)
    return div_vars


def _int_wrap_str_floordiv(source):
    """str(x // 12) / str(x % 12) should be str(int(x // 12)) etc. when x became a
    float through an earlier division (x /= k or x = x / k)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    div_vars = _float_div_vars(tree)
    if not div_vars:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'str' and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.FloorDiv, ast.Mod)):
                names = {n.id for n in ast.walk(arg) if isinstance(n, ast.Name)}
                if names & div_vars:
                    s, e = _span(source, arg)
                    arg_src = source[s:e]
                    if arg_src.strip().startswith('int('):
                        continue
                    new_arg = 'int(' + arg_src + ')'
                    out.append(_splice(source, arg, new_arg))
    return out


def _is_inch_part(e):
    """Matches (X % 36) // 3 shaped sub-expressions."""
    return (isinstance(e, ast.BinOp) and isinstance(e.op, ast.FloorDiv)
            and isinstance(e.right, ast.Constant) and e.right.value == 3
            and isinstance(e.left, ast.BinOp) and isinstance(e.left.op, ast.Mod)
            and isinstance(e.left.right, ast.Constant) and e.left.right.value == 36)


def _fix_feet_inch_carry(source):
    """Fixes the misconception of computing feet as n//36 and inches as
    (n%36)//3 + rounding separately, which drops the carry when the rounded
    inch count reaches 12. Rewrites the print call to compute the total,
    carry-safe, inch count once and derive feet/inches from it."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'print' and len(node.args) == 2):
            continue
        a0, a1 = node.args

        if not (isinstance(a0, ast.BinOp) and isinstance(a0.op, ast.FloorDiv)
                and isinstance(a0.right, ast.Constant) and a0.right.value == 36):
            continue
        feet_expr = a0.left

        if not (isinstance(a1, ast.BinOp) and isinstance(a1.op, ast.Add)):
            continue

        left, right = a1.left, a1.right
        if _is_inch_part(left):
            inch_part, add_part = left, right
        elif _is_inch_part(right):
            inch_part, add_part = right, left
        else:
            continue

        fs, fe = _span(source, feet_expr)
        feet_text = source[fs:fe]
        ms, me = _span(source, inch_part.left.left)
        mod_base_text = source[ms:me]
        if mod_base_text.strip() != feet_text.strip():
            continue

        as_, ae = _span(source, add_part)
        add_text = source[as_:ae]

        total_expr = '(' + feet_text + '//3+' + add_text + ')'
        new_inner = total_expr + '//12, ' + total_expr + '%12'
        new_call = 'print(' + new_inner + ')'
        out.append(_splice(source, node, new_call))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="wrap_float_floordiv_result_in_int",
                apply=_int_wrap_str_floordiv,
                symptoms=("wrong",),
            ),
            Rule(
                name="feet_inch_rounding_carry_missed",
                apply=_fix_feet_inch_carry,
                symptoms=("wrong",),
            ),
        ]