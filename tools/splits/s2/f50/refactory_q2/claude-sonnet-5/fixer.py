import ast
import difflib
import builtins

from src.core.repair import Rule


# ----------------------------------------------------------------------
# generic AST helpers
# ----------------------------------------------------------------------

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


def _apply_edits(source, edits):
    """edits: list of (node, new_text). Apply all, largest offset first."""
    spans = []
    for node, text in edits:
        try:
            s, e = _span(source, node)
        except Exception:
            continue
        spans.append((s, e, text))
    if not spans:
        return None
    spans.sort(key=lambda x: x[0], reverse=True)
    out = source
    for s, e, text in spans:
        out = out[:s] + text + out[e:]
    return out


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _enclosing(node, kind):
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, kind):
            return cur
        cur = getattr(cur, "parent", None)
    return None


def _names_in_target(t):
    names = []
    if isinstance(t, ast.Name):
        names.append(t.id)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for e in t.elts:
            names.extend(_names_in_target(e))
    return names


def _collect_defined(func):
    defined = set(a.arg for a in func.args.args)
    if func.args.vararg:
        defined.add(func.args.vararg.arg)
    if func.args.kwarg:
        defined.add(func.args.kwarg.arg)
    for a in list(func.args.kwonlyargs) + list(getattr(func.args, "posonlyargs", [])):
        defined.add(a.arg)
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                defined.update(_names_in_target(t))
        elif isinstance(node, ast.AugAssign):
            defined.update(_names_in_target(node.target))
        elif isinstance(node, (ast.For, ast.comprehension)):
            defined.update(_names_in_target(node.target))
        elif isinstance(node, ast.FunctionDef):
            defined.add(node.name)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                defined.add(node.name)
        elif isinstance(node, ast.withitem):
            if node.optional_vars:
                defined.update(_names_in_target(node.optional_vars))
    return defined


def _module_funcs(tree):
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def _is_bool_const(node, val):
    return isinstance(node, ast.Constant) and isinstance(node.value, bool) and node.value is val


def _is_small_int(node, val):
    return isinstance(node, ast.Constant) and node.value == val and not isinstance(node.value, bool)


# ----------------------------------------------------------------------
# Rule 1: undefined name should be the unused first parameter
# ----------------------------------------------------------------------

def _rule_unused_param_rename(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    try:
        mod_funcs = _module_funcs(tree)
        bset = set(dir(builtins))
        edits = []
        for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            params = [a.arg for a in func.args.args]
            if not params:
                continue
            first_param = params[0]
            defined = _collect_defined(func)
            used_loads = set()
            load_nodes = []
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_loads.add(node.id)
                    load_nodes.append(node)
            if first_param in used_loads:
                continue
            undefined = set()
            for name in used_loads:
                if name in defined or name in bset or name in mod_funcs:
                    continue
                undefined.add(name)
            if len(undefined) != 1:
                continue
            bad = next(iter(undefined))
            targets = [n for n in load_nodes if n.id == bad]
            if not targets:
                continue
            for n in targets:
                edits.append((n, first_param))
        if not edits:
            return []
        new_source = _apply_edits(source, edits)
        if new_source is None or new_source == source:
            return []
        return [new_source]
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 2: call to an undefined function that closely matches a real one
# ----------------------------------------------------------------------

def _rule_typo_call_rename(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    try:
        mod_funcs = _module_funcs(tree)
        bset = set(dir(builtins))
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
                if name in mod_funcs or name in bset:
                    continue
                match = difflib.get_close_matches(name, list(mod_funcs), n=1, cutoff=0.6)
                if match:
                    edits.append((node.func, match[0]))
        if not edits:
            return []
        new_source = _apply_edits(source, edits)
        if new_source is None or new_source == source:
            return []
        return [new_source]
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 3: "duplicate count" boundary off-by-one (count>1/>=2/==2 logic)
# ----------------------------------------------------------------------

def _rule_fix_uniqueness_boundary(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    try:
        _add_parents(tree)
        edits = []

        # (a) bare `return <expr> > 1` / `>= 2`
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Compare) \
               and len(node.value.ops) == 1:
                cmp = node.value
                op = cmp.ops[0]
                right = cmp.comparators[0]
                left = cmp.left
                matched = (isinstance(op, ast.Gt) and _is_small_int(right, 1)) or \
                          (isinstance(op, ast.GtE) and _is_small_int(right, 2))
                if matched:
                    ls, le = _span(source, left)
                    left_text = source[ls:le]
                    edits.append((cmp, "%s == 1" % left_text))

        # (b) `if <expr> > 1 / >= 2 / == 2: return False` paired with a return True
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
                continue
            op = test.ops[0]
            right = test.comparators[0]
            left = test.left
            matched = (isinstance(op, ast.Gt) and _is_small_int(right, 1)) or \
                      (isinstance(op, ast.GtE) and _is_small_int(right, 2)) or \
                      (isinstance(op, ast.Eq) and _is_small_int(right, 2))
            if not matched:
                continue
            body = node.body
            if len(body) != 1 or not isinstance(body[0], ast.Return) or not _is_bool_const(body[0].value, False):
                continue
            ls, le = _span(source, left)
            left_text = source[ls:le]
            target_return = None
            if node.orelse and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return) \
               and _is_bool_const(node.orelse[0].value, True):
                target_return = node.orelse[0]
            else:
                func = _enclosing(node, ast.FunctionDef)
                if func is not None:
                    cands = [n for n in ast.walk(func)
                             if isinstance(n, ast.Return) and _is_bool_const(n.value, True)
                             and n.lineno >= node.lineno]
                    cands.sort(key=lambda n: (n.lineno, n.col_offset))
                    if cands:
                        target_return = cands[0]
            if target_return is not None:
                edits.append((target_return, "return %s == 1" % left_text))

        if not edits:
            return []
        new_source = _apply_edits(source, edits)
        if new_source is None or new_source == source:
            return []
        return [new_source]
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 4: contains_unique_day calls unique_day with the month index (x[0])
# instead of the day index (x[1])
# ----------------------------------------------------------------------

def _subscript_index(node):
    sl = node.slice
    if isinstance(sl, ast.Index):  # py < 3.9
        sl = sl.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
        return sl.value, sl
    return None, None


def _rule_fix_wrong_tuple_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    try:
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
               and node.func.id == "unique_day" and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Subscript):
                    idx, idx_node = _subscript_index(arg0)
                    if idx == 0 and idx_node is not None:
                        edits.append((idx_node, "1"))
        if not edits:
            return []
        new_source = _apply_edits(source, edits)
        if new_source is None or new_source == source:
            return []
        return [new_source]
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 5: premature `return False` inside a search loop that should keep
# looking at remaining candidates
# ----------------------------------------------------------------------

