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


def _remove_stmt_line(source, stmt):
    lines = source.splitlines(keepends=True)
    start_line = stmt.lineno - 1
    end_line = stmt.end_lineno - 1
    return ''.join(lines[:start_line] + lines[end_line + 1:])


def _line_indent(source, node):
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[:len(line) - len(line.lstrip(' \t'))]


def _unwrap_index(slice_node):
    if hasattr(ast, 'Index') and isinstance(slice_node, ast.Index):
        return slice_node.value
    return slice_node


def _root_name(node):
    while isinstance(node, ast.Subscript):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _decl_acc(body, exclude):
    for node in body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.List) and len(node.value.elts) == 0
                and node.targets[0].id not in exclude):
            return node.targets[0].id
    return None


def _target_funcs(tree, name='remove_extras'):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name and node.args.args:
            yield node


def _extend_to_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'extend' and len(node.args) == 1):
            arg = node.args[0]
            if isinstance(arg, (ast.List, ast.Tuple)):
                continue
            fs, fe = _span(source, node.func)
            text = source[fs:fe]
            if text.endswith('extend'):
                new_text = text[:-len('extend')] + 'append'
                out.append(source[:fs] + new_text + source[fe:])
    return out


def _iterate_over_builtin_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        if param == 'list':
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.For) and isinstance(node.iter, ast.Name)
                    and node.iter.id == 'list'):
                out.append(_splice(source, node.iter, param))
    return out


def _membership_against_source(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        acc = _decl_acc(fn.body, {param})
        for forn in ast.walk(fn):
            if not isinstance(forn, ast.For) or not isinstance(forn.target, ast.Name):
                continue
            item = forn.target.id
            local_acc = acc
            if local_acc is None:
                for sub in ast.walk(forn):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr in ('append', 'extend')
                            and isinstance(sub.func.value, ast.Name)
                            and sub.func.value.id not in (item, param)):
                        local_acc = sub.func.value.id
                        break
                    if (isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name)
                            and isinstance(sub.op, ast.Add) and sub.target.id not in (item, param)):
                        local_acc = sub.target.id
                        break
            if local_acc is None or local_acc == item:
                continue
            for cmp in ast.walk(forn):
                if (isinstance(cmp, ast.Compare) and len(cmp.ops) == 1
                        and isinstance(cmp.left, ast.Name) and cmp.left.id == item):
                    comp = cmp.comparators[0]
                    root = _root_name(comp)
                    if root == param and root != local_acc:
                        out.append(_splice(source, comp, local_acc))
    return out


def _loop_target_shadows_accumulator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        assigned_names = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                assigned_names.add(node.id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                assigned_names.add(node.target.id)
        for forn in ast.walk(fn):
            if not isinstance(forn, ast.For) or not isinstance(forn.target, ast.Name):
                continue
            tgt = forn.target.id
            if tgt == param:
                continue
            is_acc = any(
                isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == tgt
                and isinstance(node.value, ast.List) and len(node.value.elts) == 0
                for node in fn.body
            )
            if not is_acc:
                continue
            counts = {}
            for node in ast.walk(forn):
                if node is forn.target:
                    continue
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.id in (tgt, param) or node.id in assigned_names:
                        continue
                    counts[node.id] = counts.get(node.id, 0) + 1
            if not counts:
                continue
            item_name = max(counts, key=counts.get)
            out.append(_splice(source, forn.target, item_name))
    return out


def _undefined_name_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    builtins_ok = {'len', 'range', 'list', 'set', 'tuple', 'int', 'str', 'sorted', 'enumerate'}
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        assigned_names = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                assigned_names.add(node.id)
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                assigned_names.add(node.target.id)
        acc = _decl_acc(fn.body, {param})
        if acc is None:
            continue
        for forn in ast.walk(fn):
            if not isinstance(forn, ast.For):
                continue
            free_names = set()
            for node in ast.walk(forn):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.id in assigned_names or node.id in (param, acc) or node.id in builtins_ok:
                        continue
                    free_names.add(node.id)
            if len(free_names) != 1:
                continue
            bad = next(iter(free_names))
            occurrences = [n for n in ast.walk(forn)
                           if isinstance(n, ast.Name) and n.id == bad and isinstance(n.ctx, ast.Load)]
            if not occurrences:
                continue
            new_source = source
            for n in sorted(occurrences, key=lambda x: _span(source, x)[0], reverse=True):
                new_source = _splice(new_source, n, acc)
            out.append(new_source)
    return out


def _augassign_wraps_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                and isinstance(node.target, ast.Name)):
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                    and val.func.attr == 'append' and isinstance(val.func.value, ast.Name)
                    and val.func.value.id == node.target.id):
                vs, ve = _span(source, val)
                out.append(_splice(source, node, source[vs:ve]))
    return out


