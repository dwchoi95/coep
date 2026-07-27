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


def _find_func(tree, name="remove_extras"):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _fix_membership_against_source_list(source):
    """`if x not in <original list>` should check the accumulator instead."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not isinstance(node.iter, ast.Name):
            continue
        iter_name = node.iter.id

        acc_names = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
               and n.func.attr == "append" and isinstance(n.func.value, ast.Name):
                acc_names.add(n.func.value.id)
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) \
               and isinstance(n.op, ast.Add):
                acc_names.add(n.target.id)
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
               and isinstance(n.targets[0], ast.Name) \
               and isinstance(n.value, ast.BinOp) and isinstance(n.value.op, ast.Add):
                left = n.value.left
                if isinstance(left, ast.Name) and left.id == n.targets[0].id:
                    acc_names.add(n.targets[0].id)
        acc_names.discard(iter_name)
        if not acc_names:
            continue

        for cnode in ast.walk(node):
            if isinstance(cnode, ast.Compare) and len(cnode.ops) == 1:
                op = cnode.ops[0]
                comp = cnode.comparators[0]
                if isinstance(comp, ast.Name) and comp.id == iter_name \
                   and isinstance(op, (ast.In, ast.NotIn)):
                    for acc in acc_names:
                        s, e = _span(source, comp)
                        out.append(source[:s] + acc + source[e:])
    return out


def _fix_shadowed_list_iter(source):
    """`for item in list:` should iterate over the actual parameter."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func_def = _find_func(tree)
    if func_def is None or not func_def.args.args:
        return []
    param_name = func_def.args.args[0].arg
    if param_name == "list":
        return []
    out = []
    for n in ast.walk(func_def):
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Name) and n.iter.id == "list":
            s, e = _span(source, n.iter)
            out.append(source[:s] + param_name + source[e:])
    return out


def _fix_bare_item_concat(source):
    """`acc = acc + item` should be `acc = acc + [item]`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            val = node.value
            if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                left, right = val.left, val.right
                if isinstance(left, ast.Name) and left.id == target_name \
                   and isinstance(right, ast.Name):
                    s, e = _span(source, right)
                    wrapped = "[" + source[s:e] + ",]"
                    out.append(source[:s] + wrapped + source[e:])
    return out


def _fix_typo_accumulator_name(source):
    """`good_lst.append(x)` mistakenly written as `undefined_name.append(x)`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func_def = _find_func(tree)
    if func_def is None:
        return []
    defined_lists = set()
    for node in ast.walk(func_def):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name) \
           and isinstance(node.value, ast.List) and len(node.value.elts) == 0:
            defined_lists.add(node.targets[0].id)
    if len(defined_lists) != 1:
        return []
    good_name = next(iter(defined_lists))
    param_names = {a.arg for a in func_def.args.args}

    out = []
    for node in ast.walk(func_def):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "append" and isinstance(node.func.value, ast.Name):
            nm = node.func.value.id
            if nm != good_name and nm not in param_names:
                s, e = _span(source, node.func.value)
                out.append(source[:s] + good_name + source[e:])
    return out


def _fix_missing_ordereddict_import(source):
    """Uses OrderedDict without importing it."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    uses = False
    has_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "OrderedDict":
            uses = True
        if isinstance(node, ast.ImportFrom) and node.module == "collections":
            for alias in node.names:
                if alias.name == "OrderedDict":
                    has_import = True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "collections":
                    has_import = True
    if uses and not has_import:
        return ["from collections import OrderedDict\n" + source]
    return []


def _fix_append_reassignment(source):
    """`acc = acc.append(x)` discards the list (append returns None)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
               and val.func.attr == "append" and isinstance(val.func.value, ast.Name) \
               and val.func.value.id == node.targets[0].id:
                vs, ve = _span(source, val)
                out.append(_splice(source, node, source[vs:ve]))
    return out


def _fix_mutating_for_range(source):
    """A `for j in range(...)` that mutates the sequence being scanned skips
    elements; convert it to a manual while-loop that only advances on a miss."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    lines = source.splitlines(keepends=True)
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not (isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"):
            continue
        args = node.iter.args
        if len(args) != 2:
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.If):
            continue
        if_node = node.body[0]
        if if_node.orelse:
            continue
        if not isinstance(node.target, ast.Name):
            continue
        j_name = node.target.id

        ss, se = _span(source, args[0])
        start_text = source[ss:se]
        ts, te = _span(source, args[1])
        stop_text = source[ts:te]
        cs, ce = _span(source, if_node.test)
        cond_text = source[cs:ce]

        body_texts = []
        for stmt in if_node.body:
            bs, be = _span(source, stmt)
            body_texts.append(source[bs:be])

        line_text = lines[node.lineno - 1]
        indent = line_text[: len(line_text) - len(line_text.lstrip())]
        body_indent = indent + "    "
        inner_indent = body_indent + "    "

        new_code = f"{j_name} = {start_text}\n"
        new_code += f"{indent}while {j_name} < {stop_text}:\n"
        new_code += f"{body_indent}if {cond_text}:\n"
        for bt in body_texts:
            new_code += f"{inner_indent}{bt}\n"
        new_code += f"{body_indent}else:\n{inner_indent}{j_name} += 1"

        out.append(_splice(source, node, new_code))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="membership_check_against_source_list",
                apply=_fix_membership_against_source_list,
                symptoms=("wrong",),
            ),
            Rule(
                name="iterate_over_shadowed_list_name",
                apply=_fix_shadowed_list_iter,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="concat_bare_item_instead_of_list",
                apply=_fix_bare_item_concat,
                symptoms=("err:TypeError", "wrong"),
            ),
            Rule(
                name="typo_accumulator_variable_name",
                apply=_fix_typo_accumulator_name,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="missing_ordereddict_import",
                apply=_fix_missing_ordereddict_import,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="append_result_reassigned_to_none",
                apply=_fix_append_reassignment,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="mutating_for_range_skips_elements",
                apply=_fix_mutating_for_range,
                symptoms=("wrong", "timeout"),
            ),
        ]