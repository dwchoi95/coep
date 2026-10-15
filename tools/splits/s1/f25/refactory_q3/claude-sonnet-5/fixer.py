import ast
import builtins


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
    except Exception:
        return None


def _iter_bodies(tree):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            val = getattr(node, field, None)
            if isinstance(val, list):
                yield val


def _slice_value(node):
    if hasattr(ast, "Index") and isinstance(node, ast.Index):
        return node.value
    return node


def _dedupe(cands, source):
    out = []
    for c in cands:
        if c and c != source and c not in out:
            out.append(c)
    return out


MUTATORS = {"reverse", "sort", "append", "extend", "insert", "remove"}


# 1. store += ele  -> store += [ele]
def _augassign_scalar_to_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
            val = node.value
            if isinstance(val, (ast.Name, ast.Subscript)):
                s, e = _span(source, val)
                new_val = "[" + source[s:e] + "]"
                out.append(_splice(source, val, new_val))
    return _dedupe(out, source)


# 2. X += X.append(y)  ->  X.append(y)
def _augassign_append_result(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) and val.func.attr == "append":
                s, e = _span(source, val)
                out.append(_splice(source, node, source[s:e]))
    return _dedupe(out, source)


# 3. using an undefined name that should be the accumulator variable
def _undefined_name_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        assigned = {func.name}
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                assigned.add(n.id)
            if isinstance(n, ast.arg):
                assigned.add(n.arg)
        acc = None
        for st in func.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                if isinstance(st.value, ast.List) and len(st.value.elts) == 0:
                    acc = st.targets[0].id
                    break
        if acc is None:
            continue
        undefined = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in assigned and n.id not in dir(builtins):
                    undefined.add(n.id)
        undefined.discard(acc)
        if len(undefined) != 1:
            continue
        bad = next(iter(undefined))
        spans = [_span(source, n) for n in ast.walk(func) if isinstance(n, ast.Name) and n.id == bad]
        if not spans:
            continue
        spans.sort(key=lambda t: t[0], reverse=True)
        new_source = source
        for s, e in spans:
            new_source = new_source[:s] + acc + new_source[e:]
        out.append(new_source)
    return _dedupe(out, source)


# 4. newlst = lst(0)  -> newlst = []
def _param_call_init_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) \
               and isinstance(node.value.func, ast.Name) and node.value.func.id == param:
                out.append(_splice(source, node.value, "[]"))
    return _dedupe(out, source)


# 5. result = lst[0]  -> result = []   (scalar init instead of empty list)
def _param_subscript0_init_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Subscript) \
               and isinstance(node.value.value, ast.Name) and node.value.value.id == param:
                sl = _slice_value(node.value.slice)
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    out.append(_splice(source, node.value, "[]"))
    return _dedupe(out, source)


# 6. (x,) singleton tuple used as list accumulator -> [x]
def _tuple_to_list_singleton(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 1:
            s, e = _span(source, node.elts[0])
            out.append(_splice(source, node, "[" + source[s:e] + "]"))
    return _dedupe(out, source)


# 7. guard against empty list before indexing param[0]
def _guard_empty_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        body = func.body
        already = False
        for st in body:
            if isinstance(st, ast.If):
                dumped = ast.dump(st.test)
                if param in dumped and ("len" in dumped or "List" in dumped):
                    already = True
        if already:
            continue
        for st in body:
            found = False
            for n in ast.walk(st):
                if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == param:
                    sl = _slice_value(n.slice)
                    if isinstance(sl, ast.Constant) and sl.value == 0:
                        found = True
            if found:
                indent = " " * st.col_offset
                s, e = _span(source, st)
                guard = f"if len({param}) == 0:\n{indent}    return []\n{indent}"
                out.append(source[:s] + guard + source[s:])
                break
    return _dedupe(out, source)


# 8. return None for empty case -> return []
def _return_none_to_empty_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            cond = node.test
            is_empty = False
            if isinstance(cond, ast.Compare) and len(cond.ops) == 1 and isinstance(cond.ops[0], ast.Eq):
                right = cond.comparators[0]
                if isinstance(right, ast.List) and len(right.elts) == 0:
                    is_empty = True
                left = cond.left
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len" \
                   and isinstance(right, ast.Constant) and right.value == 0:
                    is_empty = True
            if is_empty:
                for st in node.body:
                    if isinstance(st, ast.Return) and isinstance(st.value, ast.Constant) and st.value.value is None:
                        out.append(_splice(source, st.value, "[]"))
    return _dedupe(out, source)


# 9. chained `x in acc == True` -> `x in acc`
def _chained_in_true_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 2:
            if isinstance(node.ops[0], ast.In) and isinstance(node.ops[1], ast.Eq):
                comp1 = node.comparators[1]
                if isinstance(comp1, ast.Constant) and comp1.value is True:
                    ls, le = _span(source, node.left)
                    ms, me = _span(source, node.comparators[0])
                    new_text = source[ls:le] + " in " + source[ms:me]
                    out.append(_splice(source, node, new_text))
    return _dedupe(out, source)


# 10. bare attribute used as statement/return/assign when it should be a call
def _bare_attribute_call_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    names = {"pop", "reverse", "sort", "append", "remove", "extend", "insert"}
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute) and node.value.attr in names:
            target = node.value
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute) and node.value.attr in names:
            target = node.value
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and node.value.attr in names:
            target = node.value
        if target is not None:
            s, e = _span(source, target)
            out.append(_splice(source, target, source[s:e] + "()"))
    return _dedupe(out, source)


