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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _multi_splice(source, edits):
    """Apply several (node, new_text) edits to source, rightmost span first."""
    edits = [e for e in edits if e is not None]
    edits_sorted = sorted(edits, key=lambda e: _span(source, e[0])[0], reverse=True)
    out = source
    for node, text in edits_sorted:
        out = _splice(out, node, text)
    return out


def _iter_bodies(tree):
    seen = []
    for node in ast.walk(tree):
        for attr in ("body", "orelse", "finalbody"):
            lst = getattr(node, attr, None)
            if isinstance(lst, list) and lst and all(isinstance(s, ast.stmt) for s in lst):
                if lst not in seen:
                    seen.append(lst)
                    yield lst


def _fix_ceil_constant_before_div3(source):
    """(expr + K)//3 with wrong K (should be +1) used as a rounding trick."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv)
                and isinstance(node.right, ast.Constant) and node.right.value == 3
                and isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add)
                and isinstance(node.left.right, ast.Constant)
                and isinstance(node.left.right.value, int)
                and node.left.right.value != 1):
            inner = node.left.left
            inner_text = _text(source, inner)
            new_text = f"({inner_text}+1)//3"
            candidate = _splice(source, node, new_text)
            if candidate != source:
                out.append(candidate)
    return out


def _fix_missing_int_cast_in_str(source):
    """str(x // 12) / str(x % 12) where x was produced by true division."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    float_vars = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div) \
                and isinstance(node.target, ast.Name):
            float_vars.add(node.target.id)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) \
                and isinstance(node.value.op, ast.Div):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    float_vars.add(t.id)
    if not float_vars:
        return []
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == 'str' and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.FloorDiv, ast.Mod)):
                names = {n.id for n in ast.walk(arg) if isinstance(n, ast.Name)}
                if names & float_vars:
                    arg_text = _text(source, arg)
                    edits.append((arg, f"int({arg_text})"))
    if not edits:
        return []
    candidate = _multi_splice(source, edits)
    return [candidate] if candidate != source else []


def _fix_feet_div36_mod_round(source):
    """feet = n//36 ; rem = n%K (possibly wrong K) ; inches = rem//3 (no rounding)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for body in _iter_bodies(tree):
        n = len(body)
        for i in range(n):
            s1 = body[i]
            if not (isinstance(s1, ast.Assign) and len(s1.targets) == 1
                    and isinstance(s1.targets[0], ast.Name)):
                continue
            v1 = s1.value
            if not (isinstance(v1, ast.BinOp) and isinstance(v1.op, ast.FloorDiv)
                    and isinstance(v1.right, ast.Constant) and v1.right.value == 36):
                continue
            feet_name = s1.targets[0].id
            dividend_expr = v1.left
            dividend_text = _text(source, dividend_expr).strip()
            for j in range(i + 1, n):
                s2 = body[j]
                rem_name = None
                s2_edit = None
                if (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                        and isinstance(s2.targets[0], ast.Name)
                        and isinstance(s2.value, ast.BinOp)
                        and isinstance(s2.value.op, ast.Mod)
                        and isinstance(s2.value.right, ast.Constant)):
                    left2 = s2.value.left
                    left2_text = _text(source, left2).strip()
                    same = False
                    if isinstance(dividend_expr, ast.Name) and isinstance(left2, ast.Name) \
                            and left2.id == dividend_expr.id:
                        same = True
                    elif left2_text == dividend_text:
                        same = True
                    if same:
                        rem_name = s2.targets[0].id
                        s2_edit = (s2.value, f"{dividend_text}-36*{feet_name}")
                elif (isinstance(s2, ast.AugAssign) and isinstance(s2.op, ast.Mod)
                        and isinstance(s2.target, ast.Name)
                        and isinstance(dividend_expr, ast.Name)
                        and s2.target.id == dividend_expr.id):
                    rem_name = s2.target.id
                    s2_edit = (s2, f"{dividend_text} -= 36*{feet_name}")

                if rem_name is None:
                    continue

                usage_node = None
                for k in range(j + 1, n):
                    st = body[k]
                    if (isinstance(st, ast.Assign) and isinstance(st.value, ast.BinOp)
                            and isinstance(st.value.op, ast.FloorDiv)
                            and isinstance(st.value.right, ast.Constant)
                            and st.value.right.value == 3
                            and isinstance(st.value.left, ast.Name)
                            and st.value.left.id == rem_name):
                        usage_node = st.value
                        break
                    if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                            and isinstance(st.value.func, ast.Name)
                            and st.value.func.id == 'print'):
                        found = False
                        for arg in st.value.args:
                            if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.FloorDiv)
                                    and isinstance(arg.right, ast.Constant)
                                    and arg.right.value == 3
                                    and isinstance(arg.left, ast.Name)
                                    and arg.left.id == rem_name):
                                usage_node = arg
                                found = True
                                break
                        if found:
                            break

                edits = [(v1, f"({dividend_text}+1)//36"), s2_edit]
                if usage_node is not None:
                    edits.append((usage_node, f"({rem_name}+1)//3"))
                candidate = _multi_splice(source, edits)
                if candidate != source:
                    out.append(candidate)
    return out


def _fix_math_ceil_div3(source):
    """math.ceil(x/3) (or bare ceil(x/3)) over-rounds; should be (x+1)//3."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_ceil = (isinstance(func, ast.Attribute) and func.attr == 'ceil') or \
                  (isinstance(func, ast.Name) and func.id == 'ceil')
        if not is_ceil or len(node.args) != 1:
            continue
        arg = node.args[0]
        if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div)
                and isinstance(arg.right, ast.Constant) and arg.right.value == 3):
            left_text = _text(source, arg.left)
            new_text = f"(({left_text})+1)//3"
            candidate = _splice(source, node, new_text)
            if candidate != source:
                out.append(candidate)
    return out


