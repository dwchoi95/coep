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


def _pos(node):
    return (node.lineno, node.col_offset)


def _fix_forward_reference(source):
    """A variable that is only later assigned as `alias = list(param)` (or a
    bare alias / slice copy of a parameter) is referenced earlier in the
    function, before the assignment runs. Replace those premature uses with
    the underlying parameter name, which is what the code actually has
    available at that point.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = {a.arg for a in func.args.args}
        for node in ast.walk(func):
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            target_name = node.targets[0].id
            value = node.value
            source_name = None
            if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id in ("list", "sorted", "tuple")
                    and len(value.args) == 1 and isinstance(value.args[0], ast.Name)):
                source_name = value.args[0].id
            elif isinstance(value, ast.Name):
                source_name = value.id
            elif isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name):
                source_name = value.value.id

            if source_name is None or source_name not in params:
                continue
            if source_name == target_name:
                continue

            assign_pos = _pos(node)
            uses = []
            for n in ast.walk(func):
                if (isinstance(n, ast.Name) and n.id == target_name
                        and n is not node.targets[0] and _pos(n) < assign_pos):
                    uses.append(n)
            if not uses:
                continue

            uses.sort(key=_pos, reverse=True)
            new_source = source
            for u in uses:
                new_source = _splice(new_source, u, source_name)
            if new_source != source:
                out.append(new_source)
    return out


_FLIP = {
    ast.Lt: "<=",
    ast.LtE: "<",
    ast.Gt: ">=",
    ast.GtE: ">",
}


def _flip_comparison_strictness(source):
    """Swap a strict/non-strict comparison for its counterpart (< <-> <=,
    > <-> >=). Covers boundary-check slips such as using `x >= max(seq)`
    where the loop structure requires the strict `x > max(seq)`, as well as
    generic off-by-one comparisons gating a sequential search."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if type(op) in _FLIP:
                sym = _FLIP[type(op)]
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " " + sym + " " + source[rs:re_]
                candidate = _splice(source, node, new_cmp)
                if candidate != source:
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="forward_reference_alias_before_assignment",
                apply=_fix_forward_reference,
                symptoms=("err:NameError", "err:UnboundLocalError", "wrong"),
            ),
            Rule(
                name="flip_comparison_strictness",
                apply=_flip_comparison_strictness,
                symptoms=("wrong",),
            ),
        ]