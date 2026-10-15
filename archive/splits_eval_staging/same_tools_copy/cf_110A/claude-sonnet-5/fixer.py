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


def _fix_print_case(source):
    """Normalize yes/no/Yes/No printed literals to YES/NO."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            for arg in node.args:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        low = sub.value.lower()
                        if low in ("yes", "no") and sub.value != low.upper():
                            edits.append(sub)
    if not edits:
        return []
    edits_sorted = sorted(edits, key=lambda n: _span(source, n)[0], reverse=True)
    new_source = source
    for node in edits_sorted:
        s, e = _span(new_source if new_source is source else source, node)
    # apply sequentially on a mutable copy using original spans computed once
    edits_with_spans = [( _span(source, n), n.value.lower().upper()) for n in edits_sorted]
    new_source = source
    for (s, e), text in edits_with_spans:
        orig = source[s:e]
        quote = orig[0] if orig and orig[0] in "'\"" else '"'
        new_source = new_source[:s] + quote + text + quote + new_source[e:]
    return [new_source]


def _int_digit_to_str(source):
    """Comparing a char (Name/Subscript) to an int literal 4/7 instead of '4'/'7'."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op, comp in zip(node.ops, node.comparators):
                if (isinstance(op, (ast.Eq, ast.Is))
                        and isinstance(comp, ast.Constant)
                        and isinstance(comp.value, int)
                        and not isinstance(comp.value, bool)
                        and comp.value in (4, 7)
                        and isinstance(node.left, (ast.Name, ast.Subscript))):
                    edits.append(comp)
    if not edits:
        return []
    edits_sorted = sorted(edits, key=lambda n: _span(source, n)[0], reverse=True)
    new_source = source
    for comp in edits_sorted:
        new_source = _splice(new_source, comp, f"'{comp.value}'")
    return [new_source]


def _str_literal_to_int_when_call(source):
    """Comparing the result of a call (e.g. len(...)) to string '4'/'7' instead of int."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Call):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.Is)) and isinstance(comp, ast.Constant) and comp.value in ("4", "7"):
                    edits.append(comp)
    if not edits:
        return []
    edits_sorted = sorted(edits, key=lambda n: _span(source, n)[0], reverse=True)
    new_source = source
    for comp in edits_sorted:
        new_source = _splice(new_source, comp, comp.value)
    return [new_source]


def _compare_with_or_literal(source):
    """x == (4 or 7) misconception -> x in (4, 7)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            comp = node.comparators[0]
            if isinstance(comp, ast.BoolOp) and isinstance(comp.op, ast.Or) and all(
                    isinstance(v, ast.Constant) for v in comp.values):
                ls, le = _span(source, node.left)
                left_text = source[ls:le]

                def fmt(v):
                    return repr(v) if isinstance(v, str) else str(v)

                vals = ", ".join(fmt(v.value) for v in comp.values)
                new_text = f"{left_text} in ({vals})"
                out.append(_splice(source, node, new_text))
    return out


def _boolop_bare_constant(source):
    """x == 4 or 7 (bare constant, missing repeated comparison) -> x in (4, 7)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            cmp_node, const_node = None, None
            if isinstance(a, ast.Compare) and isinstance(b, ast.Constant):
                cmp_node, const_node = a, b
            elif isinstance(b, ast.Compare) and isinstance(a, ast.Constant):
                cmp_node, const_node = b, a
            if cmp_node is not None and len(cmp_node.ops) == 1 and isinstance(cmp_node.ops[0], (ast.Eq, ast.Is)):
                comp = cmp_node.comparators[0]
                if isinstance(comp, ast.Constant):
                    ls, le = _span(source, cmp_node.left)
                    left_text = source[ls:le]

                    def fmt(v):
                        return repr(v) if isinstance(v, str) else str(v)

                    new_text = f"{left_text} in ({fmt(comp.value)}, {fmt(const_node.value)})"
                    out.append(_splice(source, node, new_text))
    return out


def _mod_check_to_eq(source):
    """count % 4 == 0 or count % 7 == 0 -> count == 4 or count == 7."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    def is_mod_zero(cmp, k):
        return (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq)
                and isinstance(cmp.comparators[0], ast.Constant) and cmp.comparators[0].value == 0
                and isinstance(cmp.left, ast.BinOp) and isinstance(cmp.left.op, ast.Mod)
                and isinstance(cmp.left.right, ast.Constant) and cmp.left.right.value == k)

    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            a, b = node.values
            if is_mod_zero(a, 4) and is_mod_zero(b, 7):
                xs, xe = _span(source, a.left.left)
                x_text = source[xs:xe]
                new_text = f"{x_text} == 4 or {x_text} == 7"
                out.append(_splice(source, node, new_text))
            elif is_mod_zero(a, 7) and is_mod_zero(b, 4):
                xs, xe = _span(source, a.left.left)
                x_text = source[xs:xe]
                new_text = f"{x_text} == 7 or {x_text} == 4"
                out.append(_splice(source, node, new_text))
    return out


