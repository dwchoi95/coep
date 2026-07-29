"""
Repair rules for the "Sequential Search" assignment.

Each rule targets one recurring misconception observed in the buggy
submissions, expressed as a small, local AST-guided source-span edit.
"""

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


# ---------------------------------------------------------------------------
# 1. `seq == () or []` / `seq == [] or ()` / `... and []` -- the bare empty
#    literal is never turned into a real comparison, so it is always truthy
#    (falsy for `[]`... regardless, it doesn't test `seq`).  Turn the bare
#    literal into an explicit `seq == <literal>` comparison.
# ---------------------------------------------------------------------------
def _fix_empty_seq_boolop(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BoolOp):
            continue
        values = node.values
        compare_name = None
        for v in values:
            if (isinstance(v, ast.Compare) and isinstance(v.left, ast.Name)
                    and len(v.ops) == 1 and isinstance(v.ops[0], ast.Eq)
                    and len(v.comparators) == 1
                    and isinstance(v.comparators[0], (ast.Tuple, ast.List))
                    and len(v.comparators[0].elts) == 0):
                compare_name = v.left.id
                break
        if compare_name is None:
            continue
        bare_literals = [v for v in values
                         if isinstance(v, (ast.Tuple, ast.List)) and len(v.elts) == 0]
        if not bare_literals:
            continue
        bare_literals.sort(key=lambda v: _span(source, v)[0], reverse=True)
        candidate = source
        for v in bare_literals:
            s, e = _span(candidate, v)
            lit_src = candidate[s:e]
            candidate = candidate[:s] + f"{compare_name} == {lit_src}" + candidate[e:]
        if candidate != source:
            out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# 2. An unconditional `return` sits *inside* the for-loop body (after an