# 11. mutate-while-iterate dedup via count()>1 / remove -> wrap with reverse()
def _reverse_wrap_remove_loop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for body in _iter_bodies(tree):
        for idx, stmt in enumerate(body):
            if not isinstance(stmt, ast.For) or not isinstance(stmt.target, ast.Name):
                continue
            target_id = stmt.target.id
            has_count_cmp = False
            remove_obj = None
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], ast.Gt):
                    left = sub.left
                    if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) and left.func.attr == "count":
                        if left.args and isinstance(left.args[0], ast.Name) and left.args[0].id == target_id:
                            comp = sub.comparators[0]
                            if isinstance(comp, ast.Constant) and comp.value == 1:
                                has_count_cmp = True
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "remove":
                    if sub.args and isinstance(sub.args[0], ast.Name) and sub.args[0].id == target_id \
                       and isinstance(sub.func.value, ast.Name):
                        remove_obj = sub.func.value.id
            if not (has_count_cmp and remove_obj):
                continue

            def is_reverse_call(n, name):
                return isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) \
                    and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "reverse" \
                    and isinstance(n.value.func.value, ast.Name) and n.value.func.value.id == name

            prev = body[idx - 1] if idx > 0 else None
            nxt = body[idx + 1] if idx + 1 < len(body) else None
            if prev is not None and is_reverse_call(prev, remove_obj) and nxt is not None and is_reverse_call(nxt, remove_obj):
                continue
            indent = " " * stmt.col_offset
            s, e = _span(source, stmt)
            before = f"{remove_obj}.reverse()\n{indent}"
            after = f"\n{indent}{remove_obj}.reverse()"
            out.append(source[:s] + before + source[s:e] + after + source[e:])
    return _dedupe(out, source)


# 12. return of the loop variable, nested in for, should be dedented and be the accumulator
def _dedent_return_loopvar_to_acc(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for body in _iter_bodies(tree):
        for stmt in body:
            if not isinstance(stmt, ast.For) or not isinstance(stmt.target, ast.Name):
                continue
            if len(stmt.body) < 2:
                continue
            last = stmt.body[-1]
            if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Name) and last.value.id == stmt.target.id):
                continue
            acc = None
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "append":
                    if isinstance(sub.func.value, ast.Name):
                        acc = sub.func.value.id
                        break
            if acc is None:
                continue
            indent = " " * stmt.col_offset
            rs, re_ = _span(source, last)
            line_start = source.rfind("\n", 0, rs) + 1
            line_end = source.find("\n", re_)
            line_end = line_end + 1 if line_end != -1 else len(source)
            new_source = source[:line_start] + source[line_end:]
            final_source = new_source[:line_start] + f"{indent}return {acc}\n" + new_source[line_start:]
            out.append(final_source)
    return _dedupe(out, source)


