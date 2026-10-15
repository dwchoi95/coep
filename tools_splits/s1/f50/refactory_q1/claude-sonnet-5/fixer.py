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


def _first_func(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef):
            return n
    return None


def _second_param(tree):
    fn = _first_func(tree)
    if fn is None or len(fn.args.args) < 2:
        return None
    return fn.args.args[1].arg


_OP_SYM = {
    ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
    ast.Eq: "==", ast.NotEq: "!=",
}


def _swap_op_candidates(source, mapping):
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                for old_t, new_cls in mapping:
                    if isinstance(op, old_t):
                        left = node.left
                        right = node.comparators[0]
                        ls, le = _span(source, left)
                        rs, re_ = _span(source, right)
                        sym = _OP_SYM[new_cls]
                        new_cmp = source[ls:le] + " " + sym + " " + source[rs:re_]
                        s, e = _span(source, node)
                        out.append(source[:s] + new_cmp + source[e:])
    except Exception:
        return []
    return out


def relax_strict_comparison(source):
    """x < e  ->  x <= e   (and  x > e -> x >= e)."""
    return _swap_op_candidates(source, [(ast.Lt, ast.LtE), (ast.Gt, ast.GtE)])


def tighten_comparison(source):
    """x <= e -> x < e   (and x >= e -> x > e)."""
    return _swap_op_candidates(source, [(ast.LtE, ast.Lt), (ast.GtE, ast.Gt)])


def flip_comparison_direction(source):
    """Swap < with > (and <= with >=) - reversed comparison misconception."""
    return _swap_op_candidates(
        source,
        [(ast.Lt, ast.Gt), (ast.Gt, ast.Lt), (ast.LtE, ast.GtE), (ast.GtE, ast.LtE)],
    )


def eq_to_lte(source):
    """x == e  ->  x <= e (equality used instead of a threshold test)."""
    return _swap_op_candidates(source, [(ast.Eq, ast.LtE)])


def fix_is_to_eq(source):
    """`seq is ()` style identity checks against literals -> ==."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Is):
                comp = node.comparators[0]
                if isinstance(comp, (ast.Tuple, ast.List)):
                    left = node.left
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, comp)
                    new_cmp = source[ls:le] + " == " + source[rs:re_]
                    s, e = _span(source, node)
                    out.append(source[:s] + new_cmp + source[e:])
    except Exception:
        return []
    return out


def fix_or_missing_comparison(source):
    """`seq == [] or ()` -> `seq == [] or seq == ()` (operator-precedence slip)."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                cmp_left_text = None
                for v in node.values:
                    if isinstance(v, ast.Compare) and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq):
                        ls, le = _span(source, v.left)
                        cmp_left_text = source[ls:le]
                        break
                if cmp_left_text is None:
                    continue
                for v in node.values:
                    if isinstance(v, (ast.Tuple, ast.List)):
                        vs, ve = _span(source, v)
                        lit_text = source[vs:ve]
                        out.append(source[:vs] + f"{cmp_left_text} == {lit_text}" + source[ve:])
    except Exception:
        return []
    return out


def _is_emptiness_test(test, seqname):
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        operand = test.operand
        return isinstance(operand, ast.Name) and operand.id == seqname
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        op = test.ops[0]
        left = test.left
        comp = test.comparators[0]
        if isinstance(op, (ast.Eq, ast.Is)):
            if isinstance(left, ast.Name) and left.id == seqname:
                if isinstance(comp, (ast.Tuple, ast.List)) and len(comp.elts) == 0:
                    return True
                if isinstance(comp, ast.Call) and isinstance(comp.func, ast.Name) \
                        and comp.func.id in ("tuple", "list") and not comp.args:
                    return True
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                if left.args and isinstance(left.args[0], ast.Name) and left.args[0].id == seqname:
                    if isinstance(comp, ast.Constant) and comp.value == 0:
                        return True
    return False