def _wrong_var_digit_check(source):
    """Inside a while-loop digit extraction, comparing the whole number
    instead of the extracted digit variable to 4/7."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        digit_assigns = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                val = stmt.value
                if (isinstance(val, ast.BinOp) and isinstance(val.op, ast.Mod)
                        and isinstance(val.left, ast.Name) and isinstance(val.right, ast.Constant)
                        and val.right.value == 10):
                    digit_assigns.append((stmt.targets[0].id, val.left.id))
        for digitvar, nvar in digit_assigns:
            if digitvar == nvar:
                continue
            name_nodes = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    for cmp_node in ast.walk(sub.test):
                        if (isinstance(cmp_node, ast.Compare) and isinstance(cmp_node.left, ast.Name)
                                and cmp_node.left.id == nvar):
                            for comp in cmp_node.comparators:
                                if isinstance(comp, ast.Constant) and comp.value in (4, 7):
                                    name_nodes.append(cmp_node.left)
            if not name_nodes:
                continue
            seen = set()
            uniq = []
            for nn in name_nodes:
                key = _span(source, nn)
                if key not in seen:
                    seen.add(key)
                    uniq.append(nn)
            uniq.sort(key=lambda n: _span(source, n)[0], reverse=True)
            new_source = source
            for nn in uniq:
                new_source = _splice(new_source, nn, digitvar)
            if new_source != source:
                out.append(new_source)
    return out


def _range_off_by_one(source):
    """range(..., len(x) - 1) that drops the last character -> remove the -1."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            args = node.args
            target = None
            if len(args) == 1:
                target = args[0]
            elif len(args) == 2:
                target = args[1]
            if (target is not None and isinstance(target, ast.BinOp) and isinstance(target.op, ast.Sub)
                    and isinstance(target.right, ast.Constant) and target.right.value == 1
                    and isinstance(target.left, ast.Call) and isinstance(target.left.func, ast.Name)
                    and target.left.func.id == "len"):
                ls, le = _span(source, target.left)
                out.append(_splice(source, target, source[ls:le]))
    return out


def _fix_boolop_logic(source):
    """De Morgan slip: `x != a or x != b` (always true) should be `and`;
    `x == a and x == b` (always false) should be `or`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and len(node.values) == 2:
            a, b = node.values
            if (isinstance(a, ast.Compare) and isinstance(b, ast.Compare)
                    and len(a.ops) == 1 and len(b.ops) == 1
                    and isinstance(a.left, ast.Name) and isinstance(b.left, ast.Name)
                    and a.left.id == b.left.id):
                opa, opb = a.ops[0], b.ops[0]
                la_s, la_e = _span(source, a)
                lb_s, lb_e = _span(source, b)
                if isinstance(node.op, ast.Or) and isinstance(opa, ast.NotEq) and isinstance(opb, ast.NotEq):
                    new_full = source[la_s:la_e] + " and " + source[lb_s:lb_e]
                    out.append(_splice(source, node, new_full))
                elif isinstance(node.op, ast.And) and isinstance(opa, ast.Eq) and isinstance(opb, ast.Eq):
                    new_full = source[la_s:la_e] + " or " + source[lb_s:lb_e]
                    out.append(_splice(source, node, new_full))
    return out


def _fix_bad_augassign(source):
    """`x =+ 1` (parsed as x = +1) typo'd for `x += 1`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.UnaryOp) and isinstance(val.op, ast.UAdd) and isinstance(val.operand, ast.Constant):
                target_name = node.targets[0].id
                new_text = f"{target_name} += {val.operand.value}"
                out.append(_splice(source, node, new_text))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="print_case_yes_no", apply=_fix_print_case, symptoms=("wrong",)),
            Rule(name="char_compared_to_int_digit", apply=_int_digit_to_str, symptoms=("wrong",)),
            Rule(name="call_result_compared_to_str_digit", apply=_str_literal_to_int_when_call,
                 symptoms=("wrong",)),
            Rule(name="compare_eq_boolop_literal", apply=_compare_with_or_literal, symptoms=("wrong",)),
            Rule(name="boolop_bare_constant", apply=_boolop_bare_constant, symptoms=("wrong",)),
            Rule(name="mod_check_should_be_eq", apply=_mod_check_to_eq, symptoms=("wrong",)),
            Rule(name="wrong_var_digit_check", apply=_wrong_var_digit_check, symptoms=("wrong",)),
            Rule(name="range_off_by_one_len_minus_1", apply=_range_off_by_one, symptoms=("wrong",)),
            Rule(name="demorgan_and_or_swap", apply=_fix_boolop_logic, symptoms=("wrong",)),
            Rule(name="bad_augassign_typo", apply=_fix_bad_augassign, symptoms=("wrong",)),
        ]