# 13. trailing return inside for loop (not of loop var) should be dedented out
def _dedent_trailing_return_generic(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for body in _iter_bodies(tree):
        for stmt in body:
            if not isinstance(stmt, ast.For):
                continue
            if len(stmt.body) < 2:
                continue
            last = stmt.body[-1]
            if not isinstance(last, ast.Return):
                continue
            if isinstance(stmt.target, ast.Name) and isinstance(last.value, ast.Name) and last.value.id == stmt.target.id:
                continue
            indent = " " * stmt.col_offset
            rs, re_ = _span(source, last)
            line_start = source.rfind("\n", 0, rs) + 1
            line_end = source.find("\n", re_)
            line_end = line_end + 1 if line_end != -1 else len(source)
            return_text = source[rs:re_]
            new_source = source[:line_start] + source[line_end:]
            final_source = new_source[:line_start] + f"{indent}{return_text}\n" + new_source[line_start:]
            out.append(final_source)
    return _dedupe(out, source)


# 14. remove an unneeded .sort() that breaks ordering of a membership-based dedup
def _remove_unneeded_sort(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        sort_stmt = None
        for st in func.body:
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute) \
               and st.value.func.attr == "sort" and isinstance(st.value.func.value, ast.Name) and st.value.func.value.id == param:
                sort_stmt = st
                break
        if sort_stmt is None:
            continue
        uses_membership = False
        uses_adjacency = False
        for n in ast.walk(func):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.NotIn):
                uses_membership = True
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Eq):
                if isinstance(n.left, ast.Subscript) and isinstance(n.comparators[0], ast.Subscript):
                    uses_adjacency = True
        if not (uses_membership and not uses_adjacency):
            continue
        s, e = _span(source, sort_stmt)
        line_start = source.rfind("\n", 0, s) + 1
        line_end = source.find("\n", e)
        line_end = line_end + 1 if line_end != -1 else len(source)
        out.append(source[:line_start] + source[line_end:])
    return _dedupe(out, source)


# 15. `x in lst[:x]` (loop value used as slice bound) should check against the accumulator
def _slice_prefix_misuse_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(func):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                left = node.left
                right = node.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Subscript):
                    sl = right.slice
                    if isinstance(sl, ast.Slice) and sl.lower is None and isinstance(sl.upper, ast.Name) and sl.upper.id == left.id:
                        acc = None
                        for n2 in ast.walk(func):
                            if isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute) and n2.func.attr == "append":
                                if isinstance(n2.func.value, ast.Name):
                                    acc = n2.func.value.id
                            if isinstance(n2, ast.AugAssign) and isinstance(n2.target, ast.Name) and isinstance(n2.op, ast.Add):
                                acc = n2.target.id
                        if acc:
                            out.append(_splice(source, right, acc))
    return _dedupe(out, source)


# 16. X = Y.mutator()  ->  X = Y ; Y.mutator()  (reverse()/remove()/etc return None)
def _assign_from_inplace_call_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) and val.func.attr in MUTATORS \
               and isinstance(val.func.value, ast.Name):
                target = node.targets[0].id
                obj = val.func.value.id
                cs, ce = _span(source, val)
                call_text = source[cs:ce]
                indent = " " * node.col_offset
                if target == obj:
                    new_text = call_text
                else:
                    new_text = f"{target} = {obj}\n{indent}{call_text}"
                out.append(_splice(source, node, new_text))
    return _dedupe(out, source)


# 17. return Y.mutator()  ->  Y.mutator() ; return Y
def _return_inplace_call_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Call) \
           and isinstance(node.value.func, ast.Attribute) and node.value.func.attr in MUTATORS \
           and isinstance(node.value.func.value, ast.Name):
            obj = node.value.func.value.id
            indent = " " * node.col_offset
            cs, ce = _span(source, node.value)
            call_text = source[cs:ce]
            new_text = f"{call_text}\n{indent}return {obj}"
            out.append(_splice(source, node, new_text))
    return _dedupe(out, source)


# 18. if <removal>: ... ; j += 1   -> move increment into else (recheck same index after removal)
def _guard_increment_after_removal(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for body in _iter_bodies(tree):
        for idx, stmt in enumerate(body):
            if not isinstance(stmt, ast.If) or stmt.orelse:
                continue
            if idx + 1 >= len(body):
                continue
            nxt = body[idx + 1]
            if not isinstance(nxt, ast.AugAssign):
                continue
            mutates = False
            for n in ast.walk(stmt):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("remove", "pop"):
                    mutates = True
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.BinOp):
                    mutates = True
            if not mutates:
                continue
            if_s, if_e = _span(source, stmt)
            aug_s, aug_e = _span(source, nxt)
            aug_text = source[aug_s:aug_e]
            indent = " " * stmt.col_offset
            inner_indent = indent + "    "
            new_source = source[:if_e] + f"\n{indent}else:\n{inner_indent}{aug_text}" + source[aug_e:]
            out.append(new_source)
    return _dedupe(out, source)


