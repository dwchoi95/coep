"""
Repair rules for the "Sorting Tuples" (sort_age) assignment.

Each rule performs a small, local, AST-span-based edit targeting one
observed misconception in student submissions. Rules never rewrite whole
functions; they only touch the specific sub-expression/statement that
carries the bug.
"""

import ast
import builtins

from src.core.repair import Rule


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------

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


def _safe(fn):
    def wrapper(source):
        try:
            return fn(source)
        except Exception:
            return []
    return wrapper


def _base_name(expr):
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Subscript) and isinstance(expr.value, ast.Name):
        return expr.value.id
    return None


# ---------------------------------------------------------------------
# 1. wrong comparison direction for selecting running max in selection sort
# ---------------------------------------------------------------------

_OP_TEXT = {ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>='}
_FLIP = {ast.Lt: ast.Gt, ast.LtE: ast.GtE, ast.Gt: ast.Lt, ast.GtE: ast.LtE}


@_safe
def fix_selection_direction(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        loop_var = node.target.id
        for sub in ast.walk(node):
            if not isinstance(sub, ast.If) or len(sub.body) != 1:
                continue
            assign = sub.body[0]
            if not (isinstance(assign, ast.Assign) and len(assign.targets) == 1
                    and isinstance(assign.targets[0], ast.Name)):
                continue
            if _base_name(assign.value) != loop_var:
                continue
            target_name = assign.targets[0].id
            test = sub.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and type(test.ops[0]) in _OP_TEXT):
                continue
            op = test.ops[0]
            left, right = test.left, test.comparators[0]
            left_base, right_base = _base_name(left), _base_name(right)
            if left_base == target_name and right_base == loop_var:
                desired_is_lt = True
            elif left_base == loop_var and right_base == target_name:
                desired_is_lt = False
            else:
                continue
            current_is_lt = type(op) in (ast.Lt, ast.LtE)
            if desired_is_lt == current_is_lt:
                continue
            new_op_type = _FLIP[type(op)]
            left_s, left_e = _span(source, left)
            right_s, right_e = _span(source, right)
            between = source[left_e:right_s]
            old_txt = _OP_TEXT[type(op)]
            new_txt = _OP_TEXT[new_op_type]
            idx = between.find(old_txt)
            if idx == -1:
                continue
            new_between = between[:idx] + new_txt + between[idx + len(old_txt):]
            out.append(source[:left_e] + new_between + source[right_s:])
    return out


# ---------------------------------------------------------------------
# 2. accumulator initialised as a tuple but overwritten with a scalar
# ---------------------------------------------------------------------

@_safe
def fix_subscript_assignment_depth(source):
    tree = ast.parse(source)
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        plain_index0 = set()
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                val = node.value
                if (isinstance(val, ast.Subscript) and isinstance(val.slice, ast.Constant)
                        and val.slice.value == 0):
                    plain_index0.add(node.targets[0].id)
        for node in ast.walk(func):
            if not (isinstance(node, ast.If) and len(node.body) == 1):
                continue
            stmt = node.body[0]
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)):
                continue
            target = stmt.targets[0].id
            val = stmt.value
            if (target in plain_index0 and isinstance(val, ast.Subscript)
                    and isinstance(val.value, ast.Name)):
                rs, re_ = _span(source, val.value)
                full_s, full_e = _span(source, val)
                out.append(source[:full_s] + source[rs:re_] + source[full_e:])
    return out


# ---------------------------------------------------------------------
# 3. statements after the inner for-loop use the raw loop variable
#    instead of the accumulator that was tracked inside the loop
# ---------------------------------------------------------------------

@_safe
def fix_postloop_wrong_var(source):
    tree = ast.parse(source)
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for parent in ast.walk(func):
            body = getattr(parent, 'body', None)
            if not isinstance(body, list):
                continue
            for idx, stmt in enumerate(body):
                if not (isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name)):
                    continue
                loop_var = stmt.target.id
                accum = None
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.If):
                        for s2 in sub.body:
                            if (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                                    and isinstance(s2.targets[0], ast.Name)
                                    and isinstance(s2.value, ast.Name)
                                    and s2.value.id == loop_var):
                                accum = s2.targets[0].id
                if accum is None or accum == loop_var:
                    continue
                rest = body[idx + 1:]
                found = []
                for s in rest:
                    for n2 in ast.walk(s):
                        if (isinstance(n2, ast.Name) and n2.id == loop_var
                                and isinstance(n2.ctx, ast.Load)):
                            found.append(n2)
                if not found:
                    continue
                new_source = source
                for n2 in sorted(found, key=lambda x: -_span(source, x)[0]):
                    s, e = _span(source, n2)
                    new_source = new_source[:s] + accum + new_source[e:]
                out.append(new_source)
    return out


