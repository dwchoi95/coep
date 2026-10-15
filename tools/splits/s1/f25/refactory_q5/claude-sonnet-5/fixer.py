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


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _find_parent_block(tree, target):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list):
                for item in block:
                    if item is target:
                        return block
    return None


def _contains(container, target):
    for n in ast.walk(container):
        if n is target:
            return True
    return False


def _close(a, b):
    """True if a,b differ by a single char insertion/deletion/substitution."""
    if a == b:
        return False
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = sum(1 for x, y in zip(a, b) if x != y)
        return diff == 1
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    i = j = 0
    diffs = 0
    while i < len(longer) and j < len(shorter):
        if longer[i] == shorter[j]:
            i += 1
            j += 1
        else:
            diffs += 1
            i += 1
            if diffs > 1:
                return False
    return True


def _fix_track_var_misuse(source):
    """After a 'find extremum' for-loop, append/remove should use the
    tracking variable, not the stale loop variable left over from the loop."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        loop_var = node.target.id
        track_name = None
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                for s in stmt.body:
                    if (isinstance(s, ast.Assign) and len(s.targets) == 1
                            and isinstance(s.targets[0], ast.Name)
                            and isinstance(s.value, ast.Name)
                            and s.value.id == loop_var):
                        track_name = s.targets[0].id
        if not track_name or track_name == loop_var:
            continue
        parent_block = _find_parent_block(tree, node)
        if parent_block is None:
            continue
        idx = parent_block.index(node)
        for sib in parent_block[idx + 1:]:
            spans = []
            for n in ast.walk(sib):
                if isinstance(n, ast.Name) and n.id == loop_var:
                    spans.append(_span(source, n))
            if spans:
                spans.sort(key=lambda t: t[0], reverse=True)
                new_source = source
                for s, e in spans:
                    new_source = new_source[:s] + track_name + new_source[e:]
                out.append(new_source)
    return out


def _fix_return_wrong_var(source):
    """The final return should slice/return the accumulator list that was
    built via .append(...), not some other (e.g. the original parameter)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        acc_names = set()
        for n in ast.walk(func):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "append" and isinstance(n.func.value, ast.Name)):
                acc_names.add(n.func.value.id)
        init_names = set()
        for n in ast.walk(func):
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.List)
                    and len(n.value.elts) == 0):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        init_names.add(t.id)
        acc_names &= init_names
        if len(acc_names) != 1:
            continue
        acc_name = next(iter(acc_names))
        for n in ast.walk(func):
            if isinstance(n, ast.Return) and n.value is not None:
                val = n.value
                target_node = None
                if isinstance(val, ast.Name):
                    target_node = val
                elif isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name):
                    target_node = val.value
                if target_node is not None and target_node.id != acc_name:
                    s, e = _span(source, target_node)
                    out.append(source[:s] + acc_name + source[e:])
    return out


def _fix_typo_name(source):
    """A used name is undefined, but a locally-assigned name differs from
    it by a single character (classic copy/paste typo)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        assigned = set()
        used = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name):
                if isinstance(n.ctx, ast.Store):
                    assigned.add(n.id)
                elif isinstance(n.ctx, ast.Load):
                    used.append(n)
        assigned |= {a.arg for a in func.args.args}
        for n in used:
            if n.id in assigned:
                continue
            candidates = [a for a in assigned if _close(a, n.id)]
            if len(candidates) == 1:
                s, e = _span(source, n)
                out.append(source[:s] + candidates[0] + source[e:])
    return out


def _fix_min_tracking(source):
    """'if loopvar < tracked: tracked = loopvar' finds the minimum, but
    top_k needs the maximum: flip the comparison."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Lt)):
            continue
        left = node.test.left
        right = node.test.comparators[0]
        if not (isinstance(left, ast.Name) and isinstance(right, ast.Name)):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Assign):
            continue
        assign = node.body[0]
        if not (len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Name)
                and assign.targets[0].id == right.id
                and isinstance(assign.value, ast.Name) and assign.value.id == left.id):
            continue
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        new_cmp = source[ls:le] + " > " + source[rs:re_]
        out.append(_splice(source, node.test, new_cmp))
    return out


def _fix_while_le_k(source):
    """while len(acc) <= k  ->  while len(acc) < k (off-by-one count bound)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.While) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.LtE)):
            continue
        left = node.test.left
        if not (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                and left.func.id == "len"):
            continue
        right = node.test.comparators[0]
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        new_cmp = source[ls:le] + " < " + source[rs:re_]
        out.append(_splice(source, node.test, new_cmp))
    return out


def _fix_index_compare(source):
    """for i in range(len(lst)): if i == X   -> should compare lst[i] == X."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)):
            continue
        it = node.iter
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                and it.func.id == "range" and len(it.args) == 1):
            continue
        inner = it.args[0]
        if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                and inner.func.id == "len" and len(inner.args) == 1
                and isinstance(inner.args[0], ast.Name)):
            continue
        list_name = inner.args[0].id
        loop_var = node.target.id
        for n in ast.walk(node):
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                left = n.left
                if isinstance(left, ast.Name) and left.id == loop_var:
                    new_left = f"{list_name}[{loop_var}]"
                    s, e = _span(source, left)
                    out.append(source[:s] + new_left + source[e:])
    return out


