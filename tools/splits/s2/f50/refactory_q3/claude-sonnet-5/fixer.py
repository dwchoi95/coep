"""
Repair module for the 'remove_extras' duplicate-elimination assignment.

Each Rule below targets one narrow, structural misconception observed in
student submissions. Rules operate by locating an AST node (or a small
cluster of related nodes) and splicing a textual replacement into the
*original* source text, leaving everything else untouched. Several
misconceptions require more than one rule to fully resolve; the search
harness is expected to apply rules repeatedly/in combination.
"""

import ast
import builtins as _builtins

from src.core.repair import Rule


# ----------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------

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


def _parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node


def _enclosing_function(node):
    cur = node
    while hasattr(cur, "_parent"):
        cur = cur._parent
        if isinstance(cur, ast.FunctionDef):
            return cur
    return None


def _enclosing_for(node):
    cur = node
    while hasattr(cur, "_parent"):
        cur = cur._parent
        if isinstance(cur, ast.For):
            return cur
    return None


def _unwrap_index(sl):
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _safe(fn):
    def wrapped(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapped


_BUILTIN_NAMES = set(dir(_builtins)) | {"True", "False", "None"}


def _find_list_tuple_init(func, name):
    for n in ast.walk(func):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
           and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name:
            if isinstance(n.value, ast.List):
                return "list"
            if isinstance(n.value, ast.Tuple):
                return "tuple"
    return None


def _find_accumulator(func):
    candidates = []
    for n in ast.walk(func):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
           and isinstance(n.targets[0], ast.Name) \
           and isinstance(n.value, (ast.List, ast.Tuple)) and not n.value.elts:
            candidates.append(n.targets[0].id)
    appended = set()
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
           and n.func.attr in ("append", "extend") and isinstance(n.func.value, ast.Name):
            appended.add(n.func.value.id)
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            appended.add(n.target.id)
    for name in candidates:
        if name in appended:
            return name
    return None


def _levenshtein(a, b):
    if a == b:
        return 0
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            cur = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[lb]


def _normalize(name):
    return name.lower().replace("_", "")


def _name_distance(a, b):
    na, nb = _normalize(a), _normalize(b)
    if na == nb:
        return 0
    if na in nb or nb in na:
        return abs(len(na) - len(nb))
    return _levenshtein(na, nb)


def _collect_assigned_names(func):
    names = set(a.arg for a in func.args.args)
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(n, ast.AugAssign):
            if isinstance(n.target, ast.Name):
                names.add(n.target.id)
        elif isinstance(n, ast.For):
            for sub in ast.walk(n.target):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
        elif isinstance(n, ast.comprehension):
            for sub in ast.walk(n.target):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
    return names


# ----------------------------------------------------------------------
# Rule 1: iterating over the builtin name `list` instead of the parameter
# ----------------------------------------------------------------------

@_safe
def fix_list_builtin_iter(source):
    tree = _parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
            func = _enclosing_function(node)
            if func is None or not func.args.args:
                continue
            param = func.args.args[0].arg
            if param == "list":
                continue
            out.append(_splice(source, node.iter, param))
    return out


# ----------------------------------------------------------------------
# Rule 2: undefined-name typo / mis-reference repair
# ----------------------------------------------------------------------

@_safe
def fix_undefined_name(source):
    tree = _parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    module_defined = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            module_defined.add(n.name)
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                module_defined.add(a.asname or a.name)
        if isinstance(n, ast.Import):
            for a in n.names:
                module_defined.add((a.asname or a.name).split(".")[0])

    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        local_assigned = _collect_assigned_names(func)
        defined = local_assigned | module_defined | _BUILTIN_NAMES
        undefined_nodes = {}
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in defined:
                    undefined_nodes.setdefault(n.id, []).append(n)

        for uid, nodes in undefined_nodes.items():
            candidate = None
            best = None
            for dname in local_assigned:
                if dname == uid or dname in module_defined:
                    continue
                d = _name_distance(uid, dname)
                if d <= 4 and (best is None or d < best):
                    best = d
                    candidate = dname
            if candidate is None:
                enclosing_for = _enclosing_for(nodes[0])
                if enclosing_for is not None and isinstance(enclosing_for.target, ast.Name):
                    cand = enclosing_for.target.id
                    if cand != uid:
                        candidate = cand
            if candidate is None:
                continue
            spans = sorted((_span(source, n) for n in nodes), key=lambda x: x[0], reverse=True)
            new_src = source
            for s, e in spans:
                new_src = new_src[:s] + candidate + new_src[e:]
            out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 3: for-loop target shadows the parameter or the accumulator
# ----------------------------------------------------------------------

@_safe
def fix_for_loop_shadow_swap(source):
    tree = _parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    blocks = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            blocks.append(body)
    for body in blocks:
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Name) \
               and isinstance(a.value, (ast.List, ast.Tuple)) and not a.value.elts \
               and isinstance(b, ast.For):
                acc_name = a.targets[0].id
                func = _enclosing_function(b)
                if func is None or not func.args.args:
                    continue
                param_name = func.args.args[0].arg
                tgt, itr = b.target, b.iter
                if not isinstance(tgt, ast.Name) or not isinstance(itr, ast.Name):
                    continue
                if tgt.id not in (acc_name, param_name):
                    continue
                counts = {}
                for n in ast.walk(b):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                        if n.id not in (acc_name, param_name, tgt.id) and n.id not in _BUILTIN_NAMES:
                            counts[n.id] = counts.get(n.id, 0) + 1
                if not counts:
                    continue
                body_var = max(counts, key=counts.get)
                new_iter_text = param_name if itr.id == acc_name else itr.id
                ts, _te = _span(source, tgt)
                _is_, ie = _span(source, itr)
                replacement = f"{body_var} in {new_iter_text}"
                out.append(source[:ts] + replacement + source[ie:])
    return out


