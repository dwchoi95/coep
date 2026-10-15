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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _build_parent_map(tree):
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    return parent


def _enclosing_function(node, parent):
    while node is not None and not isinstance(node, ast.FunctionDef):
        node = parent.get(node)
    return node


def _seq_param_name(func):
    if func is not None and len(func.args.args) >= 2:
        return func.args.args[1].arg
    return "seq"


def _line_indent(source, pos):
    line_start = source.rfind("\n", 0, pos) + 1
    return source[line_start:pos]


# ---------------------------------------------------------------------------
# Rule: relax strict `x < Y` to `x <= Y`
# ---------------------------------------------------------------------------
def _x_lt_to_lte(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left = node.left
            if isinstance(left, ast.Name) and left.id == "x":
                comp = node.comparators[0]
                ls, le = _span(source, left)
                cs, ce = _span(source, comp)
                new_cmp = source[ls:le] + " <= " + source[cs:ce]
                out.append(_splice(source, node, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule: flip wrong direction comparison `x < Y` / `x > Y` (accumulator style)
# ---------------------------------------------------------------------------
def _flip_x_compare_direction(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    flip = {ast.Lt: ("Gt", ">"), ast.Gt: ("Lt", "<")}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(node.left, ast.Name) and node.left.id == "x" and type(op) in flip:
                comp = node.comparators[0]
                if isinstance(comp, ast.Name):
                    _, sym = flip[type(op)]
                    ls, le = _span(source, node.left)
                    cs, ce = _span(source, comp)
                    new_cmp = source[ls:le] + f" {sym} " + source[cs:ce]
                    out.append(_splice(source, node, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule: `for i in len(seq):` -> `for i in range(len(seq)):`
# ---------------------------------------------------------------------------
def _for_over_len_to_range(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "len":
                s, e = _span(source, it)
                new_text = f"range({source[s:e]})"
                out.append(_splice(source, it, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: range(len(seq) - 1) -> range(len(seq))
# ---------------------------------------------------------------------------
def _range_len_minus_one_to_len(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" \
                and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                right = arg.right
                left = arg.left
                if isinstance(right, ast.Constant) and right.value == 1 \
                        and isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                    ls, le = _span(source, left)
                    new_text = source[ls:le]
                    out.append(_splice(source, arg, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: final `return i + 1` (anywhere it ends a block) -> `return len(seq)`
# ---------------------------------------------------------------------------
def _final_return_plus_one_to_len(source):
    tree = _parse(source)
    if tree is None:
        return []
    parent = _build_parent_map(tree)
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            last = body[-1]
            if isinstance(last, ast.Return) and isinstance(last.value, ast.BinOp) \
                    and isinstance(last.value.op, ast.Add):
                right = last.value.right
                if isinstance(right, ast.Constant) and right.value == 1:
                    func = _enclosing_function(node, parent)
                    seq_name = _seq_param_name(func)
                    out.append(_splice(source, last, f"return len({seq_name})"))
    return out


# ---------------------------------------------------------------------------
# Rule: for-loop with a return inside, missing fallback return after it
# ---------------------------------------------------------------------------
def _missing_return_after_for(source):
    tree = _parse(source)
    if tree is None:
        return []
    parent = _build_parent_map(tree)
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            last = body[-1]
            if isinstance(last, ast.For) and not last.orelse:
                has_return = any(isinstance(n, ast.Return) for n in ast.walk(last))
                if has_return:
                    func = _enclosing_function(node, parent)
                    seq_name = _seq_param_name(func)
                    s, e = _span(source, last)
                    indent = _line_indent(source, s)
                    insertion = "\n" + indent + f"return len({seq_name})"
                    out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule: `if cond: return i  else: return stop` inside for -> for/else
# ---------------------------------------------------------------------------
def _if_else_to_for_else(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and not node.orelse and len(node.body) == 1:
            if_node = node.body[0]
            if isinstance(if_node, ast.If) and if_node.orelse and len(if_node.orelse) == 1:
                for_start, _ = _span(source, node)
                body_last_end = _span(source, if_node.body[-1])[1]
                kept_text = source[for_start:body_last_end]
                indent_for = _line_indent(source, for_start)
                orelse_stmt = if_node.orelse[0]
                os_, oe_ = _span(source, orelse_stmt)
                orelse_text = source[os_:oe_]
                new_text = (kept_text + "\n" + indent_for + "else:\n"
                            + indent_for + "    " + orelse_text)
                out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: for body = [If(return i) (no else), Return(stop)] sequential
#       -> move second return into for/else
# ---------------------------------------------------------------------------
def _for_if_return_sequential_to_orelse(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and not node.orelse and len(node.body) == 2:
            if_node, ret_node = node.body
            if isinstance(if_node, ast.If) and not if_node.orelse and isinstance(ret_node, ast.Return):
                for_start, _ = _span(source, node)
                if_end = _span(source, if_node)[1]
                kept_text = source[for_start:if_end]
                indent_for = _line_indent(source, for_start)
                rs, re_ = _span(source, ret_node)
                ret_text = source[rs:re_]
                new_text = (kept_text + "\n" + indent_for + "else:\n"
                            + indent_for + "    " + ret_text)
                out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: fix `seq == () or []` style bare-literal boolean-or typo
# ---------------------------------------------------------------------------
def _fix_bare_or_literal(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            compares = [v for v in node.values if isinstance(v, ast.Compare)]
            bares = [v for v in node.values
                     if isinstance(v, (ast.List, ast.Tuple)) and not v.elts]
            if compares and bares:
                cmp0 = compares[0]
                if len(cmp0.ops) == 1 and isinstance(cmp0.ops[0], ast.Eq):
                    ls, le = _span(source, cmp0.left)
                    left_text = source[ls:le]
                    for bare in bares:
                        bs, be = _span(source, bare)
                        new_text = f"{left_text} == " + source[bs:be]
                        out.append(_splice(source, bare, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: insert `if not seq: return 0` guard before an indexing-first If
# ---------------------------------------------------------------------------
def _mentions_emptiness(test):
    for n in ast.walk(test):
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return True
        if isinstance(n, ast.Compare):
            for c in n.comparators:
                if isinstance(c, (ast.List, ast.Tuple)) and not c.elts:
                    return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "len":
            return True
    return False


def _insert_empty_seq_guard(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            seq_name = _seq_param_name(node)
            idx = 0
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                idx = 1
            if idx >= len(body):
                continue
            first = body[idx]
            if isinstance(first, ast.If):
                test = first.test
                uses_seq_index = any(
                    isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == seq_name
                    for n in ast.walk(test)
                )
                if uses_seq_index and not _mentions_emptiness(test):
                    s, _ = _span(source, first)
                    indent = _line_indent(source, s)
                    insertion = f"if not {seq_name}:\n{indent}    return 0\n{indent}el"
                    out.append(source[:s] + insertion + source[s:])
    return out


# ---------------------------------------------------------------------------
# Rule: remove an erroneous `seq = []` (or similar) reset of a parameter
# ---------------------------------------------------------------------------
def _remove_param_reset_to_empty(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            params = {a.arg for a in node.args.args}
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                    t = stmt.targets[0]
                    if isinstance(t, ast.Name) and t.id in params \
                            and isinstance(stmt.value, (ast.List, ast.Tuple)) and not stmt.value.elts:
                        s, e = _span(source, stmt)
                        line_start = source.rfind("\n", 0, s) + 1
                        line_end = source.find("\n", e)
                        line_end = len(source) if line_end == -1 else line_end + 1
                        out.append(source[:line_start] + source[line_end:])
    return out


# ---------------------------------------------------------------------------
# Rule: unwrap `if seq: ... else: return None` guard around a working loop
# ---------------------------------------------------------------------------
def _unwrap_truthy_seq_guard(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            is_bare_seq = isinstance(test, ast.Name) and test.id == "seq"
            if is_bare_seq and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return):
                ret = node.orelse[0]
                is_none = ret.value is None or (
                    isinstance(ret.value, ast.Constant) and ret.value.value is None
                )
                if is_none and node.body:
                    s_if, _ = _span(source, node)
                    indent_if = _line_indent(source, s_if)
                    first_body_stmt = node.body[0]
                    bs, _ = _span(source, first_body_stmt)
                    body_line_start = source.rfind("\n", 0, bs) + 1
                    indent_body = source[body_line_start:bs]
                    dedent_amount = len(indent_body) - len(indent_if)
                    if dedent_amount > 0 and indent_body.strip() == "":
                        last_body_stmt = node.body[-1]
                        _, be = _span(source, last_body_stmt)
                        body_text = source[body_line_start:be]
                        new_lines = []
                        for line in body_text.splitlines(keepends=True):
                            if line.startswith(indent_body):
                                new_lines.append(line[dedent_amount:])
                            else:
                                new_lines.append(line)
                        new_body_text = "".join(new_lines)
                        out.append(_splice(source, node, new_body_text.rstrip("\n")))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="strict_x_lt_to_lte",
                apply=_x_lt_to_lte,
                symptoms=("wrong",),
            ),
            Rule(
                name="flip_x_compare_direction",
                apply=_flip_x_compare_direction,
                symptoms=("wrong",),
            ),
            Rule(
                name="for_over_len_to_range",
                apply=_for_over_len_to_range,
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="range_len_minus_one_to_len",
                apply=_range_len_minus_one_to_len,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="final_return_plus_one_to_len",
                apply=_final_return_plus_one_to_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_return_after_for",
                apply=_missing_return_after_for,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="if_else_to_for_else",
                apply=_if_else_to_for_else,
                symptoms=("wrong",),
            ),
            Rule(
                name="for_if_return_sequential_to_orelse",
                apply=_for_if_return_sequential_to_orelse,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_bare_or_literal",
                apply=_fix_bare_or_literal,
                symptoms=("wrong",),
            ),
            Rule(
                name="insert_empty_seq_guard",
                apply=_insert_empty_seq_guard,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="remove_param_reset_to_empty",
                apply=_remove_param_reset_to_empty,
                symptoms=("wrong",),
            ),
            Rule(
                name="unwrap_truthy_seq_guard",
                apply=_unwrap_truthy_seq_guard,
                symptoms=("wrong",),
            ),
        ]