# 19. while VAR < ...: body with no increment of VAR -> append VAR += 1
def _add_missing_increment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            test = node.test
            var = None
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Lt):
                if isinstance(test.left, ast.Name):
                    var = test.left.id
            if var is None or not node.body:
                continue
            incremented = False
            for st in node.body:
                if isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name) and st.target.id == var:
                    incremented = True
                if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) \
                   and st.targets[0].id == var:
                    incremented = True
            if incremented:
                continue
            last = node.body[-1]
            indent = " " * last.col_offset
            s, e = _span(source, last)
            out.append(source[:e] + f"\n{indent}{var} += 1" + source[e:])
    return _dedupe(out, source)


# 20. `if x in acc: acc.append(x)` should be `not in` (inverted guard)
def _in_should_be_not_in_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 \
           and isinstance(node.test.ops[0], ast.In):
            comp = node.test
            acc_candidates = set()
            for st in node.body:
                if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute) \
                   and st.value.func.attr == "append" and isinstance(st.value.func.value, ast.Name):
                    acc_candidates.add(st.value.func.value.id)
            if isinstance(comp.comparators[0], ast.Name) and comp.comparators[0].id in acc_candidates:
                ls, le = _span(source, comp.left)
                rs, re_ = _span(source, comp.comparators[0])
                new_text = source[ls:le] + " not in " + source[rs:re_]
                out.append(_splice(source, comp, new_text))
    return _dedupe(out, source)


# 21. obj.append[x]  ->  obj.append(x)  (bracket/paren confusion)
def _subscript_as_call_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr in ("append", "remove", "add"):
            sl = _slice_value(node.slice)
            s, e = _span(source, sl)
            arg_text = source[s:e]
            vs, ve = _span(source, node.value)
            val_text = source[vs:ve]
            out.append(_splice(source, node, f"{val_text}({arg_text})"))
    return _dedupe(out, source)


from src.core.repair import Rule


class Fixer:
    def rules(self):
        return [
            Rule(name="augassign_scalar_to_list", apply=_augassign_scalar_to_list,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="augassign_append_result", apply=_augassign_append_result,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="undefined_name_is_accumulator", apply=_undefined_name_fix,
                 symptoms=("err:NameError",)),
            Rule(name="param_call_init_to_empty_list", apply=_param_call_init_fix,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="param_subscript0_init_to_empty_list", apply=_param_subscript0_init_fix,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="tuple_to_list_singleton", apply=_tuple_to_list_singleton,
                 symptoms=("wrong",)),
            Rule(name="guard_empty_list_before_index0", apply=_guard_empty_list,
                 symptoms=("err:IndexError",)),
            Rule(name="return_none_to_empty_list", apply=_return_none_to_empty_list,
                 symptoms=("wrong",)),
            Rule(name="chained_in_true_fix", apply=_chained_in_true_fix,
                 symptoms=("wrong",)),
            Rule(name="bare_attribute_call_fix", apply=_bare_attribute_call_fix,
                 symptoms=("wrong", "err:TypeError", "err:AttributeError")),
            Rule(name="reverse_wrap_remove_loop", apply=_reverse_wrap_remove_loop,
                 symptoms=("wrong",)),
            Rule(name="dedent_return_loopvar_to_acc", apply=_dedent_return_loopvar_to_acc,
                 symptoms=("wrong",)),
            Rule(name="dedent_trailing_return_generic", apply=_dedent_trailing_return_generic,
                 symptoms=("wrong",)),
            Rule(name="remove_unneeded_sort", apply=_remove_unneeded_sort,
                 symptoms=("wrong",)),
            Rule(name="slice_prefix_misuse_fix", apply=_slice_prefix_misuse_fix,
                 symptoms=("wrong",)),
            Rule(name="assign_from_inplace_call_fix", apply=_assign_from_inplace_call_fix,
                 symptoms=("wrong", "err:AttributeError", "err:TypeError")),
            Rule(name="return_inplace_call_fix", apply=_return_inplace_call_fix,
                 symptoms=("wrong", "err:AttributeError", "err:TypeError")),
            Rule(name="guard_increment_after_removal", apply=_guard_increment_after_removal,
                 symptoms=("wrong",)),
            Rule(name="add_missing_loop_increment", apply=_add_missing_increment,
                 symptoms=("timeout", "wrong")),
            Rule(name="in_should_be_not_in", apply=_in_should_be_not_in_fix,
                 symptoms=("wrong",)),
            Rule(name="subscript_as_call_fix", apply=_subscript_as_call_fix,
                 symptoms=("err:TypeError",)),
        ]