#    `if ...: return i`), so it fires on the very first iteration.  Move it
#    out to after the loop.
# ---------------------------------------------------------------------------
def _dedent_trailing_return(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    lines = source.splitlines(keepends=True)
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if len(node.body) < 2 or not isinstance(node.body[-1], ast.Return):
            continue
        if not any(isinstance(s, ast.If) for s in node.body[:-1]):
            continue
        last = node.body[-1]
        if last.lineno != last.end_lineno:
            continue
        if last.lineno - 1 >= len(lines):
            continue
        for_line = lines[node.lineno - 1]
        for_indent = len(for_line) - len(for_line.lstrip())
        ret_idx = last.lineno - 1
        ret_line = lines[ret_idx]
        ret_indent = len(ret_line) - len(ret_line.lstrip())
        if ret_indent <= for_indent:
            continue
        new_lines = lines[:ret_idx] + lines[ret_idx + 1:]
        insert_idx = ret_idx
        new_stmt_line = (' ' * for_indent) + ret_line.strip() + '\n'
        new_lines = new_lines[:insert_idx] + [new_stmt_line] + new_lines[insert_idx:]
        candidate = ''.join(new_lines)
        if candidate != source:
            out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# 3. The search loop simply falls off the end without ever returning
#    `len(seq)` for values bigger than everything.  Append the missing
#    `return len(seq)` right after the loop.
# ---------------------------------------------------------------------------
def _append_missing_return_len(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    lines = source.splitlines(keepends=True)
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        last = func.body[-1]
        if not isinstance(last, ast.For):
            continue
        if not any(isinstance(s, ast.If) for s in last.body):
            continue
        seq_src = None
        it = last.iter
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name):
            if it.func.id == 'enumerate' and it.args:
                s, e = _span(source, it.args[0])
                seq_src = source[s:e]
            elif (it.func.id == 'range' and it.args
                  and isinstance(it.args[0], ast.Call)
                  and isinstance(it.args[0].func, ast.Name)
                  and it.args[0].func.id == 'len' and it.args[0].args):
                s, e = _span(source, it.args[0].args[0])
                seq_src = source[s:e]
        if seq_src is None:
            if len(func.args.args) >= 2:
                seq_src = func.args.args[1].arg
            else:
                continue
        if last.lineno - 1 >= len(lines):
            continue
        for_line = lines[last.lineno - 1]
        for_indent = len(for_line) - len(for_line.lstrip())
        indent_str = ' ' * for_indent
        s_for, e_for = _span(source, last)
        line_end = source.find('\n', e_for)
        insertion = f"{indent_str}return len({seq_src})\n"
        if line_end == -1:
            sep = '' if source.endswith('\n') else '\n'
            candidate = source + sep + insertion
        else:
            insert_pos = line_end + 1
            candidate = source[:insert_pos] + insertion + source[insert_pos:]
        if candidate != source:
            out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# 4. Strict-vs-nonstrict comparison confusion around the value that gets
#    returned as the insertion index.  `x < elem` / `elem > x` should be
#    non-strict so that equal values land at the earlier index.
# ---------------------------------------------------------------------------
def _acceptable_index_body(first):
    if isinstance(first, ast.Return) and isinstance(first.value, ast.Name):
        return True
    if (isinstance(first, ast.Assign) and len(first.targets) == 1
            and isinstance(first.targets[0], ast.Name)
            and isinstance(first.value, ast.Constant) and first.value is True):
        return True
    return False


def _relax_index_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        if not node.body or not _acceptable_index_body(node.body[0]):
            continue
        op = test.ops[0]
        left, right = test.left, test.comparators[0]
        new_op_text = None
        if isinstance(op, ast.Lt) and isinstance(left, ast.Name) and left.id == 'x':
            new_op_text = '<='
        elif isinstance(op, ast.Gt) and isinstance(right, ast.Name) and right.id == 'x':
            new_op_text = '>='
        if new_op_text is None:
            continue
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        new_test = source[ls:le] + f" {new_op_text} " + source[rs:re_]
        out.append(_splice(source, test, new_test))
    return out


# ---------------------------------------------------------------------------
# 5. The mirrored mistake: the branch that returns `len(seq)` should require
#    a *strict* greater-than, not `>=` (otherwise the equal-to-last-element
#    case is mishandled).
# ---------------------------------------------------------------------------
def _tighten_len_compare(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        if not isinstance(test.ops[0], ast.GtE):
            continue
        left = test.left
        if not (isinstance(left, ast.Name) and left.id == 'x'):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not (isinstance(first, ast.Return) and isinstance(first.value, ast.Call)
                and isinstance(first.value.func, ast.Name) and first.value.func.id == 'len'):
            continue
        right = test.comparators[0]
        ls, le = _span(source, left)
        rs, re_ = _span(source, right)
        new_test = source[ls:le] + " > " + source[rs:re_]
        out.append(_splice(source, test, new_test))
    return out


# ---------------------------------------------------------------------------
# 6. `for i in range(seq)` / `for i in len(range(seq))` -- the len() is
#    missing or the range()/len() calls are nested in the wrong order.
# ---------------------------------------------------------------------------
def _fix_range_len(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        it = node.iter
        new_it_src = None
        if (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                and it.func.id == 'range' and len(it.args) == 1
                and isinstance(it.args[0], ast.Name)):
            new_it_src = f"range(len({it.args[0].id}))"
        elif (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
              and it.func.id == 'len' and len(it.args) == 1
              and isinstance(it.args[0], ast.Call)
              and isinstance(it.args[0].func, ast.Name)
              and it.args[0].func.id == 'range' and len(it.args[0].args) == 1
              and isinstance(it.args[0].args[0], ast.Name)):
            new_it_src = f"range(len({it.args[0].args[0].id}))"
        if new_it_src:
            out.append(_splice(source, it, new_it_src))
    return out


# ---------------------------------------------------------------------------
# 7. `for i, elem in seq:` -- forgot to wrap the sequence in `enumerate(...)`.
# ---------------------------------------------------------------------------
def _fix_missing_enumerate(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.For) and isinstance(node.target, ast.Tuple)
                and len(node.target.elts) == 2 and isinstance(node.iter, ast.Name)):
            new_it = f"enumerate({node.iter.id})"
            out.append(_splice(source, node.iter, new_it))
    return out


# ---------------------------------------------------------------------------
# 8. Counting loop that compares in the wrong direction:
#    `if x < elem: counter += 1  else: break` should compare `x > elem`.
# ---------------------------------------------------------------------------
def _flip_counting_direction(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        op = test.ops[0]
        if not isinstance(op, (ast.Lt, ast.Gt)):
            continue
        if not (isinstance(test.left, ast.Name) and test.left.id == 'x'):
            continue
        if not node.body or not node.orelse:
            continue
        has_incr = any(isinstance(s, ast.AugAssign) for s in node.body)
        has_break = any(isinstance(s, ast.Break) for s in node.orelse)
        if not (has_incr and has_break):
            continue
        new_op = '>' if isinstance(op, ast.Lt) else '<'
        ls, le = _span(source, test.left)
        rs, re_ = _span(source, test.comparators[0])
        new_test = source[ls:le] + f" {new_op} " + source[rs:re_]
        out.append(_splice(source, test, new_test))
    return out


# ---------------------------------------------------------------------------
# 9. `position += position` (or any `x += x`) should be `x += 1`.
# ---------------------------------------------------------------------------
def _fix_self_increment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add)
                and isinstance(node.target, ast.Name) and isinstance(node.value, ast.Name)
                and node.target.id == node.value.id):
            out.append(_splice(source, node.value, "1"))
    return out


# ---------------------------------------------------------------------------
# 10. Missing empty-sequence guard before indexing `seq[0]` / `seq[-1]`.
# ---------------------------------------------------------------------------
def _insert_empty_guard(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != 'search':
            continue
        if len(func.args.args) < 2:
            continue
        seqname = func.args.args[1].arg
        seg = ast.get_source_segment(source, func) or ""
        flat = seg.replace(' ', '')
        guard_markers = (
            f"len({seqname})", f"{seqname}==()", f"{seqname}==[]",
            f"not{seqname}", f"{seqname}==None",
        )
        if any(m in flat for m in guard_markers):
            continue
        uses_index0 = False
        for node in ast.walk(func):
            if isinstance(node, ast.Subscript):
                nseg = (ast.get_source_segment(source, node) or "").replace(' ', '')
                if nseg.startswith(seqname + "[0]") or nseg.startswith(seqname + "[-1]"):
                    uses_index0 = True
                    break
        if not uses_index0 or not func.body:
            continue
        first_stmt = func.body[0]
        s, _ = _span(source, first_stmt)
        line_start = source.rfind('\n', 0, s) + 1
        indent_str = source[line_start:s]
        if indent_str.strip():
            indent_str = ' ' * (len(indent_str) - len(indent_str.lstrip()))
        insertion = f"{indent_str}if not {seqname}:\n{indent_str}    return 0\n"
        candidate = source[:line_start] + insertion + source[line_start:]
        if candidate != source:
            out.append(candidate)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="empty_seq_bare_literal_in_boolop",
                apply=_fix_empty_seq_boolop,
                symptoms=("wrong", "err:IndexError", "err:TypeError"),
            ),
            Rule(
                name="dedent_trailing_return_out_of_loop",
                apply=_dedent_trailing_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="append_missing_return_len_after_loop",
                apply=_append_missing_return_len,
                symptoms=("wrong",),
            ),
            Rule(
                name="relax_strict_compare_for_index_return",
                apply=_relax_index_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="tighten_gte_compare_for_len_return",
                apply=_tighten_len_compare,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_range_len_iteration",
                apply=_fix_range_len,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="fix_missing_enumerate",
                apply=_fix_missing_enumerate,
                symptoms=("wrong", "err:TypeError", "err:ValueError"),
            ),
            Rule(
                name="flip_counting_loop_direction",
                apply=_flip_counting_direction,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_self_increment_should_be_plus_one",
                apply=_fix_self_increment,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="insert_empty_sequence_guard",
                apply=_insert_empty_guard,
                symptoms=("err:IndexError", "wrong"),
            ),
        ]