import ast
import builtins
import difflib

from src.core.repair import Rule

_BUILTINS = set(dir(builtins))


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def _span(source, node):
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


def _get_func(tree, name="sort_age"):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _sole_param(func):
    if func.args.args:
        return func.args.args[0].arg
    return None


def _unwrap_slice(sl):
    if isinstance(sl, ast.Index):
        return sl.value
    return sl


def _assigned_names(func):
    names = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
        elif isinstance(node, ast.AugAssign):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, ast.For):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def _undefined_name_nodes(func, assigned):
    result = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in assigned or node.id in _BUILTINS or node.id == func.name:
                continue
            result.setdefault(node.id, []).append(node)
    return result


def _uses_name_as_whole_tuple(func, name):
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("remove", "append", "insert"):
                for a in node.args:
                    if isinstance(a, ast.Name) and a.id == name:
                        return True
    return False


def _has_reverse_of_result(func):
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "reverse":
            return True
        if isinstance(node, ast.Subscript):
            sl = _unwrap_slice(node.slice)
            if isinstance(sl, ast.Slice) and sl.step is not None:
                if isinstance(sl.step, ast.UnaryOp) and isinstance(sl.step.op, ast.USub):
                    return True
    return False


def _is_swap_assign(stmt):
    return (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Tuple) and isinstance(stmt.value, ast.Tuple))


# ---------------------------------------------------------------------------
# Rule 1: rename a NameError identifier that is a typo of a real local name
# ---------------------------------------------------------------------------

def typo_undefined_rename(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    assigned = _assigned_names(func)
    undefined = _undefined_name_nodes(func, assigned)
    out = []
    for undef_id, nodes in undefined.items():
        candidates = []
        for name in assigned:
            if name == undef_id:
                continue
            ratio = difflib.SequenceMatcher(None, undef_id, name).ratio()
            if ratio >= 0.75 or undef_id in name or name in undef_id:
                candidates.append(name)
        candidates = sorted(set(candidates))
        if len(candidates) == 1:
            repl = candidates[0]
            spans = sorted((_span(source, n) for n in nodes), key=lambda se: se[0], reverse=True)
            new_src = source
            for s, e in spans:
                new_src = new_src[:s] + repl + new_src[e:]
            out.append(new_src)
    return out


# ---------------------------------------------------------------------------
# Rule 2: undefined argument to .remove()/.append() should be the real tracker
# ---------------------------------------------------------------------------

def tracker_rename_in_remove_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    assigned = _assigned_names(func)
    out = []
    for node in ast.walk(func):
        if not isinstance(node, ast.While):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        tracker = None
        if (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name) and isinstance(first.value, ast.Subscript)):
            tracker = first.targets[0].id
        if tracker is None:
            continue
        remove_node = append_node = None
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.args and isinstance(call.args[0], ast.Name):
                    if call.func.attr == "remove":
                        remove_node = call.args[0]
                    elif call.func.attr == "append":
                        append_node = call.args[0]
        if remove_node is not None and append_node is not None:
            if remove_node.id == append_node.id and remove_node.id != tracker and remove_node.id not in assigned:
                spans = sorted([_span(source, remove_node), _span(source, append_node)],
                                key=lambda se: se[0], reverse=True)
                new_src = source
                for s, e in spans:
                    new_src = new_src[:s] + tracker + new_src[e:]
                out.append(new_src)
    return out


# ---------------------------------------------------------------------------
# Rule 3: undefined container identifier should be the function's parameter
# ---------------------------------------------------------------------------