# ----------------------------------------------------------------------
# Rule 4: membership/count test performed against source list, not acc
# ----------------------------------------------------------------------

@_safe
def fix_membership_against_source(source):
    tree = _parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        cont_node = None
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            op = test.ops[0]
            if isinstance(op, (ast.In, ast.NotIn)):
                comp = test.comparators[0]
                if isinstance(comp, ast.Name):
                    cont_node = comp
            elif isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)):
                left = test.left
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) \
                   and left.func.attr == "count" and isinstance(left.func.value, ast.Name):
                    cont_node = left.func.value
        if cont_node is None:
            continue
        enclosing_for = _enclosing_for(node)
        if enclosing_for is None or not isinstance(enclosing_for.iter, ast.Name):
            continue
        src_name = enclosing_for.iter.id
        if cont_node.id != src_name:
            continue
        acc_name = None
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
               and n.func.attr in ("append", "extend") and isinstance(n.func.value, ast.Name):
                if n.func.value.id != src_name:
                    acc_name = n.func.value.id
                    break
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id != src_name:
                acc_name = n.target.id
                break
        if acc_name is None:
            continue
        out.append(_splice(source, cont_node, acc_name))
    return out


# ----------------------------------------------------------------------
# Rule 5: `acc += item` (or `acc += acc + item`) without sequence wrapping
# ----------------------------------------------------------------------

