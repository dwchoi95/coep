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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _slots_from_print(source, call):
    """Try to find the two value-expressions (feet, inch) fed to a print call."""
    if len(call.args) >= 2:
        return call.args[0], call.args[1]
    if len(call.args) == 1:
        a = call.args[0]
        if isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute) and a.func.attr == "format":
            if len(a.args) >= 2:
                return a.args[0], a.args[1]
        if isinstance(a, ast.JoinedStr):
            vals = [v.value for v in a.values if isinstance(v, ast.FormattedValue)]
            if len(vals) >= 2:
                return vals[0], vals[1]
        if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Add):
            calls = []

            def collect(node):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                    collect(node.left)
                    collect(node.right)
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id == "str" and len(node.args) == 1):
                    calls.append(node.args[0])

            collect(a)
            if len(calls) >= 2:
                return calls[0], calls[1]
    return None


def _find_print_calls(tree):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "print":
                out.append(node)
    return out


def _carry_inch_to_feet(source):
    """Insert a feet/inch carry-over guard before the final print of two values."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in _find_print_calls(tree):
            call = node.value
            slots = _slots_from_print(source, call)
            if not slots:
                continue
            n0, n1 = slots
            s, e = _span(source, node)
            line_start = source.rfind("\n", 0, s) + 1
            indent = source[line_start:s]
            s0, e0 = _span(source, n0)
            s1, e1 = _span(source, n1)
            feet_src = source[s0:e0]
            inch_src = source[s1:e1]
            if feet_src == "__feet" or inch_src == "__inch":
                continue
            stmt_src = source[s:e]
            spans = sorted([(s0, e0, "__feet"), (s1, e1, "__inch")], key=lambda t: t[0], reverse=True)
            new_stmt = stmt_src
            for sp_s, sp_e, name in spans:
                rel_s, rel_e = sp_s - s, sp_e - s
                new_stmt = new_stmt[:rel_s] + name + new_stmt[rel_e:]
            insertion = (
                "__feet = {feet}\n"
                "{indent}__inch = {inch}\n"
                "{indent}if __inch == 12:\n"
                "{indent}    __feet += 1\n"
                "{indent}    __inch = 0\n"
                "{indent}"
            ).format(feet=feet_src, inch=inch_src, indent=indent)
            candidate = source[:s] + insertion + new_stmt + source[e:]
            if candidate != source:
                out.append(candidate)
    except Exception:
        return out
    return out


def _merged_single_print_fix(source):
    """print(n//36 + (n%36)/3) style single merged output -> two rounded values."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in _find_print_calls(tree):
            call = node.value
            if len(call.args) != 1:
                continue
            arg = call.args[0]
            if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)):
                continue
            left, right = arg.left, arg.right
            if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.FloorDiv)
                    and isinstance(left.right, ast.Constant) and left.right.value == 36):
                continue
            if not (isinstance(right, ast.BinOp) and isinstance(right.op, ast.Div)
                    and isinstance(right.right, ast.Constant) and right.right.value == 3):
                continue
            inner = right.left
            if not (isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Mod)
                    and isinstance(inner.right, ast.Constant) and inner.right.value == 36):
                continue
            b1s, b1e = _span(source, left.left)
            b2s, b2e = _span(source, inner.left)
            if source[b1s:b1e] != source[b2s:b2e]:
                continue
            base_src = source[b1s:b1e]
            new_args = "({b}+1)//36, ({b}+1)%36//3".format(b=base_src)
            out.append(_splice(source, arg, new_args))
    except Exception:
        return out
    return out