def undefined_container_to_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    param = _sole_param(func)
    if not param:
        return []
    assigned = _assigned_names(func)
    undefined = _undefined_name_nodes(func, assigned)
    out = []
    for undef_id, nodes in undefined.items():
        if undef_id == param:
            continue
        used_as_container = False
        for node in ast.walk(func):
            if isinstance(node, ast.While) and isinstance(node.test, ast.Name) and node.test.id == undef_id:
                used_as_container = True
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == undef_id:
                used_as_container = True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("remove", "append", "pop") and isinstance(node.func.value, ast.Name):
                    if node.func.value.id == undef_id:
                        used_as_container = True
        if used_as_container:
            spans = sorted((_span(source, n) for n in nodes), key=lambda se: se[0], reverse=True)
            new_src = source
            for s, e in spans:
                new_src = new_src[:s] + param + new_src[e:]
            out.append(new_src)
    return out


# ---------------------------------------------------------------------------
# Rule 4: bare tracker compared against element[1] is missing its own [1]
# ---------------------------------------------------------------------------

def add_subscript_to_bare_tracker_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Lt, ast.Gt)):
            left = node.left
            right = node.comparators[0]
            candidates = []
            if isinstance(left, ast.Subscript) and isinstance(right, ast.Name):
                candidates.append(right)
            if isinstance(right, ast.Subscript) and isinstance(left, ast.Name):
                candidates.append(left)
            for name_node in candidates:
                if _uses_name_as_whole_tuple(func, name_node.id):
                    new_text = name_node.id + "[1]"
                    out.append(_splice(source, name_node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 5: tracker reassigned from element[1] (int) instead of whole element
# ---------------------------------------------------------------------------

def strip_subscript_in_tracker_reassign(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    out = []
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        for stmt in node.body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Subscript)
                    and isinstance(stmt.value.value, ast.Name)):
                tracker = stmt.targets[0].id
                if _uses_name_as_whole_tuple(func, tracker):
                    replacement = stmt.value.value.id
                    out.append(_splice(source, stmt.value, replacement))
    return out


# ---------------------------------------------------------------------------
# Rule 6: tracker initialized with a double subscript ([0][1]) but later
# treated as the whole tuple -> strip the trailing [1]
# ---------------------------------------------------------------------------

def strip_double_subscript_tracker_init(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    out = []
    for node in ast.walk(func):
        if not isinstance(node, ast.While):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)
                and isinstance(first.value, ast.Subscript)
                and isinstance(first.value.value, ast.Subscript)):
            tracker = first.targets[0].id
            if _uses_name_as_whole_tuple(func, tracker):
                inner = first.value.value
                s, e = _span(source, inner)
                new_text = source[s:e]
                out.append(_splice(source, first.value, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 7: bare element compared to bare tracker (forgot [1] on both sides)
# ---------------------------------------------------------------------------

def bare_compare_add_age_subscript(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    out = []
    for node in ast.walk(func):
        if not isinstance(node, ast.For):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        loop_var = node.target.id
        for n in ast.walk(node):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], (ast.Lt, ast.Gt)):
                left, right = n.left, n.comparators[0]
                if (isinstance(left, ast.Name) and left.id == loop_var
                        and isinstance(right, ast.Name) and right.id != loop_var
                        and _uses_name_as_whole_tuple(func, right.id)):
                    new_cmp = left.id + "[1]" + (" < " if isinstance(n.ops[0], ast.Lt) else " > ") + right.id + "[1]"
                    out.append(_splice(source, n, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule 8: empty-list guard written with a tuple instead of a list
# ---------------------------------------------------------------------------

def empty_tuple_to_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    param = _sole_param(func)
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left, right = node.left, node.comparators[0]
            if (isinstance(left, ast.Name) and left.id == param
                    and isinstance(right, ast.Tuple) and not right.elts):
                out.append(_splice(source, right, "[]"))
    return out


# ---------------------------------------------------------------------------
# Rule 9: no guard before indexing the parameter at [0] -> IndexError on []
# ---------------------------------------------------------------------------

def guard_empty_list_before_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    param = _sole_param(func)
    if not param:
        return []
    body = func.body
    stmts = [s for s in body if not (isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant)
                                      and isinstance(s.value.value, str))]
    if not stmts:
        return []
    first = stmts[0]
    if isinstance(first, (ast.If,)):
        return []
    found = False
    for n in ast.walk(first):
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == param:
            sl = _unwrap_slice(n.slice)
            if isinstance(sl, ast.Constant) and sl.value == 0:
                found = True
    if not found:
        return []
    indent = " " * first.col_offset
    guard = f"if not {param}:\n{indent}    return []\n{indent}"
    s, _ = _span(source, first)
    new_src = source[:s] + guard + source[s:]
    return [new_src]


# ---------------------------------------------------------------------------
# Rule 10: .pop([lst[i]]) should be del lst[i]
# ---------------------------------------------------------------------------

def fix_wrong_pop_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "pop" and len(node.args) == 1):
            arg = node.args[0]
            if isinstance(arg, ast.List) and len(arg.elts) == 1 and isinstance(arg.elts[0], ast.Subscript):
                inner = arg.elts[0]
                recv_s, recv_e = _span(source, node.func.value)
                idx_node = _unwrap_slice(inner.slice)
                idx_s, idx_e = _span(source, idx_node)
                receiver_text = source[recv_s:recv_e]
                index_text = source[idx_s:idx_e]
                new_text = f"del {receiver_text}[{index_text}]"
                out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule 11: moving an element to the end without resetting the scan index
# ---------------------------------------------------------------------------

def insert_index_reset_after_move(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.If):
                continue
            has_extend = False
            del_stmt = None
            counter = None
            reset_present = False
            for s in stmt.body:
                if (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                        and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == "extend"):
                    has_extend = True
                if isinstance(s, ast.Delete):
                    for t in s.targets:
                        if isinstance(t, ast.Subscript):
                            sl = _unwrap_slice(t.slice)
                            if isinstance(sl, ast.Name):
                                counter = sl.id
                                del_stmt = s
            if counter:
                for s in stmt.body:
                    if isinstance(s, ast.Assign):
                        for tg in s.targets:
                            if isinstance(tg, ast.Name) and tg.id == counter:
                                reset_present = True
            if has_extend and del_stmt is not None and counter and not reset_present:
                _, e = _span(source, del_stmt)
                indent = " " * del_stmt.col_offset
                insertion = "\n" + indent + f"{counter} = 0"
                out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule 12: swap-based sort comparison pointing the wrong way
# ---------------------------------------------------------------------------

def flip_swap_comparison(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], (ast.Lt, ast.Gt))):
            continue
        has_swap = any(_is_swap_assign(s) for s in node.body)
        if not has_swap:
            continue
        op = node.test.ops[0]
        new_op = " < " if isinstance(op, ast.Gt) else " > "
        left_s, left_e = _span(source, node.test.left)
        right_s, right_e = _span(source, node.test.comparators[0])
        new_cmp = source[left_s:left_e] + new_op + source[right_s:right_e]
        out.append(_splice(source, node.test, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule 13: a single bubble-sort pass never repeated -> wrap in an outer loop
# ---------------------------------------------------------------------------

def wrap_single_pass_bubble_in_outer_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    top_loops = [n for n in func.body if isinstance(n, (ast.For, ast.While))]
    if len(top_loops) != 1 or not isinstance(top_loops[0], ast.For):
        return []
    loop = top_loops[0]
    if not (isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name)
            and loop.iter.func.id == "range" and loop.iter.args):
        return []
    bound = loop.iter.args[-1]
    if not (isinstance(bound, ast.BinOp) and isinstance(bound.op, ast.Sub)
            and isinstance(bound.left, ast.Call) and isinstance(bound.left.func, ast.Name)
            and bound.left.func.id == "len"):
        return []
    has_swap_if = False
    for n in ast.walk(loop):
        if isinstance(n, ast.If) and any(_is_swap_assign(s) for s in n.body):
            has_swap_if = True
    if not has_swap_if:
        return []
    param = _sole_param(func) or "lst"
    s, e = _span(source, loop)
    inner_text = source[s:e]
    lines = inner_text.splitlines(keepends=True)
    shifted = "".join(("    " + ln) if ln.strip() else ln for ln in lines)
    new_text = f"for _pass_ in range(len({param})):\n" + shifted
    return [source[:s] + new_text + source[e:]]


# ---------------------------------------------------------------------------
# Rule 14: return statement left inside the accumulation loop (early exit)
# ---------------------------------------------------------------------------

def move_return_out_of_while(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    out = []
    for node in ast.walk(func):
        if not isinstance(node, ast.While):
            continue
        body = node.body
        if len(body) < 2 or not isinstance(body[-1], ast.Return):
            continue
        ret = body[-1]
        if ret.col_offset <= node.col_offset:
            continue
        ret_s, _ = _span(source, ret)
        line_start = ret_s - ret.col_offset
        if source[line_start:ret_s].strip(" ") != "":
            continue
        while_indent = " " * node.col_offset
        new_src = source[:line_start] + while_indent + source[ret_s:]
        out.append(new_src)
    return out


# ---------------------------------------------------------------------------
# Rule 15: extremal-tracking comparison pointed the wrong way (min vs max)
# ---------------------------------------------------------------------------

def flip_extremal_comparison(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func = _get_func(tree)
    if not func:
        return []
    if _has_reverse_of_result(func):
        return []
    out = []
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Assign):
            continue
        assign = node.body[0]
        if not (len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name)):
            continue
        tracker = assign.targets[0].id
        val = assign.value
        loop_var_names = set()
        if isinstance(val, ast.Name):
            loop_var_names.add(val.id)
        elif isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name):
            loop_var_names.add(val.value.id)
        if not loop_var_names:
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], (ast.Lt, ast.Gt))):
            continue
        if not _uses_name_as_whole_tuple(func, tracker):
            continue
        op = test.ops[0]
        new_op = " < " if isinstance(op, ast.Gt) else " > "
        left_s, left_e = _span(source, test.left)
        right_s, right_e = _span(source, test.comparators[0])
        new_cmp = source[left_s:left_e] + new_op + source[right_s:right_e]
        out.append(_splice(source, test, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="typo_undefined_rename",
                 apply=typo_undefined_rename,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="tracker_rename_in_remove_append",
                 apply=tracker_rename_in_remove_append,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_container_to_param",
                 apply=undefined_container_to_param,
                 symptoms=("err:NameError",)),
            Rule(name="add_subscript_to_bare_tracker_compare",
                 apply=add_subscript_to_bare_tracker_compare,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="strip_subscript_in_tracker_reassign",
                 apply=strip_subscript_in_tracker_reassign,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="strip_double_subscript_tracker_init",
                 apply=strip_double_subscript_tracker_init,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="bare_compare_add_age_subscript",
                 apply=bare_compare_add_age_subscript,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="empty_tuple_to_list",
                 apply=empty_tuple_to_list,
                 symptoms=("wrong",)),
            Rule(name="guard_empty_list_before_index",
                 apply=guard_empty_list_before_index,
                 symptoms=("err:IndexError",)),
            Rule(name="fix_wrong_pop_call",
                 apply=fix_wrong_pop_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="insert_index_reset_after_move",
                 apply=insert_index_reset_after_move,
                 symptoms=("wrong", "timeout")),
            Rule(name="flip_swap_comparison",
                 apply=flip_swap_comparison,
                 symptoms=("wrong",)),
            Rule(name="wrap_single_pass_bubble_in_outer_loop",
                 apply=wrap_single_pass_bubble_in_outer_loop,
                 symptoms=("wrong",)),
            Rule(name="move_return_out_of_while",
                 apply=move_return_out_of_while,
                 symptoms=("wrong",)),
            Rule(name="flip_extremal_comparison",
                 apply=flip_extremal_comparison,
                 symptoms=("wrong",)),
        ]