# ---------------------------------------------------------------------
# 4. a single undefined name used where another variable was intended
# ---------------------------------------------------------------------

def _role(source, node):
    s, e = _span(source, node)
    after = source[e:e + 8]
    before = source[max(0, s - 8):s]
    if after.startswith('.remove('):
        return 'remove_recv'
    if after.startswith('.append('):
        return 'append_recv'
    if before.endswith('remove('):
        return 'elem_in_remove'
    if before.endswith('append('):
        return 'elem_in_append'
    return None


@_safe
def fix_undefined_name(source):
    tree = ast.parse(source)
    out = []
    builtin_names = set(dir(builtins))
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        assigned, used = set(), []
        for node in ast.walk(func):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    assigned.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    used.append(node)
            elif isinstance(node, ast.FunctionDef) and node is not func:
                assigned.add(node.name)
        params = {a.arg for a in func.args.args}
        known = assigned | params | {"True", "False", "None"}
        undefined = {}
        for n in used:
            if n.id not in known and n.id not in builtin_names:
                undefined.setdefault(n.id, []).append(n)
        if len(undefined) != 1:
            continue
        undef_name, nodes = next(iter(undefined.items()))

        return_ids = set()
        for n2 in ast.walk(func):
            if isinstance(n2, ast.Return) and isinstance(n2.value, ast.Name):
                return_ids.add(id(n2.value))

        roles = set()
        for n2 in nodes:
            if id(n2) in return_ids:
                roles.add('return_val')
            r = _role(source, n2)
            if r:
                roles.add(r)

        extremum_candidates = []
        for n2 in ast.walk(func):
            if isinstance(n2, ast.If):
                for s2 in n2.body:
                    if (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                            and isinstance(s2.targets[0], ast.Name)):
                        extremum_candidates.append(s2.targets[0].id)

        list_candidates = []
        for s2 in func.body:
            if (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                    and isinstance(s2.targets[0], ast.Name)
                    and isinstance(s2.value, ast.List) and len(s2.value.elts) == 0):
                list_candidates.append(s2.targets[0].id)

        replacement = None
        if 'remove_recv' in roles and len(params) == 1:
            replacement = next(iter(params))
        elif ('append_recv' in roles or 'return_val' in roles) and list_candidates:
            replacement = list_candidates[-1]
        elif ('elem_in_remove' in roles or 'elem_in_append' in roles) and extremum_candidates:
            replacement = extremum_candidates[-1]

        if replacement is None:
            if extremum_candidates:
                replacement = extremum_candidates[-1]
            elif list_candidates:
                replacement = list_candidates[-1]
            elif len(params) == 1:
                replacement = next(iter(params))

        if replacement is None or replacement == undef_name:
            continue

        spans = [_span(source, n) for n in nodes]
        new_source = source
        for s, e in sorted(spans, key=lambda x: -x[0]):
            new_source = new_source[:s] + replacement + new_source[e:]
        out.append(new_source)
    return out


# ---------------------------------------------------------------------
# 5. swapped assignment: `loopvar = accumulator` instead of the reverse
# ---------------------------------------------------------------------

@_safe
def fix_swapped_assignment(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        loop_var = node.target.id
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.If) and len(sub.body) == 1):
                continue
            assign = sub.body[0]
            if not (isinstance(assign, ast.Assign) and len(assign.targets) == 1
                    and isinstance(assign.targets[0], ast.Name)
                    and assign.targets[0].id == loop_var
                    and isinstance(assign.value, ast.Name)
                    and assign.value.id != loop_var):
                continue
            tgt_s, tgt_e = _span(source, assign.targets[0])
            val_s, val_e = _span(source, assign.value)
            tgt_txt = source[tgt_s:tgt_e]
            val_txt = source[val_s:val_e]
            new_stmt = f"{val_txt} = {tgt_txt}"
            out.append(_splice(source, assign, new_stmt))
    return out


# ---------------------------------------------------------------------
# 6. function builds a list but never returns it
# ---------------------------------------------------------------------

@_safe
def add_missing_return(source):
    tree = ast.parse(source)
    out = []
    for func in tree.body:
        if not (isinstance(func, ast.FunctionDef) and func.name == "sort_age"):
            continue
        body = func.body
        if not body:
            continue
        last = body[-1]
        if isinstance(last, ast.Return):
            continue
        acc_var = None
        for stmt in body:
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.List) and len(stmt.value.elts) == 0):
                acc_var = stmt.targets[0].id
        if acc_var is None:
            continue
        indent = " " * last.col_offset
        s, e = _span(source, last)
        new_source = source[:e] + "\n" + indent + f"return {acc_var}" + source[e:]
        out.append(new_source)
    return out


# ---------------------------------------------------------------------
# 7. `return X.reverse` / `return X.reverse()` (reverse() returns None)
# ---------------------------------------------------------------------