def _fix_independent_feet_round(source):
    """feet = n//36 computed independently of a separately rounded total-inches var."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for body in _iter_bodies(tree):
        n = len(body)
        for i in range(n):
            s1 = body[i]
            if not (isinstance(s1, ast.Assign) and len(s1.targets) == 1
                    and isinstance(s1.targets[0], ast.Name)):
                continue
            v1 = s1.value
            if not (isinstance(v1, ast.BinOp) and isinstance(v1.op, ast.FloorDiv)
                    and isinstance(v1.right, ast.Constant) and v1.right.value == 36):
                continue
            feet_name = s1.targets[0].id
            dividend_text = _text(source, v1.left).strip()
            for j in range(i + 1, n):
                s2 = body[j]
                if not (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                        and isinstance(s2.targets[0], ast.Name)):
                    continue
                v2 = s2.value
                if not (isinstance(v2, ast.Call) and isinstance(v2.func, ast.Name)
                        and v2.func.id == 'round' and len(v2.args) == 1):
                    continue
                arg = v2.args[0]
                if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div)
                        and isinstance(arg.right, ast.Constant) and arg.right.value == 3):
                    continue
                if _text(source, arg.left).strip() != dividend_text:
                    continue

                total_text = _text(source, v2)
                inches_name = s2.targets[0].id
                for k in range(j + 1, n):
                    st = body[k]
                    if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                            and isinstance(st.value.func, ast.Name)
                            and st.value.func.id == 'print'
                            and len(st.value.args) == 2
                            and isinstance(st.value.args[0], ast.Name)
                            and isinstance(st.value.args[1], ast.Name)
                            and st.value.args[0].id == feet_name
                            and st.value.args[1].id == inches_name):
                        edits = [
                            (v1, total_text),
                            (st.value.args[0], f"{feet_name}//12"),
                            (st.value.args[1], f"{feet_name}%12"),
                        ]
                        candidate = _multi_splice(source, edits)
                        if candidate != source:
                            out.append(candidate)
                        break
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="ceil_div3_wrong_constant",
                apply=_fix_ceil_constant_before_div3,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_int_cast_after_float_division",
                apply=_fix_missing_int_cast_in_str,
                symptoms=("wrong", "err:ValueError"),
            ),
            Rule(
                name="feet_div36_then_mod_missing_round",
                apply=_fix_feet_div36_mod_round,
                symptoms=("wrong",),
            ),
            Rule(
                name="math_ceil_overrounds_div3",
                apply=_fix_math_ceil_div3,
                symptoms=("wrong",),
            ),
            Rule(
                name="independent_feet_and_rounded_total_inches",
                apply=_fix_independent_feet_round,
                symptoms=("wrong",),
            ),
        ]