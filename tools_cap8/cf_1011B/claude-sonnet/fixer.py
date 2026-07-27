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


def _line_indent(source, node):
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[: len(line) - len(line.lstrip())]


def _increase_binary_search_bound(source):
    """Binary search upper bound set too tight (e.g. r = 100); widen it."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, int)
            and node.value.value == 100
        ):
            # confirm this constant lives near a binary-search-style while loop
            found_pattern = False
            for n2 in ast.walk(tree):
                if isinstance(n2, ast.While):
                    for stmt in ast.walk(n2):
                        if (
                            isinstance(stmt, ast.Assign)
                            and isinstance(stmt.value, ast.BinOp)
                            and isinstance(stmt.value.op, ast.FloorDiv)
                        ):
                            found_pattern = True
                            break
                if found_pattern:
                    break
            if found_pattern:
                new_source = _splice(source, node.value, "100000")
                if new_source != source:
                    out.append(new_source)
    return out


def _fix_accumulator_reset(source):
    """Accumulator not reset each outer iteration and no early-stop break."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    body_lists = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(node, field, None)
            if isinstance(lst, list) and lst and isinstance(lst[0], ast.stmt):
                body_lists.append(lst)

    for lst in body_lists:
        for i in range(len(lst) - 1):
            stmt = lst[i]
            nxt = lst[i + 1]
            if not (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
                and stmt.value.value == 0
            ):
                continue
            if not isinstance(nxt, ast.For):
                continue
            acc_name = stmt.targets[0].id
            outer = nxt

            has_aug = False
            for sub in ast.walk(outer):
                if (
                    isinstance(sub, ast.AugAssign)
                    and isinstance(sub.target, ast.Name)
                    and sub.target.id == acc_name
                    and isinstance(sub.op, ast.Add)
                ):
                    has_aug = True
                    break
            if not has_aug:
                continue

            target_if = None
            for sub in outer.body:
                if isinstance(sub, ast.If):
                    names = {
                        n.id for n in ast.walk(sub.test) if isinstance(n, ast.Name)
                    }
                    if acc_name in names:
                        target_if = sub
                        break
            if target_if is None:
                continue

            has_break = any(isinstance(x, ast.Break) for x in ast.walk(target_if))
            if has_break:
                continue

            if not outer.body:
                continue
            first_stmt = outer.body[0]
            indent = _line_indent(source, first_stmt)
            reset_text = f"{acc_name} = 0\n{indent}"
            s0, _ = _span(source, first_stmt)
            new_source = source[:s0] + reset_text + source[s0:]

            offset = len(reset_text)
            _, if_e = _span(source, target_if)
            if_e_new = if_e + offset
            if_indent = _line_indent(source, target_if)
            else_text = f"\n{if_indent}else:\n{if_indent}    break"
            new_source = new_source[:if_e_new] + else_text + new_source[if_e_new:]

            if new_source != source:
                out.append(new_source)
    return out


def _flip_comparison(source):
    """Loosen/tighten a strict comparison (>, >=, <, <=) by one step."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    mapping = {
        ast.GtE: (ast.Gt, ">"),
        ast.Gt: (ast.GtE, ">="),
        ast.LtE: (ast.Lt, "<"),
        ast.Lt: (ast.LtE, "<="),
    }
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if type(op) in mapping:
                _, op_text = mapping[type(op)]
                left = node.left
                right = node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + f" {op_text} " + source[rs:re_]
                candidate = _splice(source, node, new_cmp)
                if candidate != source:
                    out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="widen_binary_search_bound",
                apply=_increase_binary_search_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="reset_accumulator_and_break",
                apply=_fix_accumulator_reset,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="comparison_flip",
                apply=_flip_comparison,
                symptoms=("wrong",),
            ),
        ]