@_safe
def fix_reverse_return(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Return) and node.value is not None):
            continue
        val = node.value
        target = None
        if isinstance(val, ast.Attribute) and val.attr == 'reverse' and isinstance(val.value, ast.Name):
            target = val.value.id
        elif (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
              and val.func.attr == 'reverse' and isinstance(val.func.value, ast.Name)):
            target = val.func.value.id
        if target is None:
            continue
        indent = " " * node.col_offset
        new_text = f"{target}.reverse()\n{indent}return {target}"
        out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------
# 8. `helper(lst).reverse` used as a bare expression statement
# ---------------------------------------------------------------------

@_safe
def fix_call_dot_reverse(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        val = node.value
        if not (isinstance(val, ast.Attribute) and val.attr == 'reverse'
                and isinstance(val.value, ast.Call)):
            continue
        call = val.value
        target = None
        if call.args and isinstance(call.args[0], ast.Name):
            target = call.args[0].id
        if target is None:
            continue
        call_s, call_e = _span(source, call)
        call_text = source[call_s:call_e]
        indent = " " * node.col_offset
        new_text = f"{call_text}\n{indent}{target}.reverse()"
        out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------
# 9. `.reverse` / `.reverse()` called as the last statement INSIDE the
#    selection loop, instead of once after it finishes
# ---------------------------------------------------------------------

@_safe
def fix_misplaced_reverse(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.While, ast.For)):
            continue
        body = node.body
        if not body:
            continue
        last = body[-1]
        target = None
        if isinstance(last, ast.Expr):
            val = last.value
            if isinstance(val, ast.Attribute) and val.attr == 'reverse' and isinstance(val.value, ast.Name):
                target = val.value.id
            elif (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)
                  and val.func.attr == 'reverse' and isinstance(val.func.value, ast.Name)):
                target = val.func.value.id
        if target is None or len(body) == 1:
            continue
        stmt_s, stmt_e = _span(source, last)
        line_start = source.rfind("\n", 0, stmt_s) + 1
        line_end = source.find("\n", stmt_e)
        line_end = line_end + 1 if line_end != -1 else len(source)
        indent = " " * node.col_offset
        replacement = f"{indent}{target}.reverse()\n"
        out.append(source[:line_start] + replacement + source[line_end:])
    return out


# ---------------------------------------------------------------------
# 10. `result += something` where `.append` was meant (tuple unpacking)
# ---------------------------------------------------------------------

@_safe
def fix_augassign_append(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                and isinstance(node.target, ast.Name)):
            continue
        val = node.value
        if isinstance(val, (ast.List, ast.Tuple)):
            continue
        target_s, target_e = _span(source, node.target)
        val_s, val_e = _span(source, val)
        new_stmt = f"{source[target_s:target_e]}.append({source[val_s:val_e]})"
        out.append(_splice(source, node, new_stmt))
    return out


# ---------------------------------------------------------------------
# 11. outer `for x in lst:` used as the main loop while mutating lst
#     with .remove() inside -> should be `while lst:`
# ---------------------------------------------------------------------

@_safe
def fix_for_should_be_while(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                and isinstance(node.iter, ast.Name)):
            continue
        target_name = node.target.id
        iter_name = node.iter.id
        used = any(isinstance(n, ast.Name) and n.id == target_name and n is not node.target
                   for n in ast.walk(node))
        has_remove = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == 'remove' and isinstance(n.func.value, ast.Name)
            and n.func.value.id == iter_name
            for n in ast.walk(node)
        )
        if used or not has_remove:
            continue
        start_s, _ = _span(source, node)
        body_s, _ = _span(source, node.body[0])
        header_text = source[start_s:body_s]
        colon_idx = header_text.rfind(':')
        if colon_idx == -1:
            continue
        new_header = f"while {iter_name}:"
        new_source = source[:start_s] + new_header + header_text[colon_idx + 1:] + source[body_s:]
        out.append(new_source)
    return out


# ---------------------------------------------------------------------
# 12. `return` placed as the last statement inside the loop, causing an
#     early exit after one iteration
# ---------------------------------------------------------------------

@_safe
def fix_return_inside_loop(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.While, ast.For)):
            continue
        body = node.body
        if len(body) < 2:
            continue
        last = body[-1]
        if not isinstance(last, ast.Return):
            continue
        stmt_s, stmt_e = _span(source, last)
        line_start = source.rfind("\n", 0, stmt_s) + 1
        line_end = source.find("\n", stmt_e)
        line_end = line_end + 1 if line_end != -1 else len(source)
        removed_line = source[line_start:line_end]
        stripped = removed_line.strip()
        indent = " " * node.col_offset
        trailing_nl = "\n" if removed_line.endswith("\n") else ""
        replacement_line = indent + stripped + trailing_nl
        new_source = source[:line_start] + replacement_line + source[line_end:]
        out.append(new_source)
    return out