def _rule_remove_premature_false_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    try:
        _add_parents(tree)
        if_edits = []
        append_edits = []  # (func, text_to_append)
        seen_funcs = set()

        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            body = node.body
            orelse = node.orelse
            if len(body) == 1 and isinstance(body[0], ast.Return) and _is_bool_const(body[0].value, True) \
               and len(orelse) == 1 and isinstance(orelse[0], ast.Return) and _is_bool_const(orelse[0].value, False):
                func = _enclosing(node, ast.FunctionDef)
                forloop = _enclosing(node, ast.For)
                if func is None or forloop is None:
                    continue
                ts, te = _span(source, node.test)
                test_text = source[ts:te]
                indent = " " * body[0].col_offset
                new_if_text = "if %s:\n%sreturn True" % (test_text, indent)
                if_edits.append((node, new_if_text))

                if id(func) not in seen_funcs:
                    last = func.body[-1] if func.body else None
                    needs_append = not (isinstance(last, ast.Return) and _is_bool_const(last.value, False))
                    if needs_append and func.body and func.body[-1] is forloop:
                        indent2 = " " * forloop.col_offset
                        append_edits.append((forloop, "\n%sreturn False" % indent2))
                    seen_funcs.add(id(func))

        if not if_edits:
            return []

        spans = []
        for n, text in if_edits:
            s, e = _span(source, n)
            spans.append((s, e, text))
        for n, text in append_edits:
            s, e = _span(source, n)
            spans.append((e, e, text))

        spans.sort(key=lambda x: x[0], reverse=True)
        out = source
        for s, e, text in spans:
            out = out[:s] + text + out[e:]
        if out == source:
            return []
        return [out]
    except Exception:
        return []


# ----------------------------------------------------------------------
# Rule 6: lowercase boolean literal typo (true/false -> True/False)
# ----------------------------------------------------------------------

def _rule_fix_lowercase_bool(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    try:
        edits = []
        mapping = {"true": "True", "false": "False", "null": "None"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in mapping:
                edits.append((node, mapping[node.id]))
        if not edits:
            return []
        new_source = _apply_edits(source, edits)
        if new_source is None or new_source == source:
            return []
        return [new_source]
    except Exception:
        return []


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="rename_undefined_name_to_unused_param",
                apply=_rule_unused_param_rename,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="rename_typo_function_call",
                apply=_rule_typo_call_rename,
                symptoms=("err:NameError", "wrong"),
            ),
            Rule(
                name="fix_uniqueness_boundary",
                apply=_rule_fix_uniqueness_boundary,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_wrong_tuple_index_in_unique_day_call",
                apply=_rule_fix_wrong_tuple_index,
                symptoms=("wrong",),
            ),
            Rule(
                name="remove_premature_false_return_in_loop",
                apply=_rule_remove_premature_false_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_lowercase_bool_literal",
                apply=_rule_fix_lowercase_bool,
                symptoms=("err:NameError",),
            ),
        ]