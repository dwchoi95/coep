import ast

from src.core.repair import Rule


# ---------------------------------------------------------------- helpers --

def _span(source, node):
    """(start, end) char offsets of node in source."""
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _line_bounds(source, node):
    """Start of node's first line .. start of line following node's last line."""
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    line_start = starts[node.lineno - 1]
    line_end = starts[node.end_lineno] if node.end_lineno < len(starts) else len(source)
    return line_start, line_end


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _safe_parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _apply_node_edits(source, edits):
    """edits: list of (node, replacement_text)."""
    spans = []
    for node, text in edits:
        s, e = _span(source, node)
        spans.append((s, e, text))
    spans.sort(key=lambda x: x[0], reverse=True)
    out = source
    for s, e, text in spans:
        out = out[:s] + text + out[e:]
    return out


def _apply_raw_edits(source, edits):
    """edits: list of (start, end, text)."""
    spans = sorted(edits, key=lambda x: x[0], reverse=True)
    out = source
    for s, e, text in spans:
        out = out[:s] + text + out[e:]
    return out


def _functions(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _names_in_target(t, out):
    if isinstance(t, ast.Name):
        out.add(t.id)
    elif isinstance(t, (ast.Tuple, ast.List)):
        for e in t.elts:
            _names_in_target(e, out)


def _lev(a, b):
    if a == b:
        return 0
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, cb in enumerate(b, 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
            prev = cur
    return dp[-1]


_BUILTINS = {
    'len', 'max', 'min', 'range', 'list', 'print', 'sorted', 'sort', 'int',
    'float', 'str', 'abs', 'sum', 'True', 'False', 'None', 'enumerate',
    'tuple', 'set', 'dict', 'bool', 'type',
}


def _max_pattern(for_node):
    """Detect: for <loopvar> in X: if <loopvar> > <extremum>: <extremum> = <loopvar>"""
    if not isinstance(for_node.target, ast.Name):
        return None
    loopvar = for_node.target.id
    for stmt in for_node.body:
        if not isinstance(stmt, ast.If):
            continue
        test = stmt.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            continue
        if not isinstance(test.ops[0], ast.Gt):
            continue
        if not (isinstance(test.left, ast.Name) and test.left.id == loopvar):
            continue
        comparator = test.comparators[0]
        for s2 in stmt.body:
            if (isinstance(s2, ast.Assign) and len(s2.targets) == 1
                    and isinstance(s2.targets[0], ast.Name)
                    and isinstance(s2.value, ast.Name) and s2.value.id == loopvar):
                return {
                    'loopvar': loopvar,
                    'extremum': s2.targets[0].id,
                    'comparator': comparator,
                    'if_node': stmt,
                }
    return None


def _stmt_lists(tree):
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            lst = getattr(node, field, None)
            if isinstance(lst, list) and lst and isinstance(lst[0], ast.stmt):
                yield lst


def _find_block_with(tree, target):
    for lst in _stmt_lists(tree):
        if target in lst:
            return lst, lst.index(target)
    return None, -1


# ---------------------------------------------------------------- rules ---

def fix_typo_undefined_name(source):
    """Replace an undefined Name with the single, structurally-similar defined
    name in the same function (NameError-causing typos)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in _functions(tree):
        defined = {a.arg for a in fn.args.args}
        defined.add(fn.name)
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    _names_in_target(t, defined)
            elif isinstance(node, ast.AugAssign):
                _names_in_target(node.target, defined)
            elif isinstance(node, ast.For):
                _names_in_target(node.target, defined)
            elif isinstance(node, ast.comprehension):
                _names_in_target(node.target, defined)
        edits = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                nm = node.id
                if nm in defined or nm in _BUILTINS:
                    continue
                cands = []
                for d in defined:
                    if d == nm:
                        continue
                    if _lev(nm, d) <= 2:
                        cands.append(d)
                    elif len(nm) >= 3 and (nm in d or d in nm):
                        cands.append(d)
                cands = list(set(cands))
                if len(cands) == 1:
                    edits.append((node, cands[0]))
        if edits:
            new_src = _apply_node_edits(source, edits)
            if new_src != source:
                out.append(new_src)
    return out


def fix_stale_loopvar_reference_after_loop(source):
    """After a correct max-finding for-loop, following .remove()/.append()
    calls mistakenly use the loop variable instead of the running extremum."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for lst in _stmt_lists(tree):
        for idx, node in enumerate(lst):
            if not isinstance(node, ast.For):
                continue
            pat = _max_pattern(node)
            if pat is None:
                continue
            loopvar, extremum = pat['loopvar'], pat['extremum']
            if loopvar == extremum:
                continue
            for after in lst[idx + 1:]:
                for sub in ast.walk(after):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr in ('remove', 'append') and len(sub.args) == 1):
                        arg = sub.args[0]
                        if isinstance(arg, ast.Name) and arg.id == loopvar:
                            edits.append((arg, extremum))
    if not edits:
        return []
    new_src = _apply_node_edits(source, edits)
    return [new_src] if new_src != source else []


def fix_stale_comparison_reference(source):
    """Comparison inside a max-finding for-loop re-derives the initial value
    (e.g. lst[0]) instead of comparing against the running extremum variable."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        pat = _max_pattern(node)
        if pat is None:
            continue
        comparator = pat['comparator']
        loopvar, extremum = pat['loopvar'], pat['extremum']
        if loopvar == extremum:
            continue
        if isinstance(comparator, ast.Name) and comparator.id == extremum:
            continue
        if isinstance(comparator, (ast.Subscript, ast.Call, ast.Attribute)):
            edits.append((comparator, extremum))
    if not edits:
        return []
    new_src = _apply_node_edits(source, edits)
    return [new_src] if new_src != source else []


def hoist_loop_init_out_of_for(source):
    """The running extremum's initialisation sits as the first statement
    *inside* the for-loop (so it resets every iteration); hoist it above."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not node.body:
            continue
        first = node.body[0]
        if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)):
            continue
        candidate_var = first.targets[0].id
        pat = _max_pattern(node)
        if pat is None or pat['extremum'] != candidate_var or pat['loopvar'] == candidate_var:
            continue
        s, e = _span(source, first)
        assign_text = source[s:e]
        rm_start, rm_end = _line_bounds(source, first)
        for_line_start, _ = _line_bounds(source, node)
        indent = ' ' * node.col_offset
        edits.append((rm_start, rm_end, ''))
        edits.append((for_line_start, for_line_start, indent + assign_text + '\n'))
    if not edits:
        return []
    new_src = _apply_raw_edits(source, edits)
    return [new_src] if new_src != source else []


def insert_missing_remove_call(source):
    """A while-loop extracts the max via a for-loop and appends it to an
    accumulator, but never removes it from the source list (infinite loop)."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for wh in ast.walk(tree):
        if not isinstance(wh, ast.While):
            continue
        for_node = None
        for stmt in wh.body:
            if isinstance(stmt, ast.For):
                for_node = stmt
                break
        if for_node is None:
            continue
        pat = _max_pattern(for_node)
        if pat is None:
            continue
        extremum = pat['extremum']
        if not isinstance(for_node.iter, ast.Name):
            continue
        iter_name = for_node.iter.id

        already = False
        for sub in ast.walk(wh):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == 'remove' and len(sub.args) == 1
                    and isinstance(sub.args[0], ast.Name) and sub.args[0].id == extremum):
                already = True
                break
        if already:
            continue

        anchor = None
        for stmt in wh.body:
            if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Attribute)
                    and stmt.value.func.attr == 'append'
                    and len(stmt.value.args) == 1
                    and isinstance(stmt.value.args[0], ast.Name)
                    and stmt.value.args[0].id == extremum):
                anchor = stmt
        if anchor is None:
            continue
        _, line_end = _line_bounds(source, anchor)
        indent = ' ' * anchor.col_offset
        edits.append((line_end, line_end, indent + f"{iter_name}.remove({extremum})\n"))
    if not edits:
        return []
    new_src = _apply_raw_edits(source, edits)
    return [new_src] if new_src != source else []


def fix_final_slice_bound(source):
    """Final slice uses a hard-coded literal or an off-by-one k+1/k-1 bound
    instead of plain k."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for fn in _functions(tree):
        if len(fn.args.args) < 2:
            continue
        k_name = fn.args.args[-1].arg
        for node in ast.walk(fn):
            if not isinstance(node, ast.Subscript):
                continue
            sl = node.slice
            if not isinstance(sl, ast.Slice) or sl.upper is None:
                continue
            upper = sl.upper
            fix = None
            if isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                fix = k_name
            elif isinstance(upper, ast.BinOp) and isinstance(upper.op, (ast.Add, ast.Sub)):
                if (isinstance(upper.left, ast.Name) and upper.left.id == k_name
                        and isinstance(upper.right, ast.Constant)):
                    fix = k_name
            if fix:
                edits.append((upper, fix))
    if not edits:
        return []
    new_src = _apply_node_edits(source, edits)
    return [new_src] if new_src != source else []


def fix_len_loop_offbyone(source):
    """A while-condition `len(acc) <= k` should be `len(acc) < k`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    edits = []
    for fn in _functions(tree):
        if len(fn.args.args) < 2:
            continue
        k_name = fn.args.args[-1].arg
        for node in ast.walk(fn):
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.LtE)
                    and isinstance(node.left, ast.Call)
                    and isinstance(node.left.func, ast.Name) and node.left.func.id == 'len'
                    and isinstance(node.comparators[0], ast.Name)
                    and node.comparators[0].id == k_name):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " < " + source[rs:re_]
                edits.append((node, new_cmp))
    if not edits:
        return []
    new_src = _apply_node_edits(source, edits)
    return [new_src] if new_src != source else []


def add_missing_return(source):
    """Function builds an accumulator via .append() in a loop but never
    returns it."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in _functions(tree):
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(fn))
        if has_return:
            continue
        accs = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.List) and not node.value.elts):
                accs.add(node.targets[0].id)
        appended = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in accs):
                appended.add(node.func.value.id)
        if len(appended) != 1 or not fn.body:
            continue
        acc = next(iter(appended))
        last = fn.body[-1]
        _, line_end = _line_bounds(source, last)
        indent = ' ' * fn.body[0].col_offset
        new_src = source[:line_end] + indent + f"return {acc}\n" + source[line_end:]
        if new_src != source:
            out.append(new_src)
    return out


def fix_unused_recursive_call(source):
    """A recursive call's result is computed but discarded (bare expression
    statement) instead of being folded into the accumulator."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in _functions(tree):
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name) and node.value.func.id == fn.name):
                continue
            lst, idx = _find_block_with(fn, node)
            if lst is None:
                continue
            acc = None
            for stmt in reversed(lst[:idx]):
                if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                        and isinstance(stmt.value.func, ast.Attribute)
                        and stmt.value.func.attr == 'append'
                        and isinstance(stmt.value.func.value, ast.Name)):
                    acc = stmt.value.func.value.id
                    break
            if acc is None:
                continue
            s, e = _span(source, node.value)
            call_text = source[s:e]
            new_text = f"{acc} += {call_text}"
            new_src = _splice(source, node, new_text)
            if new_src != source:
                out.append(new_src)
    return out


def fix_return_source_variable(source):
    """Final return slices the (mutated/shrunk) original parameter instead
    of the accumulator list that was actually built up."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in _functions(tree):
        if not fn.args.args:
            continue
        first_param = fn.args.args[0].arg
        accs = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.List) and not node.value.elts):
                accs.add(node.targets[0].id)
        appended = set()
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'append' and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in accs):
                appended.add(node.func.value.id)
        candidates = appended - {first_param}
        if len(candidates) != 1:
            continue
        acc = next(iter(candidates))
        for node in ast.walk(fn):
            if (isinstance(node, ast.Return) and isinstance(node.value, ast.Subscript)
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == first_param):
                new_src = _splice(source, node.value.value, acc)
                if new_src != source:
                    out.append(new_src)
    return out


# ---------------------------------------------------------------- Fixer ---

class Fixer:
    def rules(self):
        return [
            Rule(name="fix_typo_undefined_name",
                 apply=fix_typo_undefined_name,
                 symptoms=("err:NameError",)),
            Rule(name="fix_stale_loopvar_reference_after_loop",
                 apply=fix_stale_loopvar_reference_after_loop,
                 symptoms=("wrong",)),
            Rule(name="fix_stale_comparison_reference",
                 apply=fix_stale_comparison_reference,
                 symptoms=("wrong",)),
            Rule(name="hoist_loop_init_out_of_for",
                 apply=hoist_loop_init_out_of_for,
                 symptoms=("wrong", "timeout")),
            Rule(name="insert_missing_remove_call",
                 apply=insert_missing_remove_call,
                 symptoms=("timeout", "wrong")),
            Rule(name="fix_final_slice_bound",
                 apply=fix_final_slice_bound,
                 symptoms=("wrong",)),
            Rule(name="fix_len_loop_offbyone",
                 apply=fix_len_loop_offbyone,
                 symptoms=("wrong",)),
            Rule(name="add_missing_return",
                 apply=add_missing_return,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_unused_recursive_call",
                 apply=fix_unused_recursive_call,
                 symptoms=("wrong",)),
            Rule(name="fix_return_source_variable",
                 apply=fix_return_source_variable,
                 symptoms=("wrong",)),
        ]