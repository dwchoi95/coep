import ast
import builtins
import difflib

from src.core.repair import Rule


# ----------------------------------------------------------------------------
# Generic span helpers
# ----------------------------------------------------------------------------

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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _indent_at(source, node):
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[:len(line) - len(line.lstrip())]


def _multi_splice(source, replacements):
    """Apply several (start, end, text) edits to source, rightmost first."""
    reps = sorted(replacements, key=lambda r: r[0], reverse=True)
    for s, e, text in reps:
        source = source[:s] + text + source[e:]
    return source


def _safe(fn):
    def wrapped(source):
        try:
            out = fn(source)
        except Exception:
            return []
        if not out:
            return []
        return [o for o in out if o != source]
    return wrapped


# ----------------------------------------------------------------------------
# Rule implementations
# ----------------------------------------------------------------------------

_BUILTINS = set(dir(builtins))
_SHADOW_BUILTINS = {'list', 'str', 'dict', 'set', 'tuple'}
_METHOD_NAMES = {'append', 'count', 'remove', 'pop', 'extend', 'index'}


def _defined_names(func):
    names = {a.arg for a in func.args.args}
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return names


def _similar(a, b):
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.75
    return difflib.SequenceMatcher(None, a, b).ratio()


def fix_undefined_name_typo(source):
    """Rename an undefined identifier to the closest defined local name."""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        defined = _defined_names(func)
        undefined = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in defined or node.id in _BUILTINS:
                    continue
                undefined.setdefault(node.id, []).append(node)
        if not undefined:
            continue
        replacements = []
        changed = False
        for bad_name, nodes in undefined.items():
            best, best_score = None, 0.0
            for cand in defined:
                sc = _similar(bad_name, cand)
                if sc > best_score:
                    best_score, best = sc, cand
            if best is not None and best_score >= 0.6:
                changed = True
                for node in nodes:
                    s, e = _span(source, node)
                    replacements.append((s, e, best))
        if changed:
            out.append(_multi_splice(source, replacements))
    return out


def fix_shadowed_builtin_iter(source):
    """for X in list:  ->  for X in <the sole parameter>:"""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = [a.arg for a in func.args.args]
        if len(params) != 1:
            continue
        param = params[0]
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                if node.iter.id in _SHADOW_BUILTINS and node.iter.id != param:
                    out.append(_splice(source, node.iter, param))
    return out


def fix_boolop_for_iter(source):
    """for i in lst and not result:  ->  for i in lst:"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.BoolOp):
            first_val = node.iter.values[0]
            out.append(_splice(source, node.iter, _text(source, first_val)))
    return out


def fix_augassign_add_scalar(source):
    """result += i  /  result += result + i  /  ... + list(i)  ->  result += [i]"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                and isinstance(node.target, ast.Name)):
            continue
        T = node.target.id
        val = node.value
        new_val_text = None
        if isinstance(val, ast.Name) and val.id != T:
            new_val_text = "[%s]" % val.id
        elif isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
            left, right = val.left, val.right
            other = None
            if isinstance(left, ast.Name) and left.id == T:
                other = right
            elif isinstance(right, ast.Name) and right.id == T:
                other = left
            if other is not None:
                if isinstance(other, ast.Name):
                    new_val_text = "[%s]" % other.id
                elif (isinstance(other, ast.Call) and isinstance(other.func, ast.Name)
                      and other.func.id == 'list' and len(other.args) == 1
                      and isinstance(other.args[0], ast.Name)):
                    new_val_text = "[%s]" % other.args[0].id
        if new_val_text is not None:
            out.append(_splice(source, val, new_val_text))
    return out


def fix_augassign_append_call(source):
    """new_list += x.append(elem)  ->  new_list.append(elem)"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            val = node.value
            if (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                    and val.func.attr == 'append' and len(val.args) == 1):
                arg_text = _text(source, val.args[0])
                new_stmt = "%s.append(%s)" % (node.target.id, arg_text)
                out.append(_splice(source, node, new_stmt))
    return out


def fix_subscript_method_call(source):
    """x.append[i]  ->  x.append(i)"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                and node.value.attr in _METHOD_NAMES):
            sl = node.slice
            if isinstance(sl, ast.Index):
                sl = sl.value
            if isinstance(sl, ast.Slice):
                continue
            arg_text = _text(source, sl)
            obj_text = _text(source, node.value)
            out.append(_splice(source, node, "%s(%s)" % (obj_text, arg_text)))
    return out


