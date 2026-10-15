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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _first_param(fn):
    if fn.args.args:
        return fn.args.args[0].arg
    return None


# ---------------------------------------------------------------------------
# Rule: comparing against the wrong (original) list instead of the
# accumulator, e.g. `if i not in lst:` instead of `if i not in new_lst:`.
# ---------------------------------------------------------------------------
def _fix_membership_against_self(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                and isinstance(node.iter, ast.Name)):
            continue
        loop_var = node.target.id
        list_name = node.iter.id
        for sub in node.body:
            if not isinstance(sub, ast.If):
                continue
            test = sub.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.NotIn)):
                continue
            left = test.left
            comp = test.comparators[0]
            if not (isinstance(left, ast.Name) and left.id == loop_var
                    and isinstance(comp, ast.Name) and comp.id == list_name):
                continue
            acc_name = None
            for s2 in sub.body:
                if isinstance(s2, ast.Expr) and isinstance(s2.value, ast.Call):
                    f = s2.value.func
                    if isinstance(f, ast.Attribute) and f.attr == "append" \
                            and isinstance(f.value, ast.Name):
                        acc_name = f.value.id
                elif isinstance(s2, ast.AugAssign) and isinstance(s2.target, ast.Name):
                    acc_name = s2.target.id
                elif isinstance(s2, ast.Assign) and len(s2.targets) == 1 \
                        and isinstance(s2.targets[0], ast.Name):
                    acc_name = s2.targets[0].id
            if acc_name and acc_name != list_name:
                s_, e_ = _span(source, comp)
                out.append(source[:s_] + acc_name + source[e_:])
    return out


# ---------------------------------------------------------------------------
# Rule: `acc += element` where element is not wrapped in a list, so the
# augmented assignment either does the wrong thing or raises a TypeError.
# ---------------------------------------------------------------------------
def _wrap_aug_add_element(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            val = node.value
            if isinstance(val, (ast.List, ast.Tuple)):
                continue
            s_, e_ = _span(source, val)
            new_text = "[" + source[s_:e_] + "]"
            out.append(_splice(source, val, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: a singleton tuple `(x,)` used where a single-element list `[x]` is
# needed (breaks `list + tuple` concatenation, or is just stylistically the
# misconception "tuple instead of list").
# ---------------------------------------------------------------------------
def _singleton_tuple_to_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 1:
            inner_s, inner_e = _span(source, node.elts[0])
            new_text = "[" + source[inner_s:inner_e] + "]"
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: accumulator initialised from the input list itself (`lst[0]`,
# `lst(0)`, etc.) instead of an empty container.
# ---------------------------------------------------------------------------
def _fix_bad_accumulator_init(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        param = _first_param(fn)
        if not param:
            continue
        for stmt in fn.body:
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            val = stmt.value
            bad = False
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
                    and val.func.id == param:
                bad = True
            elif isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) \
                    and val.value.id == param:
                bad = True
            if bad:
                out.append(_splice(source, val, "[]"))
    return out


# ---------------------------------------------------------------------------
# Rule: `acc.insert(0, x)` reverses order; should be `acc.append(x)`.
# ---------------------------------------------------------------------------
def _fix_insert_zero(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "insert" and len(node.args) == 2:
            first_arg = node.args[0]
            is_zero = isinstance(first_arg, ast.Constant) and first_arg.value == 0
            if not is_zero:
                continue
            obj_s, obj_e = _span(source, node.func.value)
            elem_s, elem_e = _span(source, node.args[1])
            new_text = source[obj_s:obj_e] + ".append(" + source[elem_s:elem_e] + ")"
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: a `return` statement placed as the last statement *inside* a loop
# instead of after it, causing the function to bail out after one iteration.
# ---------------------------------------------------------------------------
def _dedent_trailing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for stmt in fn.body:
            if not isinstance(stmt, (ast.For, ast.While)):
                continue
            body = stmt.body
            if not body:
                continue
            last = body[-1]
            if isinstance(last, ast.Return) and last.col_offset > stmt.col_offset:
                lines = source.splitlines(keepends=True)
                starts = [0]
                for ln in lines:
                    starts.append(starts[-1] + len(ln))
                line_start = starts[last.lineno - 1]
                old_indent_end = line_start + last.col_offset
                new_pad = " " * stmt.col_offset
                new_source = source[:line_start] + new_pad + source[old_indent_end:]
                out.append(new_source)
    return out


# ---------------------------------------------------------------------------
# Fallback rule: the main loop is structurally broken (mutates the input
# list it iterates over, misuses `list.remove`'s return value, forgets to
# call `.copy()`, nests nested index loops with `!=` comparisons, etc).
# Replace just that loop with the canonical "seen before" dedup loop,
# leaving any later statements in place (now dead code, but syntactically
# harmless since the new loop always returns).
# ---------------------------------------------------------------------------
_MUTATING_METHODS = {"remove", "pop", "insert", "append", "count"}


def _contains_name(node, name):
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == name:
            return True
    return False


def _loop_is_broken(loop, param_name):
    called_func_ids = set()
    for n in ast.walk(loop):
        if isinstance(n, ast.Call):
            called_func_ids.add(id(n.func))
    for n in ast.walk(loop):
        if n is loop:
            continue
        if isinstance(n, (ast.For, ast.While)):
            return True
        if isinstance(n, ast.Compare):
            if any(isinstance(op, ast.NotEq) for op in n.ops):
                return True
        if isinstance(n, ast.Attribute):
            if n.attr == "copy" and id(n) not in called_func_ids:
                return True
            if n.attr in _MUTATING_METHODS and param_name is not None \
                    and _contains_name(n.value, param_name):
                return True
    return False


def _rebuild_broken_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        param = _first_param(fn)
        if not param:
            continue
        for stmt in fn.body:
            if not isinstance(stmt, (ast.For, ast.While)):
                continue
            if not _loop_is_broken(stmt, param):
                continue
            pad = " " * stmt.col_offset
            new_text = (
                "new_list = []\n"
                + pad + "for item in " + param + ":\n"
                + pad + "    if item not in new_list:\n"
                + pad + "        new_list.append(item)\n"
                + pad + "return new_list"
            )
            out.append(_splice(source, stmt, new_text))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="membership_check_against_original_list",
                apply=_fix_membership_against_self,
                symptoms=("wrong",),
            ),
            Rule(
                name="aug_add_missing_list_wrap",
                apply=_wrap_aug_add_element,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="singleton_tuple_should_be_list",
                apply=_singleton_tuple_to_list,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="accumulator_initialised_from_input",
                apply=_fix_bad_accumulator_init,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="insert_zero_reverses_order",
                apply=_fix_insert_zero,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_trapped_inside_loop",
                apply=_dedent_trailing_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="rebuild_structurally_broken_loop",
                apply=_rebuild_broken_loop,
                symptoms=("wrong", "timeout", "err:TypeError", "err:AttributeError", "err:NameError"),
            ),
        ]