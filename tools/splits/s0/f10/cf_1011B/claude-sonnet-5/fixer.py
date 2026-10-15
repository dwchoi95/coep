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


def _swap_nm_input_order(source):
    """Fix `m, n = map(int, input().split())` (swapped input order)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Tuple):
            tgt = node.targets[0]
            if len(tgt.elts) == 2 and all(isinstance(e, ast.Name) for e in tgt.elts):
                names = [e.id for e in tgt.elts]
                if names == ['m', 'n']:
                    e0, e1 = tgt.elts
                    s0, e0e = _span(source, e0)
                    s1, e1e = _span(source, e1)
                    if e0e <= s1:
                        new_tgt_text = source[s1:e1e] + source[e0e:s1] + source[s0:e0e]
                        out.append(_splice(source, tgt, new_tgt_text))
    return out


def _divide_by_wrong_count_var(source):
    """Fix final `... // m` that should be `... // n` (n = participants)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    n_name = None
    m_name = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Tuple):
            tgt = node.targets[0]
            val = node.value
            if len(tgt.elts) == 2 and all(isinstance(e, ast.Name) for e in tgt.elts) \
               and isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
               and val.func.id == 'map':
                n_name = tgt.elts[0].id
                m_name = tgt.elts[1].id
                break
    if n_name is None or m_name is None or n_name == m_name:
        return []

    parent = _parent_map(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.FloorDiv, ast.Div)) \
           and isinstance(node.right, ast.Name) and node.right.id == m_name:
            p = parent.get(node)
            is_output = False
            if isinstance(p, ast.Call) and isinstance(p.func, ast.Name) and p.func.id == 'print':
                is_output = True
            if isinstance(p, ast.Return):
                is_output = True
            if is_output:
                out.append(_splice(source, node.right, n_name))
    return out


def _sum_counts_to_max_counts(source):
    """Fix `sum(counts) // n`-style aggregation that should use max()."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    parent = _parent_map(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'sum' and node.args:
            arg = node.args[0]
            valid = False
            if isinstance(arg, ast.Attribute) and arg.attr == 'values':
                valid = True
            elif isinstance(arg, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
                for n2 in ast.walk(arg):
                    if isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute) \
                       and n2.func.attr == 'count':
                        valid = True
                        break
            if not valid:
                continue
            p = parent.get(node)
            if isinstance(p, ast.BinOp) and isinstance(p.op, (ast.Div, ast.FloorDiv)) \
               and p.left is node:
                fs, fe = _span(source, node.func)
                out.append(source[:fs] + 'max' + source[fe:])
    return out


def _counter_missing_values(source):
    """Fix `max(cnt) // n` where cnt is a Counter/dict (missing .values())."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    counter_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            is_counter = False
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
               and val.func.id == 'Counter':
                is_counter = True
            elif isinstance(val, ast.DictComp):
                is_counter = True
            if is_counter:
                counter_names.add(node.targets[0].id)
    if not counter_names:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id in ('max', 'min', 'sum') and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Name) and arg.id in counter_names:
                s, e = _span(source, arg)
                out.append(source[:s] + source[s:e] + '.values()' + source[e:])
    return out


def _round_div_to_floor_div(source):
    """Fix `round(a / b)` used where floor division `a // b` is needed."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == 'round' and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                ls, le = _span(source, arg.left)
                rs, re_ = _span(source, arg.right)
                new_expr = source[ls:le] + ' // ' + source[rs:re_]
                out.append(_splice(source, node, new_expr))
    return out


def _cmp_flip(source):
    """Relax/tighten a strict comparison by one notch (Lt<->Le, Gt<->Ge)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    mapping = {
        ast.Lt: ' <= ',
        ast.LtE: ' < ',
        ast.Gt: ' >= ',
        ast.GtE: ' > ',
    }
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and type(node.ops[0]) in mapping:
            replacement_op = mapping[type(node.ops[0])]
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + replacement_op + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="swap_nm_input_order",
                apply=_swap_nm_input_order,
                symptoms=("wrong",),
            ),
            Rule(
                name="divide_by_wrong_count_var",
                apply=_divide_by_wrong_count_var,
                symptoms=("wrong",),
            ),
            Rule(
                name="sum_counts_should_be_max_counts",
                apply=_sum_counts_to_max_counts,
                symptoms=("wrong",),
            ),
            Rule(
                name="counter_missing_values",
                apply=_counter_missing_values,
                symptoms=("wrong",),
            ),
            Rule(
                name="round_div_should_be_floor_div",
                apply=_round_div_to_floor_div,
                symptoms=("wrong",),
            ),
            Rule(
                name="comparison_off_by_one",
                apply=_cmp_flip,
                symptoms=("wrong",),
            ),
        ]