def _append_target_should_be_accumulator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        acc = _decl_acc(fn.body, {param})
        if acc is None:
            continue
        acc_appended = any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ('append', 'extend') and isinstance(node.func.value, ast.Name)
            and node.func.value.id == acc
            for node in ast.walk(fn)
        )
        if acc_appended:
            continue
        for forn in ast.walk(fn):
            if not isinstance(forn, ast.For):
                continue
            if not (isinstance(forn.iter, ast.Name) and forn.iter.id == param):
                continue
            for node in ast.walk(forn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ('append', 'extend')
                        and isinstance(node.func.value, ast.Name) and node.func.value.id == param):
                    out.append(_splice(source, node.func.value, acc))
    return out


def _count_condition_to_membership(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        acc = _decl_acc(fn.body, {param})
        if acc is None:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
                left = node.left
                op = node.ops[0]
                comp = node.comparators[0]
                if (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                        and left.func.attr == 'count' and isinstance(left.func.value, ast.Name)
                        and left.func.value.id == param and len(left.args) == 1
                        and isinstance(op, ast.Eq) and isinstance(comp, ast.Constant)
                        and comp.value == 1):
                    its, ite = _span(source, left.args[0])
                    item_src = source[its:ite]
                    out.append(_splice(source, node, f"{item_src} not in {acc}"))
    return out


def _index0_should_be_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        for node in fn.body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                var = node.targets[0].id
                val = node.value
                if isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) and val.value.id == param:
                    idx = _unwrap_index(val.slice)
                    if isinstance(idx, ast.Constant) and idx.value == 0:
                        used_as_container = any(
                            isinstance(n2, ast.Compare)
                            and any(isinstance(c, ast.Name) and c.id == var for c in n2.comparators)
                            for n2 in ast.walk(fn)
                        )
                        if used_as_container:
                            vs, ve = _span(source, val)
                            out.append(_splice(source, val, "[" + source[vs:ve] + "]"))
    return out


def _insert_empty_guard(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        has_index0 = False
        for node in ast.walk(fn):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == param:
                idx = _unwrap_index(node.slice)
                if isinstance(idx, ast.Constant) and idx.value == 0:
                    has_index0 = True
        if not has_index0:
            continue
        has_guard = False
        for node in fn.body:
            if isinstance(node, ast.If):
                try:
                    ts, te = _span(source, node.test)
                    src_test = source[ts:te]
                except Exception:
                    src_test = ''
                if param in src_test and ('[]' in src_test or 'not ' in src_test or 'len(' in src_test):
                    has_guard = True
        if has_guard:
            continue
        first = fn.body[0]
        fs, _ = _span(source, first)
        indent = _line_indent(source, first)
        guard = f"if not {param}:\n{indent}    return []\n{indent}"
        out.append(source[:fs] + guard + source[fs:])
    return out


def _remove_redundant_sort_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        for stmt in fn.body:
            if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Attribute) and stmt.value.func.attr == 'sort'
                    and isinstance(stmt.value.func.value, ast.Name) and stmt.value.func.value.id == param
                    and not stmt.value.args):
                out.append(_remove_stmt_line(source, stmt))
    return out


