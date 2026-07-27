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


def _name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    return None


def _iter_blocks(tree):
    for node in ast.walk(tree):
        if hasattr(node, "body") and isinstance(node.body, list):
            yield node.body
        if hasattr(node, "orelse") and isinstance(node.orelse, list) and node.orelse:
            yield node.orelse


def _fix_add_constant_before_floordiv3(source):
    """(x + 2)//3  ->  (x + 1)//3   (wrong ceiling-rounding offset before /3)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            right = node.right
            if isinstance(right, ast.Constant) and right.value == 3:
                left = node.left
                if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add):
                    for side in (left.left, left.right):
                        if isinstance(side, ast.Constant) and isinstance(side.value, int) \
                                and side.value in (0, 2):
                            new_src = _splice(source, side, "1")
                            if new_src != source:
                                out.append(new_src)
    return out


def _fix_round_boundary(source):
    """After `ic = round(...)`, missing carry when ic == 12 inches -> add normalization."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for block in _iter_blocks(tree):
        for i, stmt in enumerate(block):
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Name)
                    and stmt.value.func.id == "round"):
                continue
            ic_name = stmt.targets[0].id
            for j in range(i + 1, len(block)):
                later = block[j]

                if isinstance(later, ast.Assign):
                    tgt_names = [t.id for t in later.targets if isinstance(t, ast.Name)]
                    if ic_name in tgt_names:
                        break

                if isinstance(later, ast.If) and isinstance(later.test, ast.Compare) \
                        and isinstance(later.test.left, ast.Name) \
                        and later.test.left.id == ic_name:
                    break

                target_stmt = None
                ft_name = None
                if isinstance(later, ast.Return) and isinstance(later.value, ast.Tuple) \
                        and len(later.value.elts) == 2:
                    names = [_name_of(e) for e in later.value.elts]
                    if ic_name in names and all(names):
                        target_stmt = later
                        ft_name = names[0] if names[1] == ic_name else names[1]
                elif isinstance(later, ast.Expr) and isinstance(later.value, ast.Call) \
                        and isinstance(later.value.func, ast.Name) \
                        and later.value.func.id == "print" \
                        and len(later.value.args) == 2:
                    names = [_name_of(a) for a in later.value.args]
                    if ic_name in names and all(names):
                        target_stmt = later
                        ft_name = names[0] if names[1] == ic_name else names[1]

                if target_stmt is not None:
                    indent = " " * target_stmt.col_offset
                    snippet = (
                        f"if {ic_name} == 12:\n"
                        f"{indent}    {ft_name} += 1\n"
                        f"{indent}    {ic_name} = 0\n"
                        f"{indent}"
                    )
                    s, _e = _span(source, target_stmt)
                    new_src = source[:s] + snippet + source[s:]
                    if new_src != source:
                        out.append(new_src)
                    break
    return out


def _fix_mod_threshold(source):
    """if n % 3 == 1: ...  ->  if n % 3 == 2: ...  (wrong rounding threshold)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq):
            left = node.test.left
            comp = node.test.comparators[0]
            if isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod) \
                    and isinstance(left.right, ast.Constant) and left.right.value == 3 \
                    and isinstance(comp, ast.Constant) and comp.value == 1:
                has_incr = any(
                    (isinstance(b, ast.AugAssign) and isinstance(b.op, ast.Add))
                    or isinstance(b, ast.Assign)
                    for b in node.body
                )
                if has_incr:
                    new_src = _splice(source, comp, "2")
                    if new_src != source:
                        out.append(new_src)
    return out


def _lt_to_le(source):
    """Relax a strict `<` comparison to `<=` (generic off-by-one slip)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
                and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            new_src = _splice(source, node, new_cmp)
            if new_src != source:
                out.append(new_src)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="rounding_offset_plus2_should_be_plus1",
                apply=_fix_add_constant_before_floordiv3,
                symptoms=("wrong",),
            ),
            Rule(
                name="round_missing_12_inch_carry",
                apply=_fix_round_boundary,
                symptoms=("wrong",),
            ),
            Rule(
                name="mod3_threshold_should_be_2",
                apply=_fix_mod_threshold,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_lt_should_be_lte",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]