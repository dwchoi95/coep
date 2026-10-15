"""
Repair module for the "Jumping Jack" assignment.

The canonical task: find minimal n such that T(n) = n*(n+1)/2 >= |x|
and (T(n) - |x|) is even.

Observed misconception (shared by many buggy submissions): students write a
brute-force loop that increments a counter n while T(n) < target, and once
T(n) == target they print n (correct), but once T(n) > target (the
"overshoot" branch) they invent some ad-hoc arithmetic (often involving
min() of two guessed formulas) instead of doing the correct parity check
against T(n) and T(n+1). We locate that specific overshoot branch
structurally (an elif/if chain containing Lt/Eq/Gt comparisons of the same
triangular-number expression against the same target variable) and splice
in the correct parity-based resolution, leaving the rest of the program
(the loop, the Lt/Eq branches, I/O, etc.) completely untouched.
"""

import ast
import re

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


def _norm(text):
    return re.sub(r"\s+", "", text)


def _line_prefix(source, node):
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    return line[: node.col_offset]


def _indent_unit(prefix):
    return "\t" if "\t" in prefix else "    "


def _elif_chain(if_node):
    chain = [if_node]
    cur = if_node
    while len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
        cur = cur.orelse[0]
        chain.append(cur)
    return chain


def _find_increment_var(stmts):
    found = {"name": None}

    class V(ast.NodeVisitor):
        def visit_AugAssign(self, node):
            if isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
                if isinstance(node.value, ast.Constant) and node.value.value == 1:
                    found["name"] = node.target.id
            self.generic_visit(node)

        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                tgt = node.targets[0]
                val = node.value
                if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                    operands = [val.left, val.right]
                    names = [o for o in operands if isinstance(o, ast.Name)]
                    consts = [o for o in operands if isinstance(o, ast.Constant)]
                    if names and consts and names[0].id == tgt.id and consts[0].value == 1:
                        found["name"] = tgt.id
            self.generic_visit(node)

    v = V()
    for s in stmts:
        v.visit(s)
    return found["name"]


def _has_div(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Div):
            return True
    return False


def fix_triangular_overshoot_branch(source):
    """Replace the broken 'T(n) > target' branch of a brute-force triangular
    search with the correct parity-based resolution (n, n+1, or n+2)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    matches = []
    seen = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        chain = _elif_chain(node)
        if len(chain) < 3:
            continue
        key = id(chain[0])
        if key in seen:
            continue
        seen.add(key)

        infos = []
        ok = True
        for br in chain:
            test = br.test
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1
                    and len(test.comparators) == 1):
                ok = False
                break
            infos.append((br, test.ops[0], test.left, test.comparators[0]))
        if not ok:
            continue

        ops = [type(i[1]) for i in infos]
        if not (ast.Lt in ops and ast.Eq in ops and ast.Gt in ops):
            continue

        try:
            left_texts = [_norm(source[_span(source, i[2])[0]:_span(source, i[2])[1]])
                          for i in infos]
            right_texts = [_norm(source[_span(source, i[3])[0]:_span(source, i[3])[1]])
                           for i in infos]
        except Exception:
            continue

        if len(set(left_texts)) != 1 or len(set(right_texts)) != 1:
            continue

        tri_node0 = infos[0][2]
        target_node0 = infos[0][3]

        if not _has_div(tri_node0):
            continue
        if not isinstance(target_node0, ast.Name):
            continue

        lt_branch = next((b for b, op, l, r in infos if isinstance(op, ast.Lt)), None)
        gt_branch = next((b for b, op, l, r in infos if isinstance(op, ast.Gt)), None)
        if lt_branch is None or gt_branch is None:
            continue

        n_var = _find_increment_var(lt_branch.body)
        if not n_var:
            continue

        ts, te = _span(source, tri_node0)
        TRI = source[ts:te]
        rs, re_ = _span(source, target_node0)
        TARGET = source[rs:re_]

        TRI2 = re.sub(r"\b" + re.escape(n_var) + r"\b", "(" + n_var + "+1)", TRI)

        body = gt_branch.body
        if not body:
            continue
        first_stmt = body[0]
        last_stmt = body[-1]
        prefix = _line_prefix(source, first_stmt)
        unit = _indent_unit(prefix)

        lines = [
            f"diff = ({TRI}) - ({TARGET})",
            f"{prefix}if diff % 2 == 0:",
            f"{prefix}{unit}print(int({n_var}))",
            f"{prefix}else:",
            f"{prefix}{unit}diff2 = ({TRI2}) - ({TARGET})",
            f"{prefix}{unit}if diff2 % 2 == 0:",
            f"{prefix}{unit}{unit}print(int({n_var}) + 1)",
            f"{prefix}{unit}else:",
            f"{prefix}{unit}{unit}print(int({n_var}) + 2)",
            f"{prefix}break",
        ]
        new_text = "\n".join(lines)

        s_start, _e = _span(source, first_stmt)
        _s, s_end = _span(source, last_stmt)
        matches.append((s_start, s_end, new_text))

    if not matches:
        return []

    matches.sort(key=lambda t: t[0], reverse=True)
    new_source = source
    for s, e, text in matches:
        new_source = new_source[:s] + text + new_source[e:]

    if new_source == source:
        return []
    return [new_source]


def relax_strict_lt(source):
    """Generic cheap slip: a strict '<' comparison that should be '<=' (or
    symmetrically '>' that should be '>='). Only fires on simple scalar
    comparisons, producing one candidate per comparison found."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            left, right = node.left, node.comparators[0]
            try:
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
            except Exception:
                continue
            if isinstance(op, ast.Lt):
                new_cmp = source[ls:le] + " <= " + source[rs:re_]
            elif isinstance(op, ast.Gt):
                new_cmp = source[ls:le] + " >= " + source[rs:re_]
            else:
                continue
            out.append(_splice(source, node, new_cmp))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="fix_triangular_overshoot_branch",
                apply=fix_triangular_overshoot_branch,
                symptoms=("wrong",),
            ),
            Rule(
                name="relax_strict_lt_gt",
                apply=relax_strict_lt,
                symptoms=("wrong",),
            ),
        ]