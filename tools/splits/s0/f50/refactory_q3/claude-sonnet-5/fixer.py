"""
Repair module for the "Duplicate elimination" (remove_extras) assignment.

Each rule below targets one recurring misconception observed in buggy
submissions and produces small, local, AST-span-based edits of the original
source text (never a full rewrite).
"""

import ast
import builtins

from src.core.repair import Rule


# --------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------

def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


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


def _apply_splices(source, replacements):
    """replacements: list of (node, new_text). Applies right-to-left."""
    reps = []
    for node, text in replacements:
        s, e = _span(source, node)
        reps.append((s, e, text))
    reps.sort(key=lambda t: t[0], reverse=True)
    out = source
    for s, e, text in reps:
        out = out[:s] + text + out[e:]
    return out


def _safe(fn):
    def wrapper(source):
        try:
            return fn(source)
        except Exception:
            return []
    wrapper.__name__ = getattr(fn, "__name__", "rule")
    return wrapper


BUILTIN_NAMES = set(dir(builtins)) | {"True", "False", "None"}


def _top_funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _get_first_param(func):
    if func.args.args:
        return func.args.args[0].arg
    return None


def _slice_expr(s):
    idx_cls = getattr(ast, "Index", None)
    if idx_cls is not None and isinstance(s, idx_cls):
        return s.value
    return s


def _target_names(t):
    out = []
    if isinstance(t, ast.Name):
        out.append(t.id)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for e in t.elts:
            out.extend(_target_names(e))
    return out


def _collect_defined_names(func):
    names = set()
    for a in func.args.args:
        names.add(a.arg)
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                names.update(_target_names(t))
        elif isinstance(node, ast.AugAssign):
            names.update(_target_names(node.target))
        elif isinstance(node, ast.For):
            names.update(_target_names(node.target))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.comprehension):
            names.update(_target_names(node.target))
    return names


def _all_accumulators(func):
    cands = []
    for node in ast.walk(func):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.List) and len(node.value.elts) == 0):
            cands.append((node.lineno, node.col_offset, node.targets[0].id))
    cands.sort()
    return [c[2] for c in cands]


def _find_accumulator(func):
    accs = _all_accumulators(func)
    return accs[0] if accs else None


# --------------------------------------------------------------------------
# Rule: bare builtin `list` used instead of the parameter name
# --------------------------------------------------------------------------

@_safe
def _fix_builtin_list_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    call_func_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            call_func_ids.add(id(node.func))
    reps = []
    for func in _top_funcs(tree):
        param = _get_first_param(func)
        if not param:
            continue
        for node in ast.walk(func):
            if (isinstance(node, ast.Name) and node.id == "list"
                    and isinstance(node.ctx, ast.Load)
                    and id(node) not in call_func_ids):
                reps.append((node, param))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: subscript used where a method call was meant: X.count[y] -> X.count(y)
# --------------------------------------------------------------------------

_METH_NAMES = {"count", "append", "extend", "remove", "insert", "index", "pop"}


@_safe
def _fix_subscript_as_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr in _METH_NAMES):
            idx = _slice_expr(node.slice)
            vs, ve = _span(source, node.value)
            iss, ie = _span(source, idx)
            new_text = source[vs:ve] + "(" + source[iss:ie] + ")"
            reps.append((node, new_text))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: `var == []` (mistaken == for init assignment)
# --------------------------------------------------------------------------

@_safe
def _fix_double_eq_assign(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if (len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq)
                    and isinstance(cmp.comparators[0], ast.List)):
                ls, le = _span(source, cmp.left)
                rs, re_ = _span(source, cmp.comparators[0])
                between = source[le:rs]
                if "==" in between:
                    new_between = between.replace("==", "=", 1)
                    new_text = source[ls:le] + new_between + source[rs:re_]
                    reps.append((node, new_text))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: .extend(scalar) should be .append(scalar)
# --------------------------------------------------------------------------

@_safe
def _fix_extend_to_append(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "extend" and len(node.args) == 1):
            arg = node.args[0]
            if isinstance(arg, (ast.List, ast.Tuple, ast.Starred, ast.GeneratorExp, ast.Set)):
                continue
            fs, fe = _span(source, node.func)
            text = source[fs:fe]
            if not text.endswith("extend"):
                continue
            new_text = text[: -len("extend")] + "append"
            reps.append((node.func, new_text))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: .insert(0, x) should be .append(x)
# --------------------------------------------------------------------------

@_safe
def _fix_insert_zero(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "insert" and len(node.args) == 2):
            a0 = node.args[0]
            if isinstance(a0, ast.Constant) and a0.value == 0:
                vs, ve = _span(source, node.func.value)
                a1s, a1e = _span(source, node.args[1])
                new_text = source[vs:ve] + ".append(" + source[a1s:a1e] + ")"
                reps.append((node, new_text))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: scalar added to list via += or `x = x + y` instead of wrapping in []