def fix_bare_attribute_call(source):
    """statement `lst.reverse` (missing call parens) -> `lst.reverse()`"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute):
            out.append(_splice(source, node.value, _text(source, node.value) + "()"))
    return out


def fix_double_equals_statement(source):
    """statement `output == []`  ->  `output = []`"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare)
                and len(node.value.ops) == 1 and isinstance(node.value.ops[0], ast.Eq)):
            left = node.value.left
            right = node.value.comparators[0]
            if isinstance(left, ast.Name):
                new_stmt = "%s = %s" % (_text(source, left), _text(source, right))
                out.append(_splice(source, node, new_stmt))
    return out


def _is_zero_index(sl):
    if isinstance(sl, ast.Index):
        sl = sl.value
    return isinstance(sl, ast.Constant) and sl.value == 0


def _is_first_elem_subscript(node, params):
    return (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
            and node.value.id in params and _is_zero_index(node.slice))


def fix_deseed_first_element(source):
    """new_lst = lst[0] / [lst[0]] / (lst[0],)  ->  empty container"""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        params = {a.arg for a in func.args.args}
        for node in ast.walk(func):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                continue
            val = node.value
            new_text = None
            if _is_first_elem_subscript(val, params):
                new_text = "[]"
            elif isinstance(val, ast.List) and len(val.elts) == 1 and _is_first_elem_subscript(val.elts[0], params):
                new_text = "[]"
            elif isinstance(val, ast.Tuple) and len(val.elts) == 1 and _is_first_elem_subscript(val.elts[0], params):
                new_text = "()"
            if new_text is not None:
                out.append(_splice(source, val, new_text))
    return out


def fix_tuple_accumulator_to_list(source):
    """Convert tuple-literal accumulator construction `(x,)` / `()` to list form."""
    tree = ast.parse(source)
    relevant = [n for n in ast.walk(tree) if isinstance(n, ast.Tuple) and len(n.elts) <= 1]
    if not relevant:
        return []
    replacements = []
    for t in relevant:
        elts_text = [_text(source, e) for e in t.elts]
        new_text = "[" + ", ".join(elts_text) + "]"
        s, e = _span(source, t)
        replacements.append((s, e, new_text))
    return [_multi_splice(source, replacements)]


def fix_membership_wrong_container(source):
    """`if i not in lst:` when the accumulator actually appended to is `output`."""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for for_node in ast.walk(func):
            if not isinstance(for_node, ast.For) or not isinstance(for_node.target, ast.Name):
                continue
            loop_var = for_node.target.id
            accumulator = None
            for n in ast.walk(for_node):
                if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                        and isinstance(n.value.func, ast.Attribute)
                        and n.value.func.attr in ('append', 'extend')
                        and isinstance(n.value.func.value, ast.Name)
                        and len(n.value.args) == 1
                        and isinstance(n.value.args[0], ast.Name)
                        and n.value.args[0].id == loop_var):
                    accumulator = n.value.func.value.id
                    break
            if accumulator is None:
                continue
            for n in ast.walk(for_node):
                if (isinstance(n, ast.Compare) and len(n.ops) == 1
                        and isinstance(n.ops[0], (ast.In, ast.NotIn))
                        and isinstance(n.left, ast.Name) and n.left.id == loop_var):
                    comp = n.comparators[0]
                    comp_text = _text(source, comp)
                    if comp_text != accumulator:
                        out.append(_splice(source, comp, accumulator))
    return out


def fix_premature_loop_return(source):
    """for ...: if ... else: return acc  ->  move return to after the loop."""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for for_node in ast.walk(func):
            if not isinstance(for_node, ast.For):
                continue
            if len(for_node.body) != 1 or not isinstance(for_node.body[0], ast.If):
                continue
            if_node = for_node.body[0]
            if len(if_node.orelse) != 1 or not isinstance(if_node.orelse[0], ast.Return):
                continue
            ret = if_node.orelse[0]
            if ret.value is None or not isinstance(ret.value, ast.Name):
                continue
            indent = _indent_at(source, for_node)
            if_s, _ = _span(source, if_node)
            body_last = if_node.body[-1]
            _, body_last_end = _span(source, body_last)
            new_if_text = source[if_s:body_last_end]
            s_for, e_for = _span(source, for_node)
            new_for_text = source[s_for:if_s] + new_if_text
            insertion = "\n%sreturn %s" % (indent, ret.value.id)
            out.append(source[:s_for] + new_for_text + insertion + source[e_for:])
    return out