def fix_empty_guard(source):
    """Normalise an empty-sequence guard whose body returns the wrong value."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    seqname = _second_param(tree)
    if seqname is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and _is_emptiness_test(node.test, seqname) and len(node.body) == 1:
                stmt = node.body[0]
                if isinstance(stmt, ast.Return):
                    if stmt.value is None:
                        s, e = _span(source, stmt)
                        out.append(source[:s] + "return 0" + source[e:])
                    else:
                        is_zero = isinstance(stmt.value, ast.Constant) and stmt.value.value == 0
                        if not is_zero:
                            s, e = _span(source, stmt.value)
                            out.append(source[:s] + "0" + source[e:])
                elif isinstance(stmt, ast.Pass):
                    s, e = _span(source, stmt)
                    out.append(source[:s] + "return 0" + source[e:])
                elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    varname = stmt.targets[0].id
                    has_later_return = any(
                        isinstance(n2, ast.Return) and isinstance(n2.value, ast.Name) and n2.value.id == varname
                        for n2 in ast.walk(tree) if n2 is not stmt
                    )
                    if has_later_return:
                        vs, ve = _span(source, stmt.value)
                        value_text = source[vs:ve]
                        s, e = _span(source, stmt)
                        out.append(source[:s] + f"return {value_text}" + source[e:])
    except Exception:
        return []
    return out


def insert_empty_guard(source):
    """Add a missing `if not seq: return 0` before code that indexes seq[0]/seq[-1]."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    fn = _first_func(tree)
    if fn is None or len(fn.args.args) < 2:
        return []
    seqname = fn.args.args[1].arg
    body = fn.body
    idx = 0
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        idx = 1
    if idx >= len(body):
        return []
    first = body[idx]
    if not isinstance(first, ast.If):
        return []
    try:
        uses_subscript = any(
            isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == seqname
            for n in ast.walk(first.test)
        )
    except Exception:
        return []
    if not uses_subscript:
        return []
    if _is_emptiness_test(first.test, seqname):
        return []
    indent = " " * first.col_offset
    insertion = f"if not {seqname}:\n{indent}    return 0\n{indent}"
    s, e = _span(source, first)
    return [source[:s] + insertion + source[s:]]


def add_missing_final_return_len(source):
    """Append a `return len(seq)` fallback after a trailing loop that can fall through."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    seqname = _second_param(tree)
    if seqname is None:
        return []
    out = []
    seen = set()
    try:
        for node in ast.walk(tree):
            for field in ("body", "orelse", "finalbody"):
                stmts = getattr(node, field, None)
                if not isinstance(stmts, list) or not stmts:
                    continue
                if not all(isinstance(s, ast.stmt) for s in stmts):
                    continue
                idx = len(stmts) - 1
                while idx >= 0 and isinstance(stmts[idx], ast.Expr) \
                        and isinstance(getattr(stmts[idx], "value", None), ast.Constant) \
                        and isinstance(stmts[idx].value.value, str):
                    idx -= 1
                if idx < 0:
                    continue
                target = stmts[idx]
                if isinstance(target, (ast.For, ast.While)) and not target.orelse:
                    key = (target.lineno, target.col_offset, id(stmts))
                    if key in seen:
                        continue
                    seen.add(key)
                    s, e = _span(source, target)
                    indent = " " * target.col_offset
                    insertion = f"\n{indent}return len({seqname})"
                    out.append(source[:e] + insertion + source[e:])
    except Exception:
        return []
    return out


def break_to_return_fallback(source):
    """for i in range(N): if cond: break / return i  ->  return i inline / return N."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            stmts = getattr(node, "body", None)
            if not isinstance(stmts, list):
                continue
            for i, st in enumerate(stmts):
                if not isinstance(st, ast.For):
                    continue
                if not (isinstance(st.iter, ast.Call) and isinstance(st.iter.func, ast.Name)
                        and st.iter.func.id == "range" and len(st.iter.args) == 1):
                    continue
                if not isinstance(st.target, ast.Name):
                    continue
                loopvar = st.target.id
                if len(st.body) != 1 or not isinstance(st.body[0], ast.If):
                    continue
                ifnode = st.body[0]
                if ifnode.orelse or len(ifnode.body) != 1 or not isinstance(ifnode.body[0], ast.Break):
                    continue
                if i + 1 >= len(stmts):
                    continue
                nxt = stmts[i + 1]
                if not (isinstance(nxt, ast.Return) and isinstance(nxt.value, ast.Name)
                        and nxt.value.id == loopvar):
                    continue
                bound_s, bound_e = _span(source, st.iter.args[0])
                bound_text = source[bound_s:bound_e]
                brk = ifnode.body[0]
                bs, be = _span(source, brk)
                replacement = f"return {loopvar}"
                new_src = source[:bs] + replacement + source[be:]
                diff = len(replacement) - (be - bs)
                ns, ne = _span(source, nxt)
                ns += diff
                ne += diff
                new_src = new_src[:ns] + f"return {bound_text}" + new_src[ne:]
                out.append(new_src)
    except Exception:
        return []
    return out