def _total_inches_misuse(source):
    """x = n//36 ; y = round(n/3)  (y uses whole n, not the remainder)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for i in range(len(body) - 1):
                s1, s2 = body[i], body[i + 1]
                if not (isinstance(s1, ast.Assign) and len(s1.targets) == 1
                        and isinstance(s1.targets[0], ast.Name)):
                    continue
                val1 = s1.value
                if not (isinstance(val1, ast.BinOp) and isinstance(val1.op, ast.FloorDiv)
                        and isinstance(val1.right, ast.Constant) and val1.right.value == 36):
                    continue
                if not (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                        and isinstance(s2.targets[0], ast.Name)):
                    continue
                val2 = s2.value
                if not (isinstance(val2, ast.Call) and isinstance(val2.func, ast.Name)
                        and val2.func.id == "round" and len(val2.args) == 1):
                    continue
                inner = val2.args[0]
                if not (isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Div)
                        and isinstance(inner.right, ast.Constant) and inner.right.value == 3):
                    continue
                b1s, b1e = _span(source, val1.left)
                b2s, b2e = _span(source, inner.left)
                if source[b1s:b1e] != source[b2s:b2e]:
                    continue
                base_src = source[b1s:b1e]
                X = s1.targets[0].id
                Y = s2.targets[0].id
                s_s, _ = _span(source, s1)
                _, e_e = _span(source, s2)
                indent = source[source.rfind("\n", 0, s_s) + 1:s_s]
                new_block = (
                    "{Y} = round({base}/3)\n"
                    "{indent}{X} = {Y} // 12\n"
                    "{indent}{Y} = {Y} % 12"
                ).format(Y=Y, X=X, base=base_src, indent=indent)
                out.append(source[:s_s] + new_block + source[e_e:])
    except Exception:
        return out
    return out


def _float_feet_round_fix(source):
    """feet = int(n/36 + 0.5)  ->  feet = int(n//36)  (feet must floor, not round)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "int" and len(node.args) == 1):
                continue
            arg = node.args[0]
            if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)):
                continue
            left, right = arg.left, arg.right
            if not (isinstance(right, ast.Constant) and isinstance(right.value, float)
                    and abs(right.value - 0.5) < 1e-9):
                continue
            if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Div)
                    and isinstance(left.right, ast.Constant) and left.right.value == 36):
                continue
            bs, be = _span(source, left.left)
            base_src = source[bs:be]
            out.append(_splice(source, arg, "{}//36".format(base_src)))
    except Exception:
        return out
    return out


def _typo_mod26_to_mod36(source):
    """`x % 26` next to `x // 36` is a typo for `x % 36`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        div36_bases = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv)
                    and isinstance(node.right, ast.Constant) and node.right.value == 36):
                s, e = _span(source, node.left)
                div36_bases.add(source[s:e])
        for node in ast.walk(tree):
            if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)
                    and isinstance(node.right, ast.Constant) and node.right.value == 26):
                s, e = _span(source, node.left)
                if source[s:e] in div36_bases:
                    rs, re_ = _span(source, node.right)
                    out.append(source[:rs] + "36" + source[re_:])
    except Exception:
        return out
    return out


def _inline_floor3_round(source):
    """A bare `rem // 3` used directly as the printed inch value (never rounded)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in _find_print_calls(tree):
            call = node.value
            slots = _slots_from_print(source, call)
            if not slots:
                continue
            for slot in slots:
                if (isinstance(slot, ast.BinOp) and isinstance(slot.op, ast.FloorDiv)
                        and isinstance(slot.right, ast.Constant) and slot.right.value == 3):
                    bs, be = _span(source, slot.left)
                    base_src = source[bs:be]
                    out.append(_splice(source, slot, "round({}/3)".format(base_src)))
    except Exception:
        return out
    return out


def _ceil_should_be_round(source):
    """math.ceil(rem/3) always rounds up; should be round(rem/3)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            is_ceil = False
            if isinstance(node.func, ast.Attribute) and node.func.attr == "ceil":
                is_ceil = True
            elif isinstance(node.func, ast.Name) and node.func.id == "ceil":
                is_ceil = True
            if not is_ceil or len(node.args) != 1:
                continue
            arg = node.args[0]
            if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div)
                    and isinstance(arg.right, ast.Constant) and arg.right.value == 3):
                continue
            s, e = _span(source, arg)
            arg_src = source[s:e]
            out.append(_splice(source, node, "round({})".format(arg_src)))
    except Exception:
        return out
    return out


def _func_self_name_misuse(source):
    """A helper fn compares its own name to a constant instead of its parameter."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and len(node.args.args) >= 1):
                continue
            param_name = node.args.args[0].arg
            for sub in ast.walk(node):
                if not (isinstance(sub, ast.Compare) and len(sub.ops) == 1
                        and isinstance(sub.ops[0], ast.Eq)):
                    continue
                if not (isinstance(sub.left, ast.Name) and sub.left.id == node.name
                        and sub.left.id != param_name):
                    continue
                rs, re_ = _span(source, sub.comparators[0])
                right_src = source[rs:re_]
                out.append(_splice(source, sub, "{} <= {}".format(param_name, right_src)))
    except Exception:
        return out
    return out


