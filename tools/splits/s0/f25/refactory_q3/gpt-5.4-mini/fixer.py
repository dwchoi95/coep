import ast
from src.core.repair import Rule


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


def _replace_node(source, target, replacement):
    return _splice(source, target, replacement)


def _dedupe_append_rule(source):
    """Use append instead of extending a list with a scalar element."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "extend" and len(node.args) == 1:
                arg = node.args[0]
                try:
                    out.append(_replace_node(source, node, source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]] + ".append(" + source[_span(source, arg)[0]:_span(source, arg)[1]] + ")"))
                except Exception:
                    pass
    return out


def _wrong_iterable_name_rule(source):
    """Iterate over the function argument instead of the built-in list/type name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    func = None
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == "remove_extras":
            func = n
            break
    if func is None or not func.args.args:
        return []
    param = func.args.args[0].arg
    for node in ast.walk(func):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
            out.append(_replace_node(source, node.iter, param))
    return out


def _undefined_seen_rule(source):
    """Replace an undefined membership target with the accumulating output list."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "seen":
            out.append(_replace_node(source, node, "output"))
    return out


def _use_result_not_input_rule(source):
    """Check for duplicates in the accumulating result, not the original input."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "lst":
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                out.append(_replace_node(source, node, left + " in new"))
    return out


def _append_instead_of_insert_rule(source):
    """Append at the end to preserve order instead of inserting at the front."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "insert" and len(node.args) == 2:
                obj = source[_span(source, node.func.value)[0]:_span(source, node.func.value)[1]]
                arg = source[_span(source, node.args[1])[0]:_span(source, node.args[1])[1]]
                out.append(_replace_node(source, node, obj + ".append(" + arg + ")"))
    return out


def _listify_ordereddict_rule(source):
    """Wrap OrderedDict.fromkeys(...) in list(...)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "fromkeys":
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                out.append(_replace_node(source, node, "list(" + txt + ")"))
    return out


def _set_to_ordered_rule(source):
    """Replace set-based dedupe with OrderedDict.fromkeys for stable order."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    if "set(" not in source:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "set" and len(node.args) == 1:
            arg = node.args[0]
            repl = "OrderedDict.fromkeys(" + source[_span(source, arg)[0]:_span(source, arg)[1]] + ")"
            out.append(_replace_node(source, node, repl))
    return out


def _early_return_rule(source):
    """Move an early return out of the loop by replacing it with continue/skip logic."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            parent = None
            for p in ast.walk(tree):
                for ch in ast.iter_child_nodes(p):
                    if ch is node:
                        parent = p
                        break
            if isinstance(parent, ast.For):
                out.append(_replace_node(source, node, "        continue"))
    return out


def _append_not_add_rule(source):
    """Use list concatenation syntax instead of adding a scalar to a list."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            target = source[_span(source, node.target)[0]:_span(source, node.target)[1]]
            val = source[_span(source, node.value)[0]:_span(source, node.value)[1]]
            out.append(_replace_node(source, node, target + " += [" + val + "]"))
    return out


def _count_condition_rule(source):
    """Fix count-based tests to compare against the accumulating list instead of mutating input."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if ".count(" in txt and "== 0" in txt:
                out.append(_replace_node(source, node, txt.replace(".count(", " in ").replace(")== 0", ")")))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="extend_scalar_to_append", apply=_dedupe_append_rule, symptoms=("wrong",)),
            Rule(name="iterate_parameter_instead_of_builtin_list", apply=_wrong_iterable_name_rule, symptoms=("wrong", "err:TypeError")),
            Rule(name="undefined_seen_to_output", apply=_undefined_seen_rule, symptoms=("err:NameError", "wrong")),
            Rule(name="membership_should_check_result", apply=_use_result_not_input_rule, symptoms=("wrong",)),
            Rule(name="insert_should_append", apply=_append_instead_of_insert_rule, symptoms=("wrong",)),
            Rule(name="wrap_ordereddict_keys_in_list", apply=_listify_ordereddict_rule, symptoms=("wrong",)),
            Rule(name="set_to_ordered_dict", apply=_set_to_ordered_rule, symptoms=("wrong",)),
            Rule(name="early_return_in_loop", apply=_early_return_rule, symptoms=("wrong",)),
            Rule(name="scalar_addition_to_list", apply=_append_not_add_rule, symptoms=("wrong", "err:TypeError")),
            Rule(name="count_condition_on_accumulator", apply=_count_condition_rule, symptoms=("wrong",)),
        ]