def fix_remove_mutating_iterated_stmt(source):
    """Drop stray `lst.remove(i)` that mutates the iterated list in dedup loops."""
    tree = ast.parse(source)
    out = []
    for for_node in ast.walk(tree):
        if not isinstance(for_node, ast.For):
            continue
        if not isinstance(for_node.iter, ast.Name) or not isinstance(for_node.target, ast.Name):
            continue
        iterable = for_node.iter.id
        loopvar = for_node.target.id
        has_append = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                          and n.func.attr == 'append' for n in ast.walk(for_node))
        if not has_append:
            continue
        for stmt in ast.walk(for_node):
            if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Attribute) and stmt.value.func.attr == 'remove'
                    and isinstance(stmt.value.func.value, ast.Name) and stmt.value.func.value.id == iterable
                    and len(stmt.value.args) == 1 and isinstance(stmt.value.args[0], ast.Name)
                    and stmt.value.args[0].id == loopvar):
                s, e = _span(source, stmt)
                line_start = source.rfind("\n", 0, s) + 1
                line_end = source.find("\n", e)
                line_end = line_end + 1 if line_end != -1 else len(source)
                out.append(source[:line_start] + source[line_end:])
    return out


def fix_pop_value_as_remove(source):
    """`for i in lst: ... lst.pop(i)` (value, not index) -> `lst.remove(i)`"""
    tree = ast.parse(source)
    out = []
    for for_node in ast.walk(tree):
        if not isinstance(for_node, ast.For):
            continue
        if not (isinstance(for_node.iter, ast.Name) and isinstance(for_node.target, ast.Name)):
            continue
        iterable = for_node.iter.id
        loopvar = for_node.target.id
        for node in ast.walk(for_node):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'pop' and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == iterable and len(node.args) == 1
                    and isinstance(node.args[0], ast.Name) and node.args[0].id == loopvar):
                _, attr_e = _span(source, node.func)
                pop_start = attr_e - len('pop')
                out.append(source[:pop_start] + 'remove' + source[attr_e:])
    return out


def fix_while_count_dedup_to_if(source):
    """`while x.count(y) != 1: x.remove(y)` -> `if x.count(y) > 1: x.remove(y)`"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.NotEq)):
            continue
        if not (isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value == 1):
            continue
        if not (isinstance(test.left, ast.Call) and isinstance(test.left.func, ast.Attribute)
                and test.left.func.attr == 'count'):
            continue
        count_expr_text = _text(source, test.left)
        new_header = "if %s > 1:" % count_expr_text
        s_node, _ = _span(source, node)
        _, e_test = _span(source, test)
        colon_idx = source.index(':', e_test)
        out.append(source[:s_node] + new_header + source[colon_idx + 1:])
    return out


def fix_missing_final_reverse(source):
    """`lst.reverse(); ...; return lst` missing the closing reverse -> insert it."""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        first = func.body[0]
        if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Call)
                and isinstance(first.value.func, ast.Attribute) and first.value.func.attr == 'reverse'
                and isinstance(first.value.func.value, ast.Name)):
            continue
        var = first.value.func.value.id
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Name) and last.value.id == var):
            continue
        has_second_reverse = False
        for node in ast.walk(func):
            if node is first.value:
                continue
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'reverse' and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == var):
                has_second_reverse = True
        if has_second_reverse:
            continue
        indent = _indent_at(source, last)
        s, _ = _span(source, last)
        line_start = source.rfind("\n", 0, s) + 1
        insertion = "%s%s.reverse()\n" % (indent, var)
        out.append(source[:line_start] + insertion + source[line_start:])
    return out


def fix_flag_reset_position(source):
    """`check = True` before a for-loop that should be reset each iteration."""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        body = func.body
        for idx, stmt in enumerate(body):
            if not (isinstance(stmt, ast.For) and idx > 0):
                continue
            prev = body[idx - 1]
            if not (isinstance(prev, ast.Assign) and len(prev.targets) == 1
                    and isinstance(prev.targets[0], ast.Name)):
                continue
            if not (isinstance(prev.value, ast.Constant) and prev.value.value is True):
                continue
            flag_name = prev.targets[0].id
            used_inside = any(isinstance(n, ast.Name) and n.id == flag_name for n in ast.walk(stmt))
            if not used_inside or not stmt.body:
                continue
            prev_s, prev_e = _span(source, prev)
            line_start = source.rfind("\n", 0, prev_s) + 1
            line_end = source.find("\n", prev_e)
            line_end = line_end + 1 if line_end != -1 else len(source)
            first_body_stmt = stmt.body[0]
            fb_s, _ = _span(source, first_body_stmt)
            indent = _indent_at(source, first_body_stmt)
            insertion_text = "%s = True\n%s" % (flag_name, indent)
            replacements = [(line_start, line_end, ""), (fb_s, fb_s, insertion_text)]
            out.append(_multi_splice(source, replacements))
    return out


def fix_set_dedup_order(source):
    """`list(set(x))` doesn't preserve order -> `list(dict.fromkeys(x))`"""
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'list' and len(node.args) == 1):
            arg = node.args[0]
            if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                    and arg.func.id == 'set' and len(arg.args) == 1):
                inner_text = _text(source, arg.args[0])
                out.append(_splice(source, node, "list(dict.fromkeys(%s))" % inner_text))
    return out