def adjust_offset_in_return(source):
    """return i+1 / return count-1  ->  return i / return len(seq)."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    seqname = _second_param(tree)
    if seqname is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) \
                    and isinstance(node.value.op, (ast.Add, ast.Sub)):
                left = node.value.left
                right = node.value.right
                if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and right.value == 1:
                    ls, le = _span(source, left)
                    left_text = source[ls:le]
                    vs, ve = _span(source, node.value)
                    out.append(source[:vs] + left_text + source[ve:])
                    out.append(source[:vs] + f"len({seqname})" + source[ve:])
    except Exception:
        return []
    return out


def fix_range_missing_len(source):
    """range(seq) -> range(len(seq));  for i in len(seq) -> for i in range(len(seq))."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    seqname = _second_param(tree)
    if seqname is None:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                it = node.iter
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range" \
                        and len(it.args) == 1:
                    arg = it.args[0]
                    if isinstance(arg, ast.Name) and arg.id == seqname:
                        s, e = _span(source, arg)
                        out.append(source[:s] + f"len({seqname})" + source[e:])
                elif isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "len":
                    if it.args and isinstance(it.args[0], ast.Name) and it.args[0].id == seqname:
                        s, e = _span(source, it)
                        text = source[s:e]
                        out.append(source[:s] + f"range({text})" + source[e:])
    except Exception:
        return []
    return out


def fix_range_bound_offset(source):
    """range(l+1) -> range(l);  range(len(seq)-1) -> range(len(seq))."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" \
                    and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Sub)) \
                        and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                    ls, le = _span(source, arg.left)
                    left_text = source[ls:le]
                    s, e = _span(source, arg)
                    out.append(source[:s] + left_text + source[e:])
    except Exception:
        return []
    return out


def fix_undefined_iterable_name(source):
    """Use of an undefined name (typo) as the sequence being iterated/enumerated."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    fn = _first_func(tree)
    if fn is None or len(fn.args.args) < 2:
        return []
    seqname = fn.args.args[1].arg
    defined = {a.arg for a in fn.args.args}
    try:
        for n in ast.walk(fn):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                defined.add(n.id)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(fn):
            target_name_node = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "enumerate" \
                    and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Name) and arg0.id not in defined:
                    target_name_node = arg0
            elif isinstance(node, ast.For):
                it = node.iter
                if isinstance(it, ast.Name) and it.id not in defined:
                    target_name_node = it
            if target_name_node is not None and target_name_node.id != seqname:
                s, e = _span(source, target_name_node)
                out.append(source[:s] + seqname + source[e:])
    except Exception:
        return []
    return out


def fix_function_name(source):
    """Rename a misnamed top-level function (e.g. search2) back to `search`."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name != "search":
                s, _ = _span(source, node)
                idx = source.index("def ", s)
                name_start = idx + len("def ")
                name_end = name_start + len(node.name)
                if source[name_start:name_end] == node.name:
                    out.append(source[:name_start] + "search" + source[name_end:])
    except Exception:
        return []
    return out


def fix_eq_as_assign(source):
    """`count==0` used as a statement (typo for `count=0`)."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare) \
                    and len(node.value.ops) == 1 and isinstance(node.value.ops[0], ast.Eq):
                left = node.value.left
                right = node.value.comparators[0]
                if isinstance(left, ast.Name):
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    new_stmt = source[ls:le] + " = " + source[rs:re_]
                    s, e = _span(source, node)
                    out.append(source[:s] + new_stmt + source[e:])
    except Exception:
        return []
    return out


def fix_self_increment(source):
    """`position += position` typo for `position += 1`."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) \
                    and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name) \
                    and node.target.id == node.value.id:
                s, e = _span(source, node.value)
                out.append(source[:s] + "1" + source[e:])
    except Exception:
        return []
    return out


def fix_assign_then_bare_return_to_break(source):
    """`result = i; return` inside a loop's if -> `result = i; break`."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                body = node.body
                if len(body) == 2 and isinstance(body[0], ast.Assign) \
                        and isinstance(body[1], ast.Return) and body[1].value is None:
                    s, e = _span(source, body[1])
                    out.append(source[:s] + "break" + source[e:])
    except Exception:
        return []
    return out


def fix_elem_window_compare(source):
    """`elem <= x <= elem + 1` (or <)  ->  `x <= elem`."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    fn = _first_func(tree)
    if fn is None or not fn.args.args:
        return []
    xname = fn.args.args[0].arg
    out = []
    try:
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 2:
                op1, op2 = node.ops
                if isinstance(op1, (ast.Lt, ast.LtE)) and isinstance(op2, (ast.Lt, ast.LtE)):
                    mid = node.comparators[0]
                    right = node.comparators[1]
                    left = node.left
                    if isinstance(mid, ast.Name) and mid.id == xname:
                        if isinstance(right, ast.BinOp) and isinstance(right.op, ast.Add) \
                                and isinstance(right.right, ast.Constant) and right.right.value == 1:
                            rl_s, rl_e = _span(source, right.left)
                            left_s, left_e = _span(source, left)
                            if source[rl_s:rl_e] == source[left_s:left_e]:
                                s, e = _span(source, node)
                                elem_text = source[left_s:left_e]
                                out.append(source[:s] + f"{xname} <= {elem_text}" + source[e:])
    except Exception:
        return []
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="relax_strict_comparison", apply=relax_strict_comparison,
                 symptoms=("wrong",)),
            Rule(name="tighten_comparison", apply=tighten_comparison,
                 symptoms=("wrong",)),
            Rule(name="flip_comparison_direction", apply=flip_comparison_direction,
                 symptoms=("wrong",)),
            Rule(name="eq_to_lte", apply=eq_to_lte,
                 symptoms=("wrong",)),
            Rule(name="fix_is_to_eq", apply=fix_is_to_eq,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_or_missing_comparison", apply=fix_or_missing_comparison,
                 symptoms=("wrong",)),
            Rule(name="fix_empty_guard", apply=fix_empty_guard,
                 symptoms=("wrong", "err:IndexError", "err:TypeError")),
            Rule(name="insert_empty_guard", apply=insert_empty_guard,
                 symptoms=("err:IndexError",)),
            Rule(name="add_missing_final_return_len", apply=add_missing_final_return_len,
                 symptoms=("wrong",)),
            Rule(name="break_to_return_fallback", apply=break_to_return_fallback,
                 symptoms=("wrong", "err:UnboundLocalError")),
            Rule(name="adjust_offset_in_return", apply=adjust_offset_in_return,
                 symptoms=("wrong",)),
            Rule(name="fix_range_missing_len", apply=fix_range_missing_len,
                 symptoms=("err:TypeError",)),
            Rule(name="fix_range_bound_offset", apply=fix_range_bound_offset,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="fix_undefined_iterable_name", apply=fix_undefined_iterable_name,
                 symptoms=("err:NameError",)),
            Rule(name="fix_function_name", apply=fix_function_name,
                 symptoms=("err:NameError",)),
            Rule(name="fix_eq_as_assign", apply=fix_eq_as_assign,
                 symptoms=("err:NameError", "err:UnboundLocalError")),
            Rule(name="fix_self_increment", apply=fix_self_increment,
                 symptoms=("timeout", "wrong")),
            Rule(name="fix_assign_then_bare_return_to_break", apply=fix_assign_then_bare_return_to_break,
                 symptoms=("wrong",)),
            Rule(name="fix_elem_window_compare", apply=fix_elem_window_compare,
                 symptoms=("wrong",)),
        ]