@_safe
def fix_augassign_bare_item(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(func):
            if not (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                    and isinstance(node.target, ast.Name)):
                continue
            value = node.value
            to_wrap = value
            if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add) \
               and isinstance(value.left, ast.Name) and value.left.id == node.target.id:
                to_wrap = value.right
            if isinstance(to_wrap, (ast.List, ast.Tuple)):
                continue
            kind = _find_list_tuple_init(func, node.target.id)
            if kind is None:
                continue
            vs, ve = _span(source, to_wrap)
            val_text = source[vs:ve]
            new_text = f"[{val_text}]" if kind == "list" else f"({val_text},)"
            out.append(_splice(source, value, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 6: `X = X.append(y)` (or augmented) capturing None return value
# ----------------------------------------------------------------------

@_safe
def fix_self_append_assignment(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
               and val.func.attr in ("append", "extend", "insert", "remove"):
                vs, ve = _span(source, val)
                out.append(_splice(source, node, source[vs:ve]))
    return out


# ----------------------------------------------------------------------
# Rule 7: subscript used instead of a method/builtin call
# ----------------------------------------------------------------------

_CALLABLE_ATTRS = {"append", "count", "insert", "remove", "extend", "index", "pop"}
_CALLABLE_BUILTINS = {"len", "list", "str", "int", "set", "tuple"}


@_safe
def fix_subscript_as_call(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        val = node.value
        obj_text = None
        if isinstance(val, ast.Attribute) and val.attr in _CALLABLE_ATTRS:
            vs, ve = _span(source, val)
            obj_text = source[vs:ve]
        elif isinstance(val, ast.Name) and val.id in _CALLABLE_BUILTINS:
            vs, ve = _span(source, val)
            obj_text = source[vs:ve]
        if obj_text is None:
            continue
        sl = _unwrap_index(node.slice)
        ss, se = _span(source, sl)
        arg_text = source[ss:se]
        out.append(_splice(source, node, f"{obj_text}({arg_text})"))
    return out


# ----------------------------------------------------------------------
# Rule 8: `obj.insert(len(x) - 1, item)` off-by-one
# ----------------------------------------------------------------------

@_safe
def fix_insert_len_minus_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr == "insert" and node.args:
            first = node.args[0]
            if isinstance(first, ast.BinOp) and isinstance(first.op, ast.Sub) \
               and isinstance(first.right, ast.Constant) and first.right.value == 1:
                left = first.left
                len_text = None
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                    ls, le = _span(source, left)
                    len_text = source[ls:le]
                elif isinstance(left, ast.Subscript) and isinstance(left.value, ast.Name) and left.value.id == "len":
                    sl = _unwrap_index(left.slice)
                    ss, se = _span(source, sl)
                    len_text = f"len({source[ss:se]})"
                if len_text:
                    out.append(_splice(source, first, len_text))
    return out


# ----------------------------------------------------------------------
# Rule 9: bare attribute access meant to be a zero-arg method call
# ----------------------------------------------------------------------

_ZERO_ARG_METHODS = {"pop", "reverse", "sort", "clear"}


@_safe
def fix_missing_call_parens(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute):
            if node.value.attr in _ZERO_ARG_METHODS:
                vs, ve = _span(source, node.value)
                out.append(_splice(source, node.value, source[vs:ve] + "()"))
    return out


# ----------------------------------------------------------------------
# Rule 10: `if x in acc: acc.append(x)` polarity flip
# ----------------------------------------------------------------------

def _appends_to(body, acc):
    for n in body:
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) \
           and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "append" \
           and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == acc:
            return True
    return False


@_safe
def fix_membership_polarity(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.In):
            comp = test.comparators[0]
            if isinstance(comp, ast.Name) and _appends_to(node.body, comp.id):
                ls, le = _span(source, test.left)
                rs, re_ = _span(source, comp)
                new_cmp = source[ls:le] + " not in " + source[rs:re_]
                out.append(_splice(source, test, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule 11: `if x != acc: acc.append(x)` should be membership test
# ----------------------------------------------------------------------

@_safe
def fix_eq_should_be_not_in(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.NotEq):
            comp = test.comparators[0]
            if isinstance(comp, ast.Name) and _appends_to(node.body, comp.id):
                ls, le = _span(source, test.left)
                rs, re_ = _span(source, comp)
                new_cmp = source[ls:le] + " not in " + source[rs:re_]
                out.append(_splice(source, test, new_cmp))
    return out


# ----------------------------------------------------------------------
# Rule 12: spurious early-return in the else branch of a dedup check
# ----------------------------------------------------------------------

@_safe
def fix_early_return_else(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not node.orelse:
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.NotIn)):
            continue
        comp = test.comparators[0]
        if not isinstance(comp, ast.Name):
            continue
        if not _appends_to(node.body, comp.id):
            continue
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return):
            last_body_stmt = node.body[-1]
            _, be = _span(source, last_body_stmt)
            _, ie = _span(source, node)
            out.append(source[:be] + source[ie:])
    return out


# ----------------------------------------------------------------------
# Rule 13: function returns the wrong variable instead of the accumulator
# ----------------------------------------------------------------------

@_safe
def fix_return_to_accumulator(source):
    tree = _parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        acc = _find_accumulator(func)
        if not acc:
            continue
        param_names = {a.arg for a in func.args.args}
        for_targets = {n.target.id for n in ast.walk(func)
                       if isinstance(n, ast.For) and isinstance(n.target, ast.Name)}
        for ret in ast.walk(func):
            if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Name):
                rid = ret.value.id
                if rid != acc and (rid in param_names or rid in for_targets):
                    out.append(_splice(source, ret.value, acc))
    return out


# ----------------------------------------------------------------------
# Rule 14: function builds an accumulator but never returns it
# ----------------------------------------------------------------------

@_safe
def fix_missing_return(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if any(isinstance(n, ast.Return) for n in ast.walk(func)):
            continue
        acc = _find_accumulator(func)
        if not acc or not func.body:
            continue
        last = func.body[-1]
        indent = " " * last.col_offset
        _, e = _span(source, last)
        out.append(source[:e] + f"\n{indent}return {acc}" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 15: `range(len(x) + 1)` off-by-one
# ----------------------------------------------------------------------

@_safe
def fix_range_len_plus_one(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "range" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                left, right = arg.left, arg.right
                if isinstance(right, ast.Constant) and right.value == 1 \
                   and isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                    ls, le = _span(source, left)
                    out.append(_splice(source, arg, source[ls:le]))
    return out


# ----------------------------------------------------------------------
# Rule 16: `lists(...)` typo for `list(...)`
# ----------------------------------------------------------------------

@_safe
def fix_lists_typo(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "lists":
            out.append(_splice(source, node.func, "list"))
    return out


# ----------------------------------------------------------------------
# Rule 17: `set(x)` used for dedup (loses order)
# ----------------------------------------------------------------------

@_safe
def fix_set_loses_order(source):
    tree = _parse(source)
    if tree is None:
        return []
    _add_parents(tree)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
           and node.func.id == "set" and len(node.args) == 1:
            as_, ae = _span(source, node.args[0])
            arg_text = source[as_:ae]
            parent = getattr(node, "_parent", None)
            if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name) and parent.func.id == "list":
                new_text = f"OrderedDict.fromkeys({arg_text})"
            else:
                new_text = f"list(OrderedDict.fromkeys({arg_text}))"
            out.append(_splice(source, node, new_text))
    return out


# ----------------------------------------------------------------------
# Rule 18: using OrderedDict without importing it
# ----------------------------------------------------------------------

@_safe
def fix_missing_ordereddict_import(source):
    tree = _parse(source)
    if tree is None:
        return []
    uses = any(isinstance(n, ast.Name) and n.id == "OrderedDict" for n in ast.walk(tree))
    if not uses:
        return []
    has_import = any(
        isinstance(n, ast.ImportFrom) and n.module == "collections"
        and any(a.name == "OrderedDict" for a in n.names)
        for n in ast.walk(tree)
    )
    if has_import:
        return []
    return [f"from collections import OrderedDict\n{source}"]


# ----------------------------------------------------------------------
# Rule 19: accumulator built as a tuple but a list is expected on return
# ----------------------------------------------------------------------

@_safe
def fix_tuple_return_to_list(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
                kind = _find_list_tuple_init(func, node.value.id)
                if kind == "tuple":
                    vs, ve = _span(source, node.value)
                    out.append(_splice(source, node.value, f"list({source[vs:ve]})"))
    return out


# ----------------------------------------------------------------------
# Rule 20: boolean "seen" flag not reset inside the outer loop
# ----------------------------------------------------------------------

@_safe
def fix_flag_not_reset(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    blocks = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            blocks.append(body)
    for body in blocks:
        for i in range(len(body) - 1):
            a, b = body[i], body[i + 1]
            if isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Name) \
               and isinstance(a.value, ast.Constant) and isinstance(a.value.value, bool) \
               and isinstance(b, ast.For) and b.body:
                flag = a.targets[0].id
                reads = writes = 0
                for n in ast.walk(b):
                    if isinstance(n, ast.Name) and n.id == flag:
                        if isinstance(n.ctx, ast.Load):
                            reads += 1
                        elif isinstance(n.ctx, ast.Store):
                            writes += 1
                if reads >= 1 and writes >= 1:
                    first_stmt = b.body[0]
                    indent = " " * first_stmt.col_offset
                    a_s, a_e = _span(source, a)
                    nl = 1 if source[a_e:a_e + 1] == "\n" else 0
                    fs, _fe = _span(source, first_stmt)
                    new_src = (source[:a_s] + source[a_e + nl:fs]
                               + f"{flag} = True\n{indent}" + source[fs:])
                    out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule 21: parameter "called" like a function to initialize accumulator
# ----------------------------------------------------------------------

@_safe
def fix_param_called_as_function(source):
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        param_names = {a.arg for a in func.args.args}
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
               and isinstance(node.value.func, ast.Name) and node.value.func.id in param_names:
                out.append(_splice(source, node.value, "[]"))
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="list_builtin_as_iterable", apply=fix_list_builtin_iter,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="undefined_name_typo", apply=fix_undefined_name,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="for_loop_shadow_swap", apply=fix_for_loop_shadow_swap,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="membership_against_source_list", apply=fix_membership_against_source,
                 symptoms=("wrong",)),
            Rule(name="augassign_bare_item_needs_wrapping", apply=fix_augassign_bare_item,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="self_append_assignment", apply=fix_self_append_assignment,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="subscript_should_be_call", apply=fix_subscript_as_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="insert_len_minus_one_offbyone", apply=fix_insert_len_minus_one,
                 symptoms=("wrong",)),
            Rule(name="missing_call_parens", apply=fix_missing_call_parens,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="membership_polarity_flip", apply=fix_membership_polarity,
                 symptoms=("wrong",)),
            Rule(name="eq_should_be_not_in", apply=fix_eq_should_be_not_in,
                 symptoms=("wrong",)),
            Rule(name="early_return_in_dedup_else", apply=fix_early_return_else,
                 symptoms=("wrong",)),
            Rule(name="return_wrong_variable", apply=fix_return_to_accumulator,
                 symptoms=("wrong",)),
            Rule(name="missing_return_statement", apply=fix_missing_return,
                 symptoms=("wrong",)),
            Rule(name="range_len_plus_one_offbyone", apply=fix_range_len_plus_one,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="lists_typo_for_list", apply=fix_lists_typo,
                 symptoms=("err:NameError",)),
            Rule(name="set_loses_order", apply=fix_set_loses_order,
                 symptoms=("wrong",)),
            Rule(name="missing_ordereddict_import", apply=fix_missing_ordereddict_import,
                 symptoms=("err:NameError",)),
            Rule(name="tuple_accumulator_returned_as_list", apply=fix_tuple_return_to_list,
                 symptoms=("wrong",)),
            Rule(name="flag_not_reset_in_outer_loop", apply=fix_flag_not_reset,
                 symptoms=("wrong",)),
            Rule(name="param_called_as_function", apply=fix_param_called_as_function,
                 symptoms=("err:TypeError",)),
        ]