def _fix_range_neg_bound(source):
    """range(-len(x), -1) skips the last element; should be range(-len(x), 0)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "range" and len(node.args) == 2):
            continue
        a0, a1 = node.args
        if not (isinstance(a0, ast.UnaryOp) and isinstance(a0.op, ast.USub)
                and isinstance(a0.operand, ast.Call)
                and isinstance(a0.operand.func, ast.Name) and a0.operand.func.id == "len"):
            continue
        if (isinstance(a1, ast.UnaryOp) and isinstance(a1.op, ast.USub)
                and isinstance(a1.operand, ast.Constant) and a1.operand.value == 1):
            s, e = _span(source, a1)
            out.append(source[:s] + "0" + source[e:])
    return out


def _fix_counter_in_if(source):
    """counter += 1 placed inside the 'found' branch (so it only increments
    on a hit, with no break) should be moved after the loop, with a break
    left in its place."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.If):
            continue
        if_node = node.body[0]
        body = if_node.body
        if len(body) < 2:
            continue
        last = body[-1]
        if not (isinstance(last, ast.AugAssign) and isinstance(last.op, ast.Add)
                and isinstance(last.target, ast.Name)):
            continue
        if any(isinstance(s, ast.Break) for s in body):
            continue
        enclosing_while = None
        for n in ast.walk(tree):
            if isinstance(n, ast.While) and _contains(n, node):
                enclosing_while = n
                break
        if enclosing_while is None:
            continue
        counter_name = last.target.id
        names_in_test = {nn.id for nn in ast.walk(enclosing_while.test) if isinstance(nn, ast.Name)}
        if counter_name not in names_in_test:
            continue
        s_last, e_last = _span(source, last)
        s_for, e_for = _span(source, node)
        aug_text = source[s_last:e_last]
        indent = " " * node.col_offset
        new_source = source[:e_for] + "\n" + indent + aug_text + source[e_for:]
        break_indent = " " * last.col_offset
        new_source = new_source[:s_last] + break_indent + "break" + new_source[e_last:]
        out.append(new_source)
    return out


def _fix_index_filter_output(source):
    """A leftover-list filter using .index(n) < k is a broken way to grab
    the top k; replace it with slicing the real sorted accumulator."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        body = func.body
        for i, stmt in enumerate(body):
            if not (isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.ListComp)):
                continue
            comp = stmt.value
            if len(comp.generators) != 1 or not isinstance(comp.generators[0].iter, ast.Name):
                continue
            gen = comp.generators[0]
            found = False
            for cond in gen.ifs:
                if (isinstance(cond, ast.Compare) and len(cond.ops) == 1
                        and isinstance(cond.ops[0], ast.Lt)):
                    left = cond.left
                    if (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                            and left.func.attr == "index"):
                        found = True
            if not found:
                continue
            if i + 1 >= len(body) or not isinstance(body[i + 1], ast.Return):
                continue
            ret = body[i + 1]
            if not (len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
                continue
            target_name = stmt.targets[0].id
            if not (isinstance(ret.value, ast.Name) and ret.value.id == target_name):
                continue
            acc_name = None
            for s in body[:i]:
                for n in ast.walk(s):
                    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                            and n.func.attr == "append" and isinstance(n.func.value, ast.Name)):
                        acc_name = n.func.value.id
            if not acc_name:
                continue
            s_start, _ = _span(source, stmt)
            _, e_end = _span(source, ret)
            out.append(source[:s_start] + f"return {acc_name}[:k]" + source[e_end:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="track_var_misuse_after_selection_loop",
                apply=_fix_track_var_misuse,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_wrong_accumulator_var",
                apply=_fix_return_wrong_var,
                symptoms=("wrong",),
            ),
            Rule(
                name="typo_undefined_name",
                apply=_fix_typo_name,
                symptoms=("err:NameError",),
            ),
            Rule(
                name="min_tracking_should_be_max",
                apply=_fix_min_tracking,
                symptoms=("wrong",),
            ),
            Rule(
                name="while_len_lte_should_be_lt",
                apply=_fix_while_le_k,
                symptoms=("wrong",),
            ),
            Rule(
                name="index_var_compared_instead_of_value",
                apply=_fix_index_compare,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="range_negative_bound_off_by_one",
                apply=_fix_range_neg_bound,
                symptoms=("wrong",),
            ),
            Rule(
                name="counter_increment_misplaced_in_if",
                apply=_fix_counter_in_if,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="index_based_filter_output_wrong",
                apply=_fix_index_filter_output,
                symptoms=("wrong",),
            ),
        ]