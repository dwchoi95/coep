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


def _find_funcdef(tree, name="top_k"):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _flip_strict_compare(source):
    """Flip a strict/non-strict comparison operator (off-by-one loop bounds)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    flip = {ast.Lt: "<=", ast.LtE: "<", ast.Gt: ">=", ast.GtE: ">"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if type(op) in flip:
                left = node.left
                right = node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " " + flip[type(op)] + " " + source[rs:re_]
                candidate = _splice(source, node, new_cmp)
                if candidate != source:
                    out.append(candidate)
    return out


def _counter_init_fix(source):
    """counter = 0 with a `while counter <= k` loop should start at 1."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for wnode in ast.walk(tree):
        if isinstance(wnode, ast.While):
            test = wnode.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 \
               and isinstance(test.ops[0], ast.LtE) and isinstance(test.left, ast.Name):
                cname = test.left.id
                for anode in ast.walk(tree):
                    if isinstance(anode, ast.Assign) and len(anode.targets) == 1 \
                       and isinstance(anode.targets[0], ast.Name) \
                       and anode.targets[0].id == cname \
                       and isinstance(anode.value, ast.Constant) \
                       and anode.value.value == 0:
                        s, e = _span(source, anode.value)
                        candidate = source[:s] + "1" + source[e:]
                        if candidate != source:
                            out.append(candidate)
    return out


def _hardcoded_slice_to_k(source):
    """Return xs[:5] (hardcoded bound) should slice by the parameter k."""
    tree = _parse(source)
    if tree is None:
        return []
    fdef = _find_funcdef(tree)
    if fdef is None or len(fdef.args.args) < 2:
        return []
    kname = fdef.args.args[1].arg
    out = []
    for node in ast.walk(fdef):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            upper = node.slice.upper
            if isinstance(upper, ast.Constant) and isinstance(upper.value, int) \
               and not isinstance(upper.value, bool):
                s, e = _span(source, upper)
                candidate = source[:s] + kname + source[e:]
                if candidate != source:
                    out.append(candidate)
    return out


def _return_var_fix(source):
    """return lst[:k] should return the accumulator variable, not the drained input list."""
    tree = _parse(source)
    if tree is None:
        return []
    fdef = _find_funcdef(tree)
    if fdef is None or not fdef.args.args:
        return []
    listname = fdef.args.args[0].arg
    acc_name = None
    for node in ast.walk(fdef):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name) \
           and isinstance(node.value, ast.List) and len(node.value.elts) == 0:
            name = node.targets[0].id
            if name == listname:
                continue
            for sub in ast.walk(fdef):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                   and sub.func.attr == "append" and isinstance(sub.func.value, ast.Name) \
                   and sub.func.value.id == name:
                    acc_name = name
                    break
        if acc_name:
            break
    if not acc_name:
        return []
    out = []
    for node in ast.walk(fdef):
        if isinstance(node, ast.Return) and node.value is not None:
            val = node.value
            if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) \
               and val.value.id == listname:
                s, e = _span(source, val.value)
                candidate = source[:s] + acc_name + source[e:]
                if candidate != source:
                    out.append(candidate)
    return out


def _extend_index_fix(source):
    """lst.extend([i]) should be lst.extend([lst[i]]) - pushing the index instead of the value."""
    tree = _parse(source)
    if tree is None:
        return []
    fdef = _find_funcdef(tree)
    if fdef is None or not fdef.args.args:
        return []
    listname = fdef.args.args[0].arg
    out = []
    for node in ast.walk(fdef):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "extend" and isinstance(node.func.value, ast.Name) \
           and node.func.value.id == listname:
            if len(node.args) == 1 and isinstance(node.args[0], ast.List) \
               and len(node.args[0].elts) == 1 and isinstance(node.args[0].elts[0], ast.Name):
                elt = node.args[0].elts[0]
                s, e = _span(source, elt)
                new_text = "{}[{}]".format(listname, elt.id)
                candidate = source[:s] + new_text + source[e:]
                if candidate != source:
                    out.append(candidate)
    return out


def _k_zero_check(source):
    """`if lst == []:` should also short-circuit when k == 0."""
    tree = _parse(source)
    if tree is None:
        return []
    fdef = _find_funcdef(tree)
    if fdef is None or len(fdef.args.args) < 2:
        return []
    kname = fdef.args.args[1].arg
    out = []
    for node in ast.walk(fdef):
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 \
               and isinstance(test.ops[0], ast.Eq) \
               and isinstance(test.comparators[0], ast.List) \
               and len(test.comparators[0].elts) == 0:
                s, e = _span(source, test)
                new_test = source[s:e] + " or {} == 0".format(kname)
                candidate = _splice(source, test, new_test)
                if candidate != source:
                    out.append(candidate)
    return out


def _counter_break_fix(source):
    """A for-loop that finds the max and increments a counter inside the `if`
    needs a `break` there instead, with the counter increment moved to run
    exactly once per while-iteration (outside the for-loop)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for wnode in ast.walk(tree):
        if not isinstance(wnode, ast.While):
            continue
        for stmt in wnode.body:
            if not isinstance(stmt, ast.For):
                continue
            for_node = stmt
            if any(isinstance(n, ast.Break) for n in ast.walk(for_node)):
                continue
            for sub in for_node.body:
                if not isinstance(sub, ast.If) or not sub.body:
                    continue
                last = sub.body[-1]
                if isinstance(last, ast.AugAssign) and isinstance(last.op, ast.Add):
                    try:
                        aug_s, aug_e = _span(source, last)
                        for_s, for_e = _span(source, for_node)
                        aug_text = source[aug_s:aug_e]
                        new_source = source[:aug_s] + "break" + source[aug_e:]
                        delta = len("break") - (aug_e - aug_s)
                        new_for_e = for_e + delta
                        indent = " " * for_node.col_offset
                        insertion = "\n" + indent + aug_text
                        candidate = new_source[:new_for_e] + insertion + new_source[new_for_e:]
                        if candidate != source:
                            out.append(candidate)
                    except Exception:
                        continue
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="flip_strict_compare",
                apply=_flip_strict_compare,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="counter_init_off_by_one",
                apply=_counter_init_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="hardcoded_slice_to_k",
                apply=_hardcoded_slice_to_k,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_var_mismatch",
                apply=_return_var_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="extend_index_fix",
                apply=_extend_index_fix,
                symptoms=("wrong", "err:IndexError"),
            ),
            Rule(
                name="k_zero_check_missing",
                apply=_k_zero_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="counter_increment_misplaced",
                apply=_counter_break_fix,
                symptoms=("wrong", "timeout"),
            ),
        ]