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


def _iter_target_funcs(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "remove_extras":
            yield node


def _find_name(source, node, target):
    if isinstance(node, ast.Name) and node.id == target:
        return source[_span(source, node)[0]:_span(source, node)[1]]
    return None


def _rule_container_membership(source):
    """Fix membership checks against the input list instead of the output list."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _iter_target_funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.NotIn):
                if len(node.comparators) != 1:
                    continue
                comp = node.comparators[0]
                if isinstance(comp, ast.Name) and comp.id in {"lst", "list"}:
                    left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    new_cmp = f"{left} not in new_lst"
                    out.append(_splice(source, node, new_cmp))
    return out


def _rule_list_typo_to_input(source):
    """Fix accidental iteration over the built-in list name instead of the argument."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _iter_target_funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
                new_iter = source[_span(source, node.iter)[0]:_span(source, node.iter)[1]].replace("list", "lst", 1)
                out.append(_splice(source, node.iter, new_iter))
    return out


def _rule_append_assign_to_append(source):
    """Fix assigning the result of list.append, which is always None."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _iter_target_funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                    if node.value.func.attr == "append":
                        obj = node.value.func.value
                        if isinstance(obj, ast.Name) and obj.id in {"newlst", "new_list", "new_lst", "remove_lst"}:
                            s, e = _span(source, node)
                            lines = source.splitlines(keepends=True)
                            starts = [0]
                            for ln in lines:
                                starts.append(starts[-1] + len(ln))
                            indent = source[starts[node.lineno - 1]:starts[node.lineno - 1] + node.col_offset]
                            target = source[_span(source, node.targets[0])[0]:_span(source, node.targets[0])[1]]
                            arg = source[_span(source, node.value.args[0])[0]:_span(source, node.value.args[0])[1]]
                            new_stmt = f"{indent}{target}.append({arg})"
                            out.append(source[:s] + new_stmt + source[e:])
    return out


def _rule_plus_elem_to_list_elem(source):
    """Fix concatenation of a list with a bare element by wrapping the element in a singleton list."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _iter_target_funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if isinstance(node.right, ast.Name):
                    left_txt = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    right_txt = source[_span(source, node.right)[0]:_span(source, node.right)[1]]
                    out.append(_splice(source, node, f"{left_txt} + [{right_txt}]"))
    return out


def _rule_plus_paren_tuple_to_list(source):
    """Fix tuple syntax used where a list singleton was intended."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _iter_target_funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                if isinstance(node.right, ast.Tuple) and len(node.right.elts) == 1:
                    left_txt = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                    elt_txt = source[_span(source, node.right.elts[0])[0]:_span(source, node.right.elts[0])[1]]
                    out.append(_splice(source, node, f"{left_txt} + [{elt_txt}]"))
    return out


def _rule_bad_newlist_names(source):
    """Unify common output-list variable name typos when the body clearly appends to it."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _iter_target_funcs(tree):
        names = {"newlst", "new_list", "new_lst", "remove_lst", "output", "final"}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and node.id in names:
                parent_hits = 0
                for other in ast.walk(func):
                    if isinstance(other, ast.Attribute) and isinstance(other.value, ast.Name):
                        if other.value.id == node.id and other.attr in {"append", "count"}:
                            parent_hits += 1
                if parent_hits:
                    continue
            if isinstance(node, ast.Name) and node.id in {"new_list", "remove_lst"}:
                rep = "new_lst" if node.id == "new_list" else "output"
                out.append(_splice(source, node, rep))
    return out


def _rule_increment_j_in_nested_loop(source):
    """Repair the inner-loop index update in duplicate removal by adding the missing else branch increment."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in _iter_target_funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.While):
                for inner in ast.walk(node):
                    if isinstance(inner, ast.If) and isinstance(inner.test, ast.Compare):
                        cmp = inner.test
                        if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq):
                            if len(inner.body) == 1 and isinstance(inner.body[0], ast.Assign):
                                target = inner.body[0].targets[0]
                                value = inner.body[0].value
                                if isinstance(target, ast.Name) and isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
                                    if isinstance(value.left, ast.Name) and value.left.id == target.id:
                                        s, e = _span(source, inner)
                                        lines = source.splitlines(keepends=True)
                                        starts = [0]
                                        for ln in lines:
                                            starts.append(starts[-1] + len(ln))
                                        indent = source[starts[inner.lineno - 1]:starts[inner.lineno - 1] + inner.col_offset]
                                        cmp_txt = source[_span(source, cmp.left)[0]:_span(source, cmp.left)[1]]
                                        right_txt = source[_span(source, cmp.comparators[0])[0]:_span(source, cmp.comparators[0])[1]]
                                        body_stmt = source[_span(source, inner.body[0])[0]:_span(source, inner.body[0])[1]]
                                        new_if = (
                                            f"{indent}if {cmp_txt} == {right_txt}:\n"
                                            f"{indent}    {body_stmt.strip()}\n"
                                            f"{indent}else:\n"
                                            f"{indent}    {target.id} += 1"
                                        )
                                        out.append(source[:s] + new_if + source[e:])
                                        return out
    return out


def _rule_add_import_ordered_dict(source):
    """Add the missing OrderedDict import when it is used directly."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    uses = False
    has_import = False
    insert_at = None
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "collections":
            for alias in node.names:
                if alias.name == "OrderedDict":
                    has_import = True
        if insert_at is None:
            insert_at = _span(source, node)[0]
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id == "OrderedDict":
                uses = True
    if uses and not has_import:
        prefix = "from collections import OrderedDict\n\n"
        return [prefix + source]
    return []


class Fixer:
    def rules(self):
        return [
            Rule(name="membership_should_use_output_list", apply=_rule_container_membership, symptoms=("wrong",)),
            Rule(name="iterate_over_lst_not_builtin_list", apply=_rule_list_typo_to_input, symptoms=("wrong",)),
            Rule(name="append_result_instead_of_assigning_none", apply=_rule_append_assign_to_append, symptoms=("wrong",)),
            Rule(name="wrap_bare_element_in_list_concatenation", apply=_rule_plus_elem_to_list_elem, symptoms=("wrong",)),
            Rule(name="wrap_singleton_tuple_as_list", apply=_rule_plus_paren_tuple_to_list, symptoms=("wrong",)),
            Rule(name="common_output_variable_typos", apply=_rule_bad_newlist_names, symptoms=("wrong",)),
            Rule(name="missing_inner_loop_increment", apply=_rule_increment_j_in_nested_loop, symptoms=("wrong", "timeout")),
            Rule(name="add_ordereddict_import", apply=_rule_add_import_ordered_dict, symptoms=("err:NameError",)),
        ]