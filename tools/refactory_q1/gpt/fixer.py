import ast
from src.core.repair import Rule

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


def _find_first(tree, pred):
    for n in ast.walk(tree):
        if pred(n):
            return n
    return None


def _ensure_indent_like(source, old_node, new_block_lines):
    s, e = _span(source, old_node)
    # Determine indentation from first line of the old node
    # Use line after last newline before s
    line_start = source.rfind("\n", 0, s) + 1
    indent = source[line_start:s]
    return "\n".join([indent + ln if ln else ln for ln in new_block_lines])


def _fix_for_early_return_to_after_loop(source):
    """
    Fix pattern:
        for ...:
            if ...: return i
            return len(seq)
    to:
        for ...:
            if ...: return i
        return len(seq)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            body = node.body
            if len(body) >= 2 and isinstance(body[-1], ast.Return):
                last_ret = body[-1]
                # Ensure last return is inside for-loop, likely len(seq)
                if (
                    isinstance(last_ret.value, ast.Call)
                    and isinstance(last_ret.value.func, ast.Name)
                    and last_ret.value.func.id == "len"
                    and len(last_ret.value.args) == 1
                ):
                    # Check previous statement contains the if/return i
                    prev = body[-2]
                    if isinstance(prev, ast.If):
                        # Look for any Return i within that If
                        inner = _find_first(
                            tree=tree,
                            pred=lambda n: False
                        )
                # We need to specifically recognize the sample: `if x<= seq[i]: return i` then `return len(seq)`
                # We'll do simpler checks:
                # - For loop contains an If with Return(i) (or Name 'i')
                # - last_ret returns len(seq)
                has_if_return_i = False
                ret_i_name = None
                for stmt in body:
                    if isinstance(stmt, ast.If):
                        for inner_stmt in ast.walk(stmt):
                            if isinstance(inner_stmt, ast.Return) and isinstance(inner_stmt.value, ast.Name):
                                has_if_return_i = True
                                ret_i_name = inner_stmt.value.id
                if not has_if_return_i:
                    continue
                # Ensure the return len(seq) is exactly last statement of for-body
                # and not present elsewhere outside the loop already
                # Remove last return from for-body and append after loop
                # Implement splice by:
                # - Replace for-body last element `return len(seq)` span with '' (remove line) and
                # - Insert `return len(seq)` just after for-loop node span.
                # But we must keep indentation and newlines; safest: replace the return statement text with ''.
                new_source = source
                # Remove last_ret text
                s, e = _span(new_source, last_ret)
                # Remove possibly trailing indentation; just delete statement range.
                # Ensure we don't leave trailing whitespace-only line by also trimming a following newline if present.
                # We'll delete up to next newline after e if that newline exists and is part of statement formatting.
                if e < len(new_source) and new_source[e:e+1] == "\n":
                    e2 = e + 1
                else:
                    e2 = e
                new_source = new_source[:s] + new_source[e2:]
                # Insert after loop: find end of for node and insert newline + `return len(seq)`
                for_end_s, for_end_e = _span(new_source, node)
                insert_pos = for_end_e
                # Determine indentation for insertion from for loop's header indentation
                line_start = new_source.rfind("\n", 0, for_end_s) + 1
                indent = new_source[line_start:for_end_s]
                # Actually indentation for statement after for-loop is same as `for` line's indentation,
                # which is indent before "for".
                # We'll compute from start of for node.
                for_start_s, _ = _span(new_source, node)
                header_line_start = new_source.rfind("\n", 0, for_start_s) + 1
                header_indent = new_source[header_line_start:for_start_s]
                # Determine return expression text as in original
                ret_expr_text = source[_span(source, last_ret.value)[0]:_span(source, last_ret.value)[1]]
                # Insert if not already exists immediately after (avoid duplicates)
                insertion = "\n" + header_indent + "return " + ret_expr_text
                new_source = new_source[:insert_pos] + insertion + new_source[insert_pos:]
                candidates.append(new_source)
    return candidates


def _fix_seq_none_to_zero_in_empty_return(source):
    """
    Fix pattern in sample:
        if seq == () or seq == []: return None
    to:
        ...: return 0
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            parent_if = None
            # Only apply if this return is within an if checking seq == () or seq == []
            # We'll check whether any ancestor If has a test that includes comparisons of seq to () or [].
            cur = node
            while True:
                # can't easily find parent via ast; use a coarse check: look for 'seq == () or seq == []' in nearby text
                s, e = _span(source, node)
                snippet_start = max(0, s - 500)
                snippet_end = min(len(source), e + 100)
                snippet = source[snippet_start:snippet_end]
                if ("seq == ()" in snippet or "seq==()" in snippet) and ("seq == []" in snippet or "seq==[]" in snippet):
                    # splice constant None to 0
                    ns, ne = _span(source, node.value)
                    out = source[:ns] + "0" + source[ne:]
                    if out != source:
                        candidates.append(out)
                break
    return candidates