def fix_print_instead_of_return(source):
    """Function ends with `print(x)` and has no return -> `return x`."""
    tree = ast.parse(source)
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(func))
        if has_return:
            continue
        last = func.body[-1]
        if (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
                and isinstance(last.value.func, ast.Name) and last.value.func.id == 'print'
                and len(last.value.args) == 1):
            arg_text = _text(source, last.value.args[0])
            out.append(_splice(source, last, "return %s" % arg_text))
    return out


# ----------------------------------------------------------------------------
# Fixer
# ----------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="undefined_name_typo",
                 apply=_safe(fix_undefined_name_typo),
                 symptoms=("wrong", "err:NameError")),
            Rule(name="shadowed_builtin_iter",
                 apply=_safe(fix_shadowed_builtin_iter),
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="boolop_for_iter",
                 apply=_safe(fix_boolop_for_iter),
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="augassign_add_scalar",
                 apply=_safe(fix_augassign_add_scalar),
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="augassign_append_call",
                 apply=_safe(fix_augassign_append_call),
                 symptoms=("wrong", "err:TypeError", "err:NameError")),
            Rule(name="subscript_method_call",
                 apply=_safe(fix_subscript_method_call),
                 symptoms=("err:TypeError",)),
            Rule(name="bare_attribute_call",
                 apply=_safe(fix_bare_attribute_call),
                 symptoms=("wrong",)),
            Rule(name="double_equals_statement",
                 apply=_safe(fix_double_equals_statement),
                 symptoms=("err:NameError", "wrong")),
            Rule(name="deseed_first_element",
                 apply=_safe(fix_deseed_first_element),
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="tuple_accumulator_to_list",
                 apply=_safe(fix_tuple_accumulator_to_list),
                 symptoms=("wrong",)),
            Rule(name="membership_wrong_container",
                 apply=_safe(fix_membership_wrong_container),
                 symptoms=("wrong",)),
            Rule(name="premature_loop_return",
                 apply=_safe(fix_premature_loop_return),
                 symptoms=("wrong",)),
            Rule(name="remove_mutating_iterated_stmt",
                 apply=_safe(fix_remove_mutating_iterated_stmt),
                 symptoms=("wrong",)),
            Rule(name="pop_value_as_remove",
                 apply=_safe(fix_pop_value_as_remove),
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="while_count_dedup_to_if",
                 apply=_safe(fix_while_count_dedup_to_if),
                 symptoms=("wrong",)),
            Rule(name="missing_final_reverse",
                 apply=_safe(fix_missing_final_reverse),
                 symptoms=("wrong",)),
            Rule(name="flag_reset_position",
                 apply=_safe(fix_flag_reset_position),
                 symptoms=("wrong",)),
            Rule(name="set_dedup_order",
                 apply=_safe(fix_set_dedup_order),
                 symptoms=("wrong",)),
            Rule(name="print_instead_of_return",
                 apply=_safe(fix_print_instead_of_return),
                 symptoms=("wrong",)),
        ]