def _feet_offset_hack(source):
    """x = (x + k) // 12 ; print(x)  loses the inch remainder entirely."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for i, stmt in enumerate(body):
                if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)):
                    continue
                target = stmt.targets[0].id
                val = stmt.value
                if not (isinstance(val, ast.BinOp) and isinstance(val.op, ast.FloorDiv)
                        and isinstance(val.right, ast.Constant) and val.right.value == 12):
                    continue
                left = val.left
                if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add)):
                    continue
                ln, rn = left.left, left.right
                if not (isinstance(ln, ast.Name) and ln.id == target
                        and isinstance(rn, ast.Constant)):
                    continue
                for j in range(i + 1, len(body)):
                    s2 = body[j]
                    if not (isinstance(s2, ast.Expr) and isinstance(s2.value, ast.Call)):
                        continue
                    c = s2.value
                    if not (isinstance(c.func, ast.Name) and c.func.id == "print"
                            and len(c.args) == 1 and isinstance(c.args[0], ast.Name)
                            and c.args[0].id == target):
                        continue
                    s_s, s_e = _span(source, stmt)
                    p_s, p_e = _span(source, s2)
                    indent = source[source.rfind("\n", 0, s_s) + 1:s_s]
                    new_assign = "feet = {t} // 12\n{indent}{t} = {t} % 12".format(t=target, indent=indent)
                    new_print = "print(feet, {t})".format(t=target)
                    cand = source[:s_s] + new_assign + source[s_e:p_s] + new_print + source[p_e:]
                    out.append(cand)
                    break
    except Exception:
        return out
    return out


def _remove_spurious_half_branch(source):
    """if n % 36 >= 18: ... else: <real logic>  -- drop the bogus half-cm shortcut."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if not (isinstance(node, ast.If) and node.orelse):
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.GtE)):
                continue
            left = test.left
            comp = test.comparators[0]
            if not (isinstance(left, ast.BinOp) and isinstance(left.op, ast.Mod)
                    and isinstance(left.right, ast.Constant) and left.right.value == 36):
                continue
            if not (isinstance(comp, ast.Constant) and comp.value == 18):
                continue
            s, e = _span(source, node)
            indent = source[source.rfind("\n", 0, s) + 1:s]
            oe_s, _ = _span(source, node.orelse[0])
            _, oe_e = _span(source, node.orelse[-1])
            orelse_src = source[oe_s:oe_e]
            first_line_start = source.rfind("\n", 0, oe_s) + 1
            orelse_indent = source[first_line_start:oe_s]
            lines = orelse_src.split("\n")
            new_lines = []
            for idx, ln in enumerate(lines):
                if ln.strip() == "":
                    new_lines.append(ln)
                    continue
                if ln.startswith(orelse_indent):
                    stripped = ln[len(orelse_indent):]
                else:
                    stripped = ln.lstrip()
                new_lines.append(indent + stripped)
            new_src = "\n".join(new_lines)
            out.append(source[:s] + new_src + source[e:])
    except Exception:
        return out
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="carry_inch_overflow_to_feet",
                apply=_carry_inch_to_feet,
                symptoms=("wrong",),
            ),
            Rule(
                name="merged_single_print_to_two_values",
                apply=_merged_single_print_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="total_inches_computed_from_whole_n",
                apply=_total_inches_misuse,
                symptoms=("wrong",),
            ),
            Rule(
                name="float_feet_rounded_instead_of_floored",
                apply=_float_feet_round_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="typo_mod26_should_be_mod36",
                apply=_typo_mod26_to_mod36,
                symptoms=("wrong",),
            ),
            Rule(
                name="inline_floor_div3_missing_round",
                apply=_inline_floor3_round,
                symptoms=("wrong",),
            ),
            Rule(
                name="ceil_should_be_round",
                apply=_ceil_should_be_round,
                symptoms=("wrong",),
            ),
            Rule(
                name="helper_function_self_name_misuse",
                apply=_func_self_name_misuse,
                symptoms=("wrong",),
            ),
            Rule(
                name="feet_offset_hack_loses_inches",
                apply=_feet_offset_hack,
                symptoms=("wrong",),
            ),
            Rule(
                name="spurious_half_cm_threshold_branch",
                apply=_remove_spurious_half_branch,
                symptoms=("wrong",),
            ),
        ]