# ---------------------------------------------------------------------
# 13. common method-name typo: `.removal(` -> `.remove(`
# ---------------------------------------------------------------------

@_safe
def fix_attr_typo(source):
    tree = ast.parse(source)
    typo_map = {'removal': 'remove'}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in typo_map:
            s, e = _span(source, node)
            attr_len = len(node.attr)
            new_attr = typo_map[node.attr]
            out.append(source[:e - attr_len] + new_attr + source[e:])
    return out


# ---------------------------------------------------------------------
# 14. `lst.pop[index]` subscript-typo'd call -> `lst.pop(index)`
# ---------------------------------------------------------------------

@_safe
def fix_subscript_call_typo(source):
    tree = ast.parse(source)
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)):
            continue
        if node.value.attr not in ('pop', 'remove', 'append', 'index'):
            continue
        idx_s, idx_e = _span(source, node.slice)
        idx_text = source[idx_s:idx_e]
        val_s, val_e = _span(source, node.value)
        new_text = source[val_s:val_e] + "(" + idx_text + ")"
        out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------
# 15. minimum is tracked (variable name suggests "small"/"low"/"min")
#     but results are appended to the END of the output, producing
#     ascending instead of descending order -> prepend instead
# ---------------------------------------------------------------------

@_safe
def fix_min_tracking_append_order(source):
    tree = ast.parse(source)
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        has_min_name = False
        for node in ast.walk(func):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                for side in (node.left, node.comparators[0]):
                    base = _base_name(side)
                    if base and any(k in base.lower() for k in ('low', 'small', 'min')):
                        has_min_name = True
        if not has_min_name:
            continue
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                tgt = node.targets[0].id
                val = node.value
                if (isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add)
                        and isinstance(val.left, ast.Name) and val.left.id == tgt
                        and isinstance(val.right, ast.List)):
                    left_s, left_e = _span(source, val.left)
                    right_s, right_e = _span(source, val.right)
                    left_txt = source[left_s:left_e]
                    right_txt = source[right_s:right_e]
                    new_val_txt = right_txt + " + " + left_txt
                    out.append(_splice(source, val, new_val_txt))
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                  and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)
                  and len(node.args) == 1):
                arg_s, arg_e = _span(source, node.args[0])
                arg_txt = source[arg_s:arg_e]
                recv_s, recv_e = _span(source, node.func.value)
                recv_txt = source[recv_s:recv_e]
                new_call = f"{recv_txt}.insert(0, {arg_txt})"
                out.append(_splice(source, node, new_call))
    return out


# ---------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="selection_direction_flip",
                 apply=fix_selection_direction,
                 symptoms=("wrong",)),
            Rule(name="scalar_overwrites_tuple_accumulator",
                 apply=fix_subscript_assignment_depth,
                 symptoms=("wrong", "err:TypeError", "err:ValueError")),
            Rule(name="postloop_uses_raw_loopvar",
                 apply=fix_postloop_wrong_var,
                 symptoms=("wrong",)),
            Rule(name="undefined_name_misreference",
                 apply=fix_undefined_name,
                 symptoms=("err:NameError",)),
            Rule(name="swapped_assignment_in_if",
                 apply=fix_swapped_assignment,
                 symptoms=("wrong",)),
            Rule(name="missing_return_of_accumulator",
                 apply=add_missing_return,
                 symptoms=("wrong",)),
            Rule(name="reverse_as_return_value",
                 apply=fix_reverse_return,
                 symptoms=("wrong",)),
            Rule(name="call_dot_reverse_no_parens",
                 apply=fix_call_dot_reverse,
                 symptoms=("err:AttributeError", "wrong")),
            Rule(name="reverse_called_inside_loop",
                 apply=fix_misplaced_reverse,
                 symptoms=("wrong",)),
            Rule(name="augassign_should_be_append",
                 apply=fix_augassign_append,
                 symptoms=("wrong",)),
            Rule(name="for_mutation_should_be_while",
                 apply=fix_for_should_be_while,
                 symptoms=("wrong", "err:RuntimeError")),
            Rule(name="return_inside_loop_early_exit",
                 apply=fix_return_inside_loop,
                 symptoms=("wrong",)),
            Rule(name="method_name_typo",
                 apply=fix_attr_typo,
                 symptoms=("err:AttributeError",)),
            Rule(name="subscript_instead_of_call",
                 apply=fix_subscript_call_typo,
                 symptoms=("err:TypeError",)),
            Rule(name="min_tracking_wrong_accumulation_order",
                 apply=fix_min_tracking_append_order,
                 symptoms=("wrong",)),
        ]