def _tuple_accumulator_return_as_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        tuple_vars = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Tuple)):
                tuple_vars.add(node.targets[0].id)
            if (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
                    and isinstance(node.value, ast.Tuple)):
                tuple_vars.add(node.target.id)
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id in tuple_vars:
                vs, ve = _span(source, node.value)
                out.append(_splice(source, node.value, f"list({source[vs:ve]})"))
    return out


def _range_arg_missing_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'range'
                    and len(node.args) == 1 and isinstance(node.args[0], ast.Name)
                    and node.args[0].id == param):
                s, e = _span(source, node.args[0])
                out.append(source[:s] + f"len({param})" + source[e:])
    return out


def _return_wrong_variable(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        acc = _decl_acc(fn.body, {param})
        if acc is None:
            continue
        acc_appended = any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ('append', 'extend') and isinstance(node.func.value, ast.Name)
            and node.func.value.id == acc
            for node in ast.walk(fn)
        )
        if not acc_appended:
            continue
        for node in fn.body:
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == param:
                out.append(_splice(source, node.value, acc))
    return out


def _assign_wraps_append_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            tgt = node.targets[0].id
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                    and val.func.attr in ('append', 'extend', 'insert')):
                args_src = []
                for a in val.args:
                    s, e = _span(source, a)
                    args_src.append(source[s:e])
                new_call = f"{tgt}.{val.func.attr}({', '.join(args_src)})"
                out.append(_splice(source, node, new_call))
    return out


def _add_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in _target_funcs(tree):
        param = fn.args.args[0].arg
        if any(isinstance(s, ast.Return) for s in fn.body):
            continue
        acc = _decl_acc(fn.body, {param})
        if acc is None:
            continue
        last = fn.body[-1]
        _, e = _span(source, last)
        indent = _line_indent(source, fn.body[0])
        out.append(source[:e] + f"\n{indent}return {acc}" + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="extend_scalar_should_be_append",
                 apply=_extend_to_append,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="iterate_over_builtin_list_not_param",
                 apply=_iterate_over_builtin_list,
                 symptoms=("err:NameError",)),
            Rule(name="membership_checked_against_source_not_accumulator",
                 apply=_membership_against_source,
                 symptoms=("wrong",)),
            Rule(name="loop_target_shadows_accumulator",
                 apply=_loop_target_shadows_accumulator,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_name_typo_for_accumulator",
                 apply=_undefined_name_typo,
                 symptoms=("err:NameError",)),
            Rule(name="augassign_wraps_append_call",
                 apply=_augassign_wraps_append,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="append_target_should_be_accumulator",
                 apply=_append_target_should_be_accumulator,
                 symptoms=("wrong",)),
            Rule(name="count_condition_should_be_membership",
                 apply=_count_condition_to_membership,
                 symptoms=("wrong",)),
            Rule(name="index0_init_should_be_singleton_list",
                 apply=_index0_should_be_list,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="insert_empty_list_guard_before_index0",
                 apply=_insert_empty_guard,
                 symptoms=("err:IndexError",)),
            Rule(name="remove_redundant_sort_call",
                 apply=_remove_redundant_sort_call,
                 symptoms=("wrong",)),
            Rule(name="tuple_accumulator_return_should_be_list",
                 apply=_tuple_accumulator_return_as_list,
                 symptoms=("wrong",)),
            Rule(name="range_arg_missing_len",
                 apply=_range_arg_missing_len,
                 symptoms=("err:TypeError",)),
            Rule(name="return_wrong_variable_use_accumulator",
                 apply=_return_wrong_variable,
                 symptoms=("wrong",)),
            Rule(name="assign_wraps_append_call",
                 apply=_assign_wraps_append_call,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="add_missing_return_for_accumulator",
                 apply=_add_missing_return,
                 symptoms=("wrong",)),
        ]