def _fix_strict_x_lt_element_plus_1_to_x_le_element(source):
    """
    Repair 4 sample:
        if x < (element + 1): result = i; return
    to:
        if x < (element + 1): result = i; break
    (break out of loop; function later returns result)
    But for local edit, if it's `return` inside loop, replace with `break`.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            # find if-return pattern `if ...: result = i; return`
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.If):
                    # condition should include `<` with (element + 1)
                    cond = stmt.test
                    if not isinstance(cond, ast.Compare):
                        continue
                    if len(cond.ops) != 1 or not isinstance(cond.ops[0], ast.Lt):
                        continue
                    # Now search for Return directly inside this If body
                    has_return = any(isinstance(s, ast.Return) for s in stmt.body)
                    if not has_return:
                        continue
                    # Replace that Return with `break` if it is inside the loop.
                    # Only do a single replacement (first return in the If body)
                    ret_stmt = None
                    for s in stmt.body:
                        if isinstance(s, ast.Return):
                            ret_stmt = s
                            break
                    if ret_stmt is None:
                        continue
                    # ensure its value is None or absent (common: `return` alone)
                    if ret_stmt.value is not None:
                        continue
                    rs, re_ = _span(source, ret_stmt)
                    # preserve indentation by using the exact start line indent from rs
                    line_start = source.rfind("\n", 0, rs) + 1
                    indent = source[line_start:rs]
                    # replace entire return statement text with break
                    new_text = "break"
                    out = source[:rs] + new_text + source[re_:]
                    candidates.append(out)
    return candidates


def _fix_comparison_boundaries_x_lt_seq0_to_x_le_seq0(source):
    """
    Fix pattern:
        elif x < seq[0]: return 0
    to:
        elif x <= seq[0]: return 0
    Targets strictness when equality should not produce i=0+ later cases.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            # Look for left being x and right being seq[0]
            if isinstance(left, ast.Name) and left.id == "x":
                # seq[0]
                if isinstance(right, ast.Subscript) and isinstance(right.value, ast.Name) and right.value.id == "seq":
                    # index constant 0
                    idx = right.slice
                    # py>=3.9 uses ast.Constant directly for simple indices
                    if isinstance(idx, ast.Constant) and idx.value == 0:
                        # splice just operator part by replacing '<' with '<='
                        # We'll replace substring spanning operator token by using node itself might be large;
                        # instead splice left-right comparison by using source of right and left around operator.
                        # Simpler: replace the exact text for `<` between right and left by using compare span and reconstruct.
                        s, e = _span(source, node)
                        full = source[s:e]
                        if "<" in full and "<=" not in full:
                            out = source[:s] + full.replace("<", "<=", 1) + source[e:]
                            if out != source:
                                candidates.append(out)
    return candidates


def _fix_for_range_missing_final_return_len_seq(source):
    """
    In Repair sample 1:
        for ...:
            if x<= seq[i]: return i
            return len(seq)
    already handled by another rule.
    Here: if return len(seq) is missing after loop, add at end of function is too big;
    so we only do local insertion if for-loop is followed by nothing.
    """
    return []


def _fix_wrong_index_after_elem_to_lower_strictness_in_loop(source):
    """
    Fix pattern (Repair 5/7/8 style):
        if x < i: return counter
    to:
        if x <= i: return counter
    General: replace `x < <something>` with `x <= <something>` where left side is Name x.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            if isinstance(node.left, ast.Name) and node.left.id == "x":
                # operator span: replace first '<' token within compare span
                s, e = _span(source, node)
                frag = source[s:e]
                if "<=" not in frag and "<" in frag:
                    out = source[:s] + frag.replace("<", "<=", 1) + source[e:]
                    if out != source:
                        candidates.append(out)
    return candidates


class Fixer:
    def rules(self):
        return [
            Rule(
                name="for_return_len_seq_should_be_after_loop",
                apply=_fix_for_early_return_to_after_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="empty_seq_none_should_be_zero",
                apply=_fix_seq_none_to_zero_in_empty_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_inside_loop_should_break_loop",
                apply=_fix_strict_x_lt_element_plus_1_to_x_le_element_plus_0_break if False else _fix_strict_x_lt_element_plus_1_to_x_le_element_plus_1_break,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_x_lt_to_non_strict_x_le_insertion_points",
                apply=_fix_wrong_index_after_elem_to_lower_strictness_in_loop,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_x_lt_seq0_should_be_non_strict",
                apply=_fix_comparison_boundaries_x_lt_seq0_to_x_le_seq0,
                symptoms=("wrong",),
            ),
        ]


def _fix_strict_x_lt_element_plus_1_to_x_le_element_plus_1_break(source):
    return _fix_strict_x_lt_element_plus_1_to_x_le_element(source)


def _fix_strict_x_lt_element_plus_1_to_x_le_element(source):
    # delegate to the earlier defined break rule
    return _fix_strict_x_lt_element_plus_1_to_x_le_element_plus_1_break_delegate(source)


def _fix_strict_x_lt_element_plus_1_to_x_le_element_plus_1_break_delegate(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.If):
                    cond = stmt.test
                    if not isinstance(cond, ast.Compare):
                        continue
                    if len(cond.ops) != 1 or not isinstance(cond.ops[0], ast.Lt):
                        continue
                    if any(
                        isinstance(b, ast.Return) and b.value is None
                        for b in stmt.body
                    ):
                        ret_stmt = None
                        for b in stmt.body:
                            if isinstance(b, ast.Return) and b.value is None:
                                ret_stmt = b
                                break
                        if ret_stmt is None:
                            continue
                        rs, re_ = _span(source, ret_stmt)
                        out = source[:rs] + "break" + source[re_:]
                        if out != source:
                            candidates.append(out)
    return candidates