# --------------------------------------------------------------------------

@_safe
def _fix_wrap_scalar_add(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            val = node.value
            if isinstance(val, (ast.List, ast.Tuple)):
                continue
            vs, ve = _span(source, val)
            new_text = "[" + source[vs:ve] + "]"
            reps.append((val, new_text))
        elif (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            val = node.value
            if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                left = val.left
                if isinstance(left, ast.Name) and left.id == node.targets[0].id:
                    right = val.right
                    if isinstance(right, (ast.List, ast.Tuple)):
                        continue
                    rs, re_ = _span(source, right)
                    new_text = "[" + source[rs:re_] + "]"
                    reps.append((right, new_text))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: `in`/`not in` tests against the wrong container
# --------------------------------------------------------------------------

@_safe
def _fix_membership_operands(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _top_funcs(tree):
        acc = _find_accumulator(func)
        if acc is None:
            continue
        reps = []
        for node in ast.walk(func):
            if isinstance(node, ast.For):
                target = node.target
                target_name = target.id if isinstance(target, ast.Name) else None
                iter_name = node.iter.id if isinstance(node.iter, ast.Name) else None
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Compare) and len(sub.ops) == 1
                            and isinstance(sub.ops[0], (ast.In, ast.NotIn))):
                        left = sub.left
                        container = sub.comparators[0]
                        if (isinstance(left, ast.Name) and iter_name
                                and left.id == iter_name and target_name
                                and left.id != target_name):
                            reps.append((left, target_name))
                        if isinstance(container, ast.Name) and container.id != acc:
                            reps.append((container, acc))
        if reps:
            cand = _apply_splices(source, reps)
            if cand != source:
                out.append(cand)
    return out


# --------------------------------------------------------------------------
# Rule: undefined name used, rename to the sole list accumulator
# --------------------------------------------------------------------------

@_safe
def _fix_undefined_to_accumulator(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    module_funcs = {n.name for n in _top_funcs(tree)}
    for func in _top_funcs(tree):
        defined = _collect_defined_names(func)
        accs = _all_accumulators(func)
        if len(accs) != 1:
            continue
        acc = accs[0]
        reps = []
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id == acc:
                    continue
                if node.id in defined:
                    continue
                if node.id in BUILTIN_NAMES:
                    continue
                if node.id in module_funcs:
                    continue
                reps.append((node, acc))
        if reps:
            cand = _apply_splices(source, reps)
            if cand != source:
                out.append(cand)
    return out


# --------------------------------------------------------------------------
# Rule: undefined accumulator name used but never initialized
# --------------------------------------------------------------------------

@_safe
def _fix_missing_accumulator_init(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _top_funcs(tree):
        if _all_accumulators(func):
            continue
        defined = _collect_defined_names(func)
        for node in ast.walk(func):
            if isinstance(node, ast.For):
                candidates = set()
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr in ("append", "extend")):
                        base = sub.func.value
                        if isinstance(base, ast.Name) and base.id not in defined:
                            candidates.add(base.id)
                    if isinstance(sub, ast.Compare):
                        for op, cmp in zip(sub.ops, sub.comparators):
                            if (isinstance(op, (ast.In, ast.NotIn))
                                    and isinstance(cmp, ast.Name) and cmp.id not in defined):
                                candidates.add(cmp.id)
                if len(candidates) == 1:
                    name = next(iter(candidates))
                    fs, _fe = _span(source, node)
                    line_start = source.rfind("\n", 0, fs) + 1
                    indent = source[line_start:fs]
                    insertion = "%s = []\n%s" % (name, indent)
                    new_source = source[:fs] + insertion + source[fs:]
                    if new_source != source:
                        out.append(new_source)
    return out


# --------------------------------------------------------------------------
# Rule: for-loop target reuses an existing meaningful name instead of binding
# a fresh item variable
# --------------------------------------------------------------------------

@_safe
def _fix_for_target_rename(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _top_funcs(tree):
        param = _get_first_param(func)
        accs = set(_all_accumulators(func))
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                tgt = node.target.id
                if tgt != param and tgt not in accs:
                    continue
                defined = _collect_defined_names(func)
                undefined = []
                seen = set()
                for sub in ast.walk(node):
                    if sub is node.target:
                        continue
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        if sub.id == tgt or sub.id in defined or sub.id in BUILTIN_NAMES:
                            continue
                        if sub.id in seen:
                            continue
                        seen.add(sub.id)
                        undefined.append(sub.id)
                if len(undefined) == 1:
                    cand = _splice(source, node.target, undefined[0])
                    if cand != source:
                        out.append(cand)
    return out


# --------------------------------------------------------------------------
# Rule: for-loop iterates over the accumulator instead of the source list
# --------------------------------------------------------------------------

@_safe
def _fix_for_iter_rename(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _top_funcs(tree):
        param = _get_first_param(func)
        if not param:
            continue
        accs = set(_all_accumulators(func))
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                if node.iter.id in accs and node.iter.id != param:
                    cand = _splice(source, node.iter, param)
                    if cand != source:
                        out.append(cand)
    return out


# --------------------------------------------------------------------------
# Rule: slicing uses the original list where it should use the local copy
# --------------------------------------------------------------------------

@_safe
def _fix_subscript_base_mismatch(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for func in _top_funcs(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                loop_src = node.iter.id
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name)
                            and sub.value.id != loop_src):
                        found = False
                        for inner in ast.walk(sub.slice):
                            if (isinstance(inner, ast.Call)
                                    and isinstance(inner.func, ast.Attribute)
                                    and isinstance(inner.func.value, ast.Name)
                                    and inner.func.value.id == loop_src
                                    and inner.func.attr == "index"):
                                found = True
                        if found:
                            reps.append((sub.value, loop_src))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: move an unconditional index increment into the else branch
# --------------------------------------------------------------------------

@_safe
def _fix_move_increment_else(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.While, ast.For)):
            body = node.body
            for idx in range(len(body) - 1):
                stmt = body[idx]
                nxt = body[idx + 1]
                if not (isinstance(stmt, ast.If) and not stmt.orelse
                        and isinstance(nxt, ast.AugAssign) and isinstance(nxt.op, ast.Add)):
                    continue
                mutates = any(isinstance(s, ast.Assign) for s in stmt.body) or any(
                    isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                    and isinstance(s.value.func, ast.Attribute)
                    and s.value.func.attr in ("remove", "pop", "insert")
                    for s in stmt.body
                )
                if not mutates:
                    continue
                ns, ne = _span(source, nxt)
                incr_text = source[ns:ne]
                line_start = source.rfind("\n", 0, ns) + 1
                remove_end = ne
                if remove_end < len(source) and source[remove_end] == "\n":
                    remove_end += 1
                new_source = source[:line_start] + source[remove_end:]
                fs, fe = _span(source, stmt)
                if_line_start = source.rfind("\n", 0, fs) + 1
                if_indent = source[if_line_start:fs]
                insertion = "\n%selse:\n%s    %s" % (if_indent, if_indent, incr_text)
                new_source = new_source[:fe] + insertion + new_source[fe:]
                if new_source != source:
                    out.append(new_source)
    return out


# --------------------------------------------------------------------------
# Rule: missing `from collections import OrderedDict`
# --------------------------------------------------------------------------

@_safe
def _fix_missing_import_ordereddict(source):
    tree = _parse(source)
    if tree is None:
        return []
    uses_od = False
    has_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "OrderedDict":
            uses_od = True
        if isinstance(node, ast.ImportFrom) and node.module == "collections":
            for alias in node.names:
                if alias.name == "OrderedDict":
                    has_import = True
    if uses_od and not has_import:
        new_source = "from collections import OrderedDict\n" + source
        return [new_source]
    return []


# --------------------------------------------------------------------------
# Rule: OrderedDict.fromkeys(...) not wrapped in list(...)
# --------------------------------------------------------------------------

@_safe
def _fix_wrap_fromkeys(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                    and val.func.attr == "fromkeys"):
                vs, ve = _span(source, val)
                new_text = "list(" + source[vs:ve] + ")"
                reps.append((val, new_text))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: list(set(x)) doesn't preserve order -> list(dict.fromkeys(x))
# --------------------------------------------------------------------------

@_safe
def _fix_set_to_fromkeys(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "list" and len(node.args) == 1):
            inner = node.args[0]
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == "set" and len(inner.args) == 1):
                reps.append((inner.func, "dict.fromkeys"))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: `x != acc` / `x == acc` used instead of `x not in acc` / `x in acc`
# --------------------------------------------------------------------------

@_safe
def _fix_eq_to_in(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _top_funcs(tree):
        accs = set(_all_accumulators(func))
        if not accs:
            continue
        reps = []
        for node in ast.walk(func):
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], (ast.Eq, ast.NotEq))):
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Name) and right.id in accs:
                    ls, le = _span(source, left)
                    rs, re_ = _span(source, right)
                    op_text = " not in " if isinstance(node.ops[0], ast.NotEq) else " in "
                    new_text = source[ls:le] + op_text + source[rs:re_]
                    reps.append((node, new_text))
        if reps:
            cand = _apply_splices(source, reps)
            if cand != source:
                out.append(cand)
    return out


# --------------------------------------------------------------------------
# Rule: `x = x.append(y)` (reassigning from a void-returning method)
# --------------------------------------------------------------------------

@_safe
def _fix_assign_void_method(source):
    tree = _parse(source)
    if tree is None:
        return []
    reps = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                    and val.func.attr in ("append", "extend", "insert", "sort", "reverse", "remove", "pop")):
                base = val.func.value
                if isinstance(base, ast.Name) and base.id == node.targets[0].id:
                    vs, ve = _span(source, val)
                    reps.append((node, source[vs:ve]))
    if not reps:
        return []
    cand = _apply_splices(source, reps)
    return [cand] if cand != source else []


# --------------------------------------------------------------------------
# Rule: return statement incorrectly indented inside the accumulation loop
# --------------------------------------------------------------------------

@_safe
def _fix_dedent_return_in_loop(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            body = node.body
            if body and isinstance(body[-1], ast.Return):
                ret = body[-1]
                fs, _fe = _span(source, node)
                for_line_start = source.rfind("\n", 0, fs) + 1
                for_indent = source[for_line_start:fs]
                ret_s, _ret_e = _span(source, ret)
                ret_line_start = source.rfind("\n", 0, ret_s) + 1
                ret_indent = source[ret_line_start:ret_s]
                if len(ret_indent) > len(for_indent):
                    new_source = source[:ret_line_start] + for_indent + source[ret_s:]
                    if new_source != source:
                        out.append(new_source)
    return out


# --------------------------------------------------------------------------
# Rule: function never returns the accumulated result
# --------------------------------------------------------------------------

@_safe
def _fix_missing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in _top_funcs(tree):
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(func))
        if has_return:
            continue
        accs = _all_accumulators(func)
        if len(accs) != 1:
            continue
        acc = accs[0]
        if not func.body:
            continue
        indent = " " * func.body[0].col_offset
        last = func.body[-1]
        _, fe = _span(source, last)
        insertion = "\n%sreturn %s" % (indent, acc)
        new_source = source[:fe] + insertion + source[fe:]
        if new_source != source:
            out.append(new_source)
    return out


# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="builtin_list_name_misuse",
                 apply=_fix_builtin_list_name,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="subscript_used_as_call",
                 apply=_fix_subscript_as_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="double_eq_instead_of_assign",
                 apply=_fix_double_eq_assign,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="extend_scalar_should_be_append",
                 apply=_fix_extend_to_append,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="insert_zero_should_be_append",
                 apply=_fix_insert_zero,
                 symptoms=("wrong",)),
            Rule(name="wrap_scalar_added_to_list",
                 apply=_fix_wrap_scalar_add,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="membership_test_wrong_container",
                 apply=_fix_membership_operands,
                 symptoms=("wrong",)),
            Rule(name="undefined_name_to_sole_accumulator",
                 apply=_fix_undefined_to_accumulator,
                 symptoms=("err:NameError",)),
            Rule(name="missing_accumulator_initialization",
                 apply=_fix_missing_accumulator_init,
                 symptoms=("err:NameError",)),
            Rule(name="for_target_reuses_other_name",
                 apply=_fix_for_target_rename,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="for_iterates_over_accumulator",
                 apply=_fix_for_iter_rename,
                 symptoms=("wrong", "timeout")),
            Rule(name="slice_base_mismatch_with_loop_copy",
                 apply=_fix_subscript_base_mismatch,
                 symptoms=("wrong",)),
            Rule(name="increment_outside_else_in_remove_loop",
                 apply=_fix_move_increment_else,
                 symptoms=("wrong", "timeout")),
            Rule(name="missing_ordereddict_import",
                 apply=_fix_missing_import_ordereddict,
                 symptoms=("err:NameError",)),
            Rule(name="fromkeys_not_wrapped_in_list",
                 apply=_fix_wrap_fromkeys,
                 symptoms=("wrong",)),
            Rule(name="set_loses_order_use_fromkeys",
                 apply=_fix_set_to_fromkeys,
                 symptoms=("wrong",)),
            Rule(name="eq_neq_should_be_in_notin",
                 apply=_fix_eq_to_in,
                 symptoms=("wrong",)),
            Rule(name="reassign_from_void_method",
                 apply=_fix_assign_void_method,
                 symptoms=("wrong", "err:AttributeError")),
            Rule(name="return_indented_inside_loop",
                 apply=_fix_dedent_return_in_loop,
                 symptoms=("wrong",)),
            Rule(name="missing_return_statement",
                 apply=_fix_missing_return,
                 symptoms=("wrong",)),
        ]