"""
Repair module for the "Sorting Tuples" (sort_age) assignment.

Each Rule targets one recurring misconception observed across buggy
submissions implementing a selection-sort-style extraction of the
oldest/largest tuple from a list of (gender, age) pairs. Rules are
structural (AST-located) and apply minimal source splices.
"""

import ast
import builtins as _builtins_mod

from src.core.repair import Rule


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _span(source, node):
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _apply_spans(source, spans):
    spans = sorted(spans, key=lambda t: t[0], reverse=True)
    out = source
    for s, e, text in spans:
        out = out[:s] + text + out[e:]
    return out


def _line_indent(source, node):
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[:len(line) - len(line.lstrip(' \t'))]


def _with_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    return tree


def _enclosing_function(node):
    cur = getattr(node, 'parent', None)
    while cur is not None and not isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
        cur = getattr(cur, 'parent', None)
    return cur


def _subscript_index(node):
    sl = node.slice
    if hasattr(ast, 'Index') and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _is_index0(node):
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Name):
        return False
    idx = _subscript_index(node)
    return isinstance(idx, ast.Constant) and idx.value == 0


_BUILTINS = set(dir(_builtins_mod)) | {'True', 'False', 'None'}


def _defined_names(func):
    names = set(a.arg for a in func.args.args)
    names.add(func.name)
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
        elif isinstance(node, ast.AugAssign):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, ast.comprehension):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    names.add(n.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            for a in node.args.args:
                names.add(a.arg)
        elif isinstance(node, ast.withitem):
            if node.optional_vars:
                for n in ast.walk(node.optional_vars):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
    return names


def _find_skeletons(tree):
    """Locate the common selection-extraction pattern:

        while lst:
            track = something[0]
            for x in lst:
                if <test>:
                    <body updating track>
            ... remove/append ...
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            body = node.body
            if not body:
                continue
            first = body[0]
            track = None
            if isinstance(first, ast.Assign) and len(first.targets) == 1 \
               and isinstance(first.targets[0], ast.Name) and _is_index0(first.value):
                track = first.targets[0].id
            if track is None:
                continue
            for stmt in body:
                if isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name):
                    loopvar = stmt.target.id
                    for sub in stmt.body:
                        if isinstance(sub, ast.If):
                            out.append({'while': node, 'assign': first, 'for': stmt,
                                        'if': sub, 'track': track, 'loopvar': loopvar})
    return out


def _safe(fn):
    def wrapper(source):
        try:
            res = fn(source)
        except Exception:
            return []
        return [r for r in res if r != source]
    return wrapper


# ---------------------------------------------------------------------------
# Rule: comparison direction wrong in selection loop (finds min instead of max)
# ---------------------------------------------------------------------------

def _matches(expr, name):
    if isinstance(expr, ast.Name) and expr.id == name:
        return True
    if isinstance(expr, ast.Subscript) and isinstance(expr.value, ast.Name) and expr.value.id == name:
        return True
    return False


_OP_FLIP = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}
_OP_TEXT = {ast.Lt: '<', ast.Gt: '>', ast.LtE: '<=', ast.GtE: '>='}


@_safe
def fix_selection_direction(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    if '.reverse(' in source or '[::-1]' in source or 'reverse=True' in source:
        return []
    skeletons = _find_skeletons(tree)
    spans = []
    for sk in skeletons:
        test = sk['if'].test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        op = test.ops[0]
        if type(op) not in _OP_FLIP:
            continue
        left, right = test.left, test.comparators[0]
        track, loopvar = sk['track'], sk['loopvar']
        if _matches(left, track) and _matches(right, loopvar):
            side = 'left'
        elif _matches(left, loopvar) and _matches(right, track):
            side = 'right'
        else:
            continue
        wrong = (side == 'left' and type(op) in (ast.Gt, ast.GtE)) or \
                (side == 'right' and type(op) in (ast.Lt, ast.LtE))
        if not wrong:
            continue
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        between = source[le:rs]
        old_txt = _OP_TEXT[type(op)]
        new_txt = _OP_TEXT[_OP_FLIP[type(op)]]
        idx = between.find(old_txt)
        if idx == -1:
            continue
        new_between = between[:idx] + new_txt + between[idx + len(old_txt):]
        spans.append((le, rs, new_between))
    if not spans:
        return []
    return [_apply_spans(source, spans)]


# ---------------------------------------------------------------------------
# Rule: remove()/append() after the loop use the loop variable instead of
# the tracked best variable.
# ---------------------------------------------------------------------------

@_safe
def fix_postloop_wrong_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    skeletons = _find_skeletons(tree)
    spans = []
    for sk in skeletons:
        track, loopvar = sk['track'], sk['loopvar']
        whilenode, fornode = sk['while'], sk['for']
        idx = whilenode.body.index(fornode)
        after = whilenode.body[idx + 1:]
        for stmt in after:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                   and n.func.attr in ('remove', 'append') and len(n.args) == 1:
                    arg = n.args[0]
                    if isinstance(arg, ast.Name) and arg.id == loopvar:
                        s, e = _span(source, arg)
                        spans.append((s, e, track))
    if not spans:
        return []
    return [_apply_spans(source, spans)]


# ---------------------------------------------------------------------------
# Rule: undefined / mistyped name used where the tracked variable belongs
# (inside the if-test or in the post-loop remove/append calls).
# ---------------------------------------------------------------------------

@_safe
def fix_undefined_to_track(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    skeletons = _find_skeletons(tree)
    spans = []
    cache = {}
    for sk in skeletons:
        func = _enclosing_function(sk['while'])
        if func is None:
            continue
        if id(func) not in cache:
            cache[id(func)] = _defined_names(func)
        defined = cache[id(func)]
        track, loopvar = sk['track'], sk['loopvar']
        whilenode, fornode = sk['while'], sk['for']
        idx = whilenode.body.index(fornode)
        targets = [sk['if'].test] + whilenode.body[idx + 1:]
        for tn in targets:
            for n in ast.walk(tn):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    if n.id not in defined and n.id not in _BUILTINS:
                        s, e = _span(source, n)
                        spans.append((s, e, track))
    if not spans:
        return []
    return [_apply_spans(source, spans)]


# ---------------------------------------------------------------------------
# Rule: backwards assignment inside the if-body (candidate = track instead
# of track = candidate).
# ---------------------------------------------------------------------------

@_safe
def fix_backwards_assignment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    skeletons = _find_skeletons(tree)
    out = []
    for sk in skeletons:
        ifnode = sk['if']
        track, loopvar = sk['track'], sk['loopvar']
        if not ifnode.body:
            continue
        st = ifnode.body[0]
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) \
           and isinstance(st.value, ast.Name) and st.targets[0].id == loopvar and st.value.id == track:
            new_text = "{} = {}".format(track, loopvar)
            out.append(_splice(source, st, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: if-body is a stray expression (e.g. "a - b") where an assignment
# "track = loopvar" was intended.
# ---------------------------------------------------------------------------

@_safe
def fix_binop_should_be_assign(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    skeletons = _find_skeletons(tree)
    out = []
    for sk in skeletons:
        ifnode = sk['if']
        track, loopvar = sk['track'], sk['loopvar']
        if not ifnode.body:
            continue
        st = ifnode.body[0]
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.BinOp):
            l, r = st.value.left, st.value.right
            if isinstance(l, ast.Name) and isinstance(r, ast.Name):
                new_text = "{} = {}".format(track, loopvar)
                out.append(_splice(source, st, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: if-body assigns into a subscript of the tracked tuple instead of
# rebinding the whole tuple ("best[1] = cand[1]" -> "best = cand").
# ---------------------------------------------------------------------------

@_safe
def fix_subscript_assign(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    skeletons = _find_skeletons(tree)
    out = []
    for sk in skeletons:
        ifnode = sk['if']
        track, loopvar = sk['track'], sk['loopvar']
        if not ifnode.body:
            continue
        st = ifnode.body[0]
        if isinstance(st, ast.Assign) and len(st.targets) == 1:
            tgt, val = st.targets[0], st.value
            if isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name) and tgt.value.id == track \
               and isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name) and val.value.id == loopvar:
                new_text = "{} = {}".format(track, loopvar)
                out.append(_splice(source, st, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: function never returns -> append "return <accumulator>".
# ---------------------------------------------------------------------------

@_safe
def fix_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(func))
        if has_return:
            continue
        acc_name = None
        for st in func.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                if isinstance(st.value, ast.List) and len(st.value.elts) == 0:
                    acc_name = st.targets[0].id
                    break
        if acc_name is None or not func.body:
            continue
        last = func.body[-1]
        _, e = _span(source, last)
        indent = _line_indent(source, last)
        insertion = "\n" + indent + "return {}".format(acc_name)
        out.append(source[:e] + insertion + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule: a "return" is placed as the last statement inside a loop, causing
# an early exit after the first iteration -> dedent it to after the loop.
# ---------------------------------------------------------------------------

@_safe
def fix_return_inside_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.While, ast.For)):
            body = node.body
            if len(body) >= 2 and isinstance(body[-1], ast.Return):
                ret = body[-1]
                if ret.end_lineno != ret.lineno:
                    continue
                loop_indent = _line_indent(source, node)
                ret_indent = _line_indent(source, ret)
                if ret_indent != loop_indent and ret_indent.startswith(loop_indent) \
                   and len(ret_indent) > len(loop_indent):
                    lines = source.splitlines(keepends=True)
                    starts = [0]
                    for ln in lines:
                        starts.append(starts[-1] + len(ln))
                    line_idx = ret.lineno - 1
                    line = lines[line_idx]
                    stripped = line[len(ret_indent):]
                    new_line = loop_indent + stripped
                    s = starts[line_idx]
                    e = starts[line_idx + 1] if line_idx + 1 < len(starts) else len(source)
                    out.append(source[:s] + new_line + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule: ".reverse"/".sort" referenced without being called.
# ---------------------------------------------------------------------------

@_safe
def fix_uncalled_reverse_sort(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute) \
           and node.value.attr in ('reverse', 'sort'):
            txt = _text(source, node.value)
            out.append(_splice(source, node, txt + "()"))
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute) \
                and node.value.attr in ('reverse', 'sort'):
            obj_txt = _text(source, node.value.value)
            indent = _line_indent(source, node)
            new_text = "{}.{}()\n{}return {}".format(obj_txt, node.value.attr, indent, obj_txt)
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: ".removal(" typo for ".remove(".
# ---------------------------------------------------------------------------

@_safe
def fix_removal_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == 'removal':
            s, e = _span(source, node)
            obj_txt = _text(source, node.value)
            new_text = obj_txt + ".remove"
            out.append(source[:s] + new_text + source[e:])
    return out


# ---------------------------------------------------------------------------
# Rule: "X.pop[i]" (subscript) instead of "X.pop(i)" (call).
# ---------------------------------------------------------------------------

@_safe
def fix_pop_bracket(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == 'pop':
            idx_node = _subscript_index(node)
            idx_txt = _text(source, idx_node)
            obj_txt = _text(source, node.value)
            new_text = "{}({})".format(obj_txt, idx_txt)
            out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: off-by-one range(1, len(x)+1) -> range(len(x)).
# ---------------------------------------------------------------------------

@_safe
def fix_range_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'range' \
           and len(node.args) == 2:
            a0, a1 = node.args
            if isinstance(a0, ast.Constant) and a0.value == 1 and isinstance(a1, ast.BinOp) \
               and isinstance(a1.op, ast.Add):
                if isinstance(a1.left, ast.Call) and isinstance(a1.left.func, ast.Name) \
                   and a1.left.func.id == 'len' and isinstance(a1.right, ast.Constant) and a1.right.value == 1:
                    len_txt = _text(source, a1.left)
                    new_text = "range({})".format(len_txt)
                    out.append(_splice(source, node, new_text))
    return out


# ---------------------------------------------------------------------------
# Rule: missing guard for the empty-list case before indexing lst[0].
# ---------------------------------------------------------------------------

@_safe
def fix_empty_list_guard(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if not func.args.args or not func.body:
            continue
        param = func.args.args[0].arg
        first = func.body[0]
        if isinstance(first, ast.If):
            continue
        found = False
        for n in ast.walk(first):
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == param:
                idx = _subscript_index(n)
                if isinstance(idx, ast.Constant) and idx.value == 0:
                    found = True
                    break
        if not found:
            continue
        indent = _line_indent(source, first)
        s, _ = _span(source, first)
        guard = "if not {0}:\n{1}    return []\n{1}".format(param, indent)
        out.append(source[:s] + guard + source[s:])
    return out


# ---------------------------------------------------------------------------
# Rule: undefined name used where the (single) list parameter was meant.
# ---------------------------------------------------------------------------

@_safe
def fix_undefined_list_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if len(func.args.args) != 1:
            continue
        param = func.args.args[0].arg
        defined = _defined_names(func)
        spans = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in defined \
               and n.id not in _BUILTINS:
                parent = getattr(n, 'parent', None)
                is_list_ctx = False
                if isinstance(parent, ast.For) and parent.iter is n:
                    is_list_ctx = True
                if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute) \
                   and parent.func.value is n and parent.func.attr in ('remove', 'append', 'pop'):
                    is_list_ctx = True
                if isinstance(parent, ast.Subscript) and parent.value is n:
                    is_list_ctx = True
                if is_list_ctx:
                    s, e = _span(source, n)
                    spans.append((s, e, param))
        if spans:
            out.append(_apply_spans(source, spans))
    return out


# ---------------------------------------------------------------------------
# Rule: generic fallback for a single-candidate NameError typo fix.
# ---------------------------------------------------------------------------

def _edit_distance_le(a, b, limit):
    if abs(len(a) - len(b)) > limit:
        return False
    la, lb = len(a), len(b)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return dp[lb] <= limit


@_safe
def fix_undefined_name_fuzzy(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _with_parents(tree)
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        defined = _defined_names(func)
        candidates = sorted(defined)
        spans = []
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in defined \
               and n.id not in _BUILTINS:
                matches = [c for c in candidates if c != n.id and _edit_distance_le(n.id, c, 2)]
                if len(matches) == 1:
                    s, e = _span(source, n)
                    spans.append((s, e, matches[0]))
        if spans:
            out.append(_apply_spans(source, spans))
    return out


# ---------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="selection_wrong_direction",
                 apply=fix_selection_direction,
                 symptoms=("wrong",)),
            Rule(name="postloop_uses_loopvar_not_tracked",
                 apply=fix_postloop_wrong_var,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="undefined_name_should_be_tracked_var",
                 apply=fix_undefined_to_track,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="backwards_assignment_in_if",
                 apply=fix_backwards_assignment,
                 symptoms=("wrong",)),
            Rule(name="binop_should_be_assignment",
                 apply=fix_binop_should_be_assign,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="subscript_assign_should_be_name_assign",
                 apply=fix_subscript_assign,
                 symptoms=("wrong",)),
            Rule(name="missing_return_statement",
                 apply=fix_missing_return,
                 symptoms=("wrong",)),
            Rule(name="return_stuck_inside_loop",
                 apply=fix_return_inside_loop,
                 symptoms=("wrong",)),
            Rule(name="reverse_or_sort_not_called",
                 apply=fix_uncalled_reverse_sort,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="removal_typo_for_remove",
                 apply=fix_removal_typo,
                 symptoms=("err:AttributeError",)),
            Rule(name="pop_bracket_should_be_call",
                 apply=fix_pop_bracket,
                 symptoms=("err:TypeError",)),
            Rule(name="range_off_by_one",
                 apply=fix_range_off_by_one,
                 symptoms=("err:IndexError", "wrong")),
            Rule(name="missing_empty_list_guard",
                 apply=fix_empty_list_guard,
                 symptoms=("err:IndexError",)),
            Rule(name="undefined_name_should_be_list_param",
                 apply=fix_undefined_list_name,
                 symptoms=("err:NameError",)),
            Rule(name="undefined_name_fuzzy_typo",
                 apply=fix_undefined_name_fuzzy,
                 symptoms=("err:NameError",)),
        ]