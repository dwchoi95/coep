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


def _parent_map(tree):
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    return parent


def _is_int_input_call(node):
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'int'
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Call)
            and isinstance(node.args[0].func, ast.Name)
            and node.args[0].func.id == 'input')


def _wrap_input_abs(source):
    """Fix the misconception of forgetting abs() around the read integer."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parent = _parent_map(tree)
    out = []
    for node in ast.walk(tree):
        if _is_int_input_call(node):
            p = parent.get(node)
            if isinstance(p, ast.Call) and isinstance(p.func, ast.Name) and p.func.id == 'abs':
                continue
            s, e = _span(source, node)
            orig = source[s:e]
            new_src = source[:s] + "abs(" + orig + ")" + source[e:]
            if new_src != source:
                out.append(new_src)
    return out


def _div_to_floordiv(source):
    """Fix using true division ('/') instead of floor division ('//') in
    triangular-number arithmetic, which causes float precision errors for
    large inputs."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    div_nodes = [n for n in ast.walk(tree)
                 if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)]
    if not div_nodes:
        return []
    out = []

    # Candidate: convert every '/' to '//' in the whole module.
    new_src = source
    # Apply from the last occurrence to the first to keep offsets valid.
    for node in sorted(div_nodes, key=lambda n: _span(source, n)[0], reverse=True):
        s, e = _span(new_src, node)
        left_txt = new_src[s:_span(new_src, node.left)[1]]
        # Find operator location: between left end and right start.
        left_end = _span(new_src, node.left)[1]
        right_start = _span(new_src, node.right)[0]
        op_region = new_src[left_end:right_start]
        if '/' in op_region and '//' not in op_region:
            new_op_region = op_region.replace('/', '//', 1)
            new_src = new_src[:left_end] + new_op_region + new_src[right_start:]
    if new_src != source:
        out.append(new_src)

    # Also candidates changing a single division at a time.
    for node in div_nodes:
        left_end = _span(source, node.left)[1]
        right_start = _span(source, node.right)[0]
        op_region = source[left_end:right_start]
        if '/' in op_region and '//' not in op_region:
            new_op_region = op_region.replace('/', '//', 1)
            variant = source[:left_end] + new_op_region + source[right_start:]
            if variant != source:
                out.append(variant)
    return out


def _add_parity_clause(source):
    """Fix the core Jumping-Jack misconception: stopping a position/target
    comparison loop as soon as the target is reached/passed, without also
    requiring that the remaining distance have the right parity."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        if not isinstance(test.ops[0], (ast.Lt, ast.LtE)):
            continue
        left, right = test.left, test.comparators[0]
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        left_txt = source[ls:le]
        right_txt = source[rs:re_]
        ts, te = _span(source, test)
        orig_test_txt = source[ts:te]
        new_test = (orig_test_txt
                    + " or (" + left_txt + " - " + right_txt + ") % 2 != 0")
        variant = _splice(source, test, new_test)
        if variant != source:
            out.append(variant)
    return out


def _flip_bound_comparison(source):
    """Generic slip: a strict/non-strict comparison operator was chosen the
    wrong way around in a loop condition."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    swap = {
        ast.Lt: ' < ',
        ast.LtE: ' <= ',
        ast.Gt: ' > ',
        ast.GtE: ' >= ',
    }
    flip_to = {
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
    }
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and type(node.ops[0]) in flip_to:
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_op = swap[flip_to[type(node.ops[0])]]
            new_cmp = source[ls:le] + new_op + source[rs:re_]
            variant = _splice(source, node, new_cmp)
            if variant != source:
                out.append(variant)
    return out


def _range_bound_off_by_one(source):
    """Generic slip: an off-by-one bound on a range() call used for search."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'range' and len(node.args) >= 2:
            stop = node.args[1]
            ss, se = _span(source, stop)
            stop_txt = source[ss:se]
            new_stop = "(" + stop_txt + ") + 1"
            variant = source[:ss] + new_stop + source[se:]
            if variant != source:
                out.append(variant)
            new_stop2 = "(" + stop_txt + ") - 1"
            variant2 = source[:ss] + new_stop2 + source[se:]
            if variant2 != source:
                out.append(variant2)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="wrap_input_abs",
                apply=_wrap_input_abs,
                symptoms=("wrong",),
            ),
            Rule(
                name="div_to_floordiv",
                apply=_div_to_floordiv,
                symptoms=("wrong",),
            ),
            Rule(
                name="add_parity_clause_to_while",
                apply=_add_parity_clause,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="flip_bound_comparison",
                apply=_flip_bound_comparison,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_bound_off_by_one",
                apply=_range_bound_off_by_one,
                symptoms=("wrong",),
            ),
        ]