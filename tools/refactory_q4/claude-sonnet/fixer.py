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


def _get_slice(node):
    sl = node.slice
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _indent_of_line(source, pos):
    line_start = source.rfind("\n", 0, pos) + 1
    line = source[line_start:pos]
    return line[: len(line) - len(line.lstrip())]


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _empty_tuple_to_list(source):
    """Fix `x == ()` style empty checks that should test against `[]`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 0:
            out.append(_splice(source, node, "[]"))
    return out


def _base_case_off_by_one(source):
    """Fix `len(x) == 1` base cases that should also cover len 0 (<= 1)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if (
                isinstance(left, ast.Call)
                and isinstance(left.func, ast.Name)
                and left.func.id == "len"
                and isinstance(right, ast.Constant)
                and right.value == 1
            ):
                ls, le = _span(source, left)
                new_cmp = source[ls:le] + " <= 1"
                out.append(_splice(source, node, new_cmp))
    return out


def _min_max_swap(source):
    """Swap min()/max() calls (a common extremum-direction slip)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("min", "max"):
            targets.append(node)
    out = []
    for node in targets:
        other = "max" if node.func.id == "min" else "min"
        fs, fe = _span(source, node.func)
        out.append(source[:fs] + other + source[fe:])
    if len(targets) > 1:
        spans = [(_span(source, n), ("max" if n.func.id == "min" else "min")) for n in targets]
        spans.sort(key=lambda t: t[0][0], reverse=True)
        combined = source
        for (s, e), repl in spans:
            combined = combined[:s] + repl + combined[e:]
        out.append(combined)
    return out


def _extremum_compare_flip(source):
    """Flip </> in comparisons that inspect the age field (index 1)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    flip = {ast.Lt: ">", ast.Gt: "<", ast.LtE: ">=", ast.GtE: "<="}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in flip:
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Subscript) or isinstance(right, ast.Subscript):
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " " + flip[type(node.ops[0])] + " " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


def _pop_no_arg_to_pop0(source):
    """Fix `.pop()` that should pop from the front: `.pop(0)`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    targets = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "pop"
            and len(node.args) == 0
            and len(node.keywords) == 0
        ):
            s, e = _span(source, node)
            if source[s:e].endswith("()"):
                targets.append((s, e))
    out = []
    for s, e in targets:
        out.append(source[:s] + source[s:e][:-1] + "0)" + source[e:])
    if len(targets) > 1:
        combined = source
        for s, e in sorted(targets, key=lambda t: t[0], reverse=True):
            combined = combined[:s] + combined[s:e][:-1] + "0)" + combined[e:]
        out.append(combined)
    return out


def _pop_subscript_to_call(source):
    """Fix `x.pop[i]` (subscript typo) into a proper call `x.pop(i)`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "pop":
            vs, ve = _span(source, node.value)
            sl = _get_slice(node)
            ss, se = _span(source, sl)
            new_text = source[vs:ve] + "(" + source[ss:se] + ")"
            out.append(_splice(source, node, new_text))
    return out


def _append_reverse_to_return(source):
    """Fix wrong final order by reversing the returned sequence."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            val = node.value
            s, e = _span(source, val)
            text = source[s:e]
            if text.endswith("[::-1]"):
                continue
            new_val = "(" + text + ")[::-1]"
            out.append(_splice(source, val, new_val))
    return out


BUILTIN_NAMES = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))


def _undefined_name_fix(source):
    """Fix a typo'd variable name that should refer to the sole parameter."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = [a.arg for a in fn.args.args]
        if len(params) != 1:
            continue
        param = params[0]
        assigned = set(params)
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    for nm in ast.walk(t):
                        if isinstance(nm, ast.Name):
                            assigned.add(nm.id)
            if isinstance(node, ast.For):
                for nm in ast.walk(node.target):
                    if isinstance(nm, ast.Name):
                        assigned.add(nm.id)
            if isinstance(node, (ast.FunctionDef,)):
                assigned.add(node.name)
        undefined_nodes = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in assigned and node.id not in BUILTIN_NAMES:
                    undefined_nodes.append(node)
        distinct_ids = {n.id for n in undefined_nodes}
        if len(distinct_ids) == 1 and undefined_nodes:
            spans = [(_span(source, n)) for n in undefined_nodes]
            spans.sort(key=lambda t: t[0], reverse=True)
            combined = source
            for s, e in spans:
                combined = combined[:s] + param + combined[e:]
            out.append(combined)
    return out


MUTATING_METHODS = {"remove", "append", "extend", "insert", "sort", "clear"}


def _none_call_arg_split(source):
    """Fix a None-returning mutation (e.g. list.remove) used as an argument."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Return) and node.value is not None):
            continue
        for inner in ast.walk(node.value):
            if not isinstance(inner, ast.Call):
                continue
            for arg in inner.args:
                if (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Attribute)
                    and arg.func.attr in MUTATING_METHODS
                ):
                    obj_node = arg.func.value
                    obj_s, obj_e = _span(source, obj_node)
                    obj_text = source[obj_s:obj_e]
                    call_s, call_e = _span(source, arg)
                    call_text = source[call_s:call_e]
                    ret_s, _ = _span(source, node)
                    indent = _indent_of_line(source, ret_s)
                    stmt = call_text + "\n" + indent
                    new_source = source[:ret_s] + stmt + source[ret_s:]
                    shift = len(stmt)
                    new_arg_s = call_s + shift
                    new_arg_e = call_e + shift
                    new_source2 = new_source[:new_arg_s] + obj_text + new_source[new_arg_e:]
                    out.append(new_source2)
    return out


def _empty_guard_insert(source):
    """Insert a missing empty-list guard before code that indexes lst[0]."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args or not fn.body:
            continue
        param = fn.args.args[0].arg
        first = fn.body[0]
        if isinstance(first, ast.If):
            continue
        found = False
        for node in ast.walk(first):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == param:
                sl = _get_slice(node)
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    found = True
                    break
        if found:
            fs, _ = _span(source, first)
            indent = _indent_of_line(source, fs)
            guard = "if {p} == []:\n{ind}    return []\n{ind}".format(p=param, ind=indent)
            out.append(source[:fs] + guard + source[fs:])
    return out


def _missing_container_removal(source):
    """Insert a missing `.remove(...)` on the loop-control container list."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.While) and isinstance(node.test, ast.Name)):
            continue
        cont_var = node.test.id
        has_remove = False
        max_var = None
        append_call = None
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "remove"
                and isinstance(inner.func.value, ast.Name)
                and inner.func.value.id == cont_var
            ):
                has_remove = True
            if (
                isinstance(inner, ast.Assign)
                and isinstance(inner.value, ast.Call)
                and isinstance(inner.value.func, ast.Name)
                and inner.value.func.id in ("max", "min")
                and len(inner.value.args) == 1
                and isinstance(inner.value.args[0], ast.Name)
                and inner.value.args[0].id == cont_var
                and len(inner.targets) == 1
                and isinstance(inner.targets[0], ast.Name)
            ):
                max_var = inner.targets[0].id
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "append"
            ):
                append_call = inner
        if not has_remove and max_var and append_call is not None:
            s, e = _span(source, append_call)
            line_end = source.find("\n", e)
            if line_end == -1:
                line_end = len(source)
            indent = _indent_of_line(source, s)
            stmt = "\n{ind}{cv}.remove({mv})".format(ind=indent, cv=cont_var, mv=max_var)
            out.append(source[:line_end] + stmt + source[line_end:])
    return out


def _reset_index_after_mutation(source):
    """Insert a missing index reset after an in-place mutation inside a loop."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and node.orelse):
            continue
        del_var = None
        for stmt in node.body:
            if isinstance(stmt, ast.Delete):
                for target in stmt.targets:
                    if isinstance(target, ast.Subscript):
                        sl = _get_slice(target)
                        if isinstance(sl, ast.Name):
                            del_var = sl.id
        if not del_var:
            continue
        already = any(
            isinstance(s, ast.Assign)
            and len(s.targets) == 1
            and isinstance(s.targets[0], ast.Name)
            and s.targets[0].id == del_var
            and isinstance(s.value, ast.Constant)
            and s.value.value == 0
            for s in node.body
        )
        if already:
            continue
        last = node.body[-1]
        ls, le = _span(source, last)
        indent = _indent_of_line(source, ls)
        stmt = "\n{ind}{v} = 0".format(ind=indent, v=del_var)
        out.append(source[:le] + stmt + source[le:])
    return out


def _wrap_rule(fn):
    def wrapped(source):
        try:
            result = fn(source)
        except Exception:
            return []
        seen = set()
        out = []
        for r in result:
            if r != source and r not in seen:
                seen.add(r)
                out.append(r)
        return out
    return wrapped


class Fixer:
    def rules(self):
        return [
            Rule(
                name="empty_tuple_to_list",
                apply=_wrap_rule(_empty_tuple_to_list),
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="base_case_off_by_one",
                apply=_wrap_rule(_base_case_off_by_one),
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="min_max_swap",
                apply=_wrap_rule(_min_max_swap),
                symptoms=("wrong",),
            ),
            Rule(
                name="extremum_compare_flip",
                apply=_wrap_rule(_extremum_compare_flip),
                symptoms=("wrong",),
            ),
            Rule(
                name="pop_no_arg_to_pop0",
                apply=_wrap_rule(_pop_no_arg_to_pop0),
                symptoms=("wrong",),
            ),
            Rule(
                name="pop_subscript_to_call",
                apply=_wrap_rule(_pop_subscript_to_call),
                symptoms=("err:TypeError",),
            ),
            Rule(
                name="append_reverse_to_return",
                apply=_wrap_rule(_append_reverse_to_return),
                symptoms=("wrong",),
            ),
            Rule(
                name="undefined_name_fix",
                apply=_wrap_rule(_undefined_name_fix),
                symptoms=("err:NameError",),
            ),
            Rule(
                name="none_call_arg_split",
                apply=_wrap_rule(_none_call_arg_split),
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="empty_guard_insert",
                apply=_wrap_rule(_empty_guard_insert),
                symptoms=("err:IndexError",),
            ),
            Rule(
                name="missing_container_removal",
                apply=_wrap_rule(_missing_container_removal),
                symptoms=("timeout", "wrong"),
            ),
            Rule(
                name="reset_index_after_mutation",
                apply=_wrap_rule(_reset_index_after_mutation),
                symptoms=("wrong",),
            ),
        ]