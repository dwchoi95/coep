```python
"""Local, LLM-free automatic repair for the `unique_in_order` assignment.

Strategy:
  1. Validate the input as-is (maybe it already passes).
  2. Try a battery of problem-specific AST/text rewrites targeting known
     misconceptions for this assignment (wrong base case for the first
     element, missing emptiness/boundary guards around result[-1] /
     lst[i-1] / lst[i+1], bad sentinel initialisations, `is` instead of
     `==`, return placed inside the loop, needless sorted()/set(),
     misnamed function).
  3. Fall back to the generic mutation search (1 edit, then 2 edits).
  4. As a last resort, combine each specific rewrite with one generic edit.
All candidates are validated through `first_passing`, which enforces the
full visible test suite and the rps <= 0.35 patch-size cap against the
ORIGINAL student source.
"""

import ast
import re

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain

ENTRY = "unique_in_order"

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1]], "expected": [1]},
    {"args": [[1, 1]], "expected": [1]},
    {"args": [[1, 1, 2, 1]], "expected": [1, 2, 1]},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 1, 1, 1]], "expected": [1]},
    {"args": [["a", "a", "b", "b", "a"]], "expected": ["a", "b", "a"]},
    {"args": [[1, "1", 1]], "expected": [1, "1", 1]},
    {"args": [[2, 2, 2, 3, 3, 1, 1, 2]], "expected": [2, 3, 1, 2]},
    {"args": [["A", "a", "A"]], "expected": ["A", "a", "A"]},
    {"args": [[0, 0, 0]], "expected": [0]},
    {"args": [[5, 4, 4, 5, 5, 4]], "expected": [5, 4, 5, 4]},
    {"args": [["x"]], "expected": ["x"]},
    {"args": [[1, 2, 2, 3, 3, 3, 4]], "expected": [1, 2, 3, 4]},
]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _parses(src):
    try:
        ast.parse(src)
        return True
    except Exception:
        return False


def _param_name(tree):
    """First parameter of the entry function (fallback: any function, then 'lst')."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY and node.args.args:
            return node.args.args[0].arg
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.args.args:
            return node.args.args[0].arg
    return "lst"


def _safe(gen):
    """Iterate a candidate generator, swallowing any mid-iteration error."""
    try:
        for c in gen:
            if isinstance(c, str):
                yield c
    except Exception:
        return


# --------------------------------------------------------------------------
# problem-specific rewrite rules
# --------------------------------------------------------------------------

def _rename_candidates(source):
    """If the (single) function has the wrong name, rename it to the entry name."""
    outs = []
    try:
        tree = ast.parse(source)
    except Exception:
        return outs
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if fns and not any(f.name == ENTRY for f in fns):
        fns[0].name = ENTRY
        try:
            ast.fix_missing_locations(tree)
            outs.append(ast.unparse(tree))
        except Exception:
            pass
    return outs


def _seed_init_candidates(source, param):
    """`result = []` -> `result = lst[:1]`.

    Fixes the classic bug where the loop starts at index 1 (or otherwise
    skips the first element) so the first element is never appended.
    One candidate per empty-list initialisation site.
    """
    outs = []
    pat = re.compile(r"(?<![=!<>])(=\s*)\[\]")
    for m in pat.finditer(source):
        outs.append(source[: m.start()] + m.group(1) + param + "[:1]" + source[m.end():])
    return outs


def _idx_patterns(cond):
    """Detect boundary-sensitive index accesses inside a condition.

    Returns list of (name, kind) with kind in {'prev', 'next', 'neg'}:
      prev: X[i - 1]  -> needs an `i == 0` style guard
      next: X[i + 1]  -> needs an `i == len(lst) - 1` style guard
      neg : X[-k]     -> needs an emptiness guard on X
    """
    found = []
    for sub in ast.walk(cond):
        if not isinstance(sub, ast.Subscript):
            continue
        s = sub.slice
        if (
            isinstance(s, ast.BinOp)
            and isinstance(s.right, ast.Constant)
            and s.right.value == 1
            and isinstance(s.left, ast.Name)
        ):
            if isinstance(s.op, ast.Sub):
                found.append((s.left.id, "prev"))
            elif isinstance(s.op, ast.Add):
                found.append((s.left.id, "next"))
        elif (
            isinstance(s, ast.UnaryOp)
            and isinstance(s.op, ast.USub)
            and isinstance(s.operand, ast.Constant)
            and isinstance(sub.value, ast.Name)
        ):
            found.append((sub.value.id, "neg"))
        elif (
            isinstance(s, ast.Constant)
            and isinstance(s.value, int)
            and s.value < 0
            and isinstance(sub.value, ast.Name)
        ):
            found.append((sub.value.id, "neg"))
    return found


def _cond_sites(tree):
    """Deterministic list of condition sites: If/IfExp tests and comprehension ifs."""
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.IfExp)):
            sites.append((node, "test", -1))
        elif isinstance(node, ast.comprehension):
            for j in range(len(node.ifs)):
                sites.append((node, "ifs", j))
    return sites


def _get_cond(site):
    node, attr, j = site
    return node.test if attr == "test" else node.ifs[j]


def _set_cond(site, new):
    node, attr, j = site
    if attr == "test":
        node.test = new
    else:
        node.ifs[j] = new


def _guard_candidates(source):
    """Wrap bare conditions with the missing boundary guard.

    e.g.  `x != result[-1]`      -> `not result or x != result[-1]`
          `lst[i] != lst[i - 1]` -> `i == 0 or lst[i] != lst[i - 1]`
                                 or `i != 0 and lst[i] == lst[i - 1]` (skip form)
          `lst[i] != lst[i + 1]` -> `i == len(lst) - 1 or ...`
    """
    outs = []
    try:
        base = ast.parse(source)
    except Exception:
        return outs
    param = _param_name(base)
    n_sites = len(_cond_sites(base))
    for k in range(n_sites):
        probe = ast.parse(source)
        cond = _get_cond(_cond_sites(probe)[k])
        if isinstance(cond, ast.BoolOp):
            continue  # already has some compound guard; generic search handles it
        guards = []
        for nm, kind in _idx_patterns(cond):
            if kind == "prev":
                guards.append(("%s == 0" % nm, "or"))
                guards.append(("%s != 0" % nm, "and"))
            elif kind == "next":
                guards.append(("%s == len(%s) - 1" % (nm, param), "or"))
                guards.append(("%s != len(%s) - 1" % (nm, param), "and"))
            else:  # neg
                guards.append(("not %s" % nm, "or"))
                guards.append(("%s" % nm, "and"))
        seen = set()
        for gsrc, mode in guards:
            if (gsrc, mode) in seen:
                continue
            seen.add((gsrc, mode))
            try:
                t2 = ast.parse(source)
                site2 = _cond_sites(t2)[k]
                c2 = _get_cond(site2)
                gexpr = ast.parse(gsrc, mode="eval").body
                new = ast.BoolOp(
                    op=ast.Or() if mode == "or" else ast.And(),
                    values=[gexpr, c2],
                )
                _set_cond(site2, new)
                ast.fix_missing_locations(t2)
                outs.append(ast.unparse(t2))
            except Exception:
                continue
    return outs


def _dedent_return_candidates(source):
    """Move a `return` that sits at the end of a loop body out of the loop."""
    outs = []
    try:
        base = ast.parse(source)
    except Exception:
        return outs

    def loops_with_trailing_return(tree):
        return [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.For, ast.While))
            and n.body
            and isinstance(n.body[-1], ast.Return)
        ]

    n = len(loops_with_trailing_return(base))
    for k in range(n):
        try:
            t2 = ast.parse(source)
            loop = loops_with_trailing_return(t2)[k]
            ret = loop.body.pop()
            if not loop.body:
                loop.body.append(ast.Pass())
            placed = False
            for node in ast.walk(t2):
                for field in ("body", "orelse", "finalbody"):
                    seq = getattr(node, field, None)
                    if isinstance(seq, list) and loop in seq:
                        seq.insert(seq.index(loop) + 1, ret)
                        placed = True
                        break
                if placed:
                    break
            if placed:
                ast.fix_missing_locations(t2)
                outs.append(ast.unparse(t2))
        except Exception:
            continue
    return outs


def _sentinel_candidates(source):
    """`prev = 0` / `prev = ''` / etc. -> `prev = object()`.

    A constant sentinel that can legitimately occur in the data (e.g. 0)
    silently drops the first run; a fresh object() never equals any element.
    """
    outs = []
    try:
        base = ast.parse(source)
    except Exception:
        return outs

    def const_assigns(tree):
        return [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
        ]

    n = len(const_assigns(base))
    for k in range(n):
        try:
            t2 = ast.parse(source)
            node = const_assigns(t2)[k]
            node.value = ast.parse("object()", mode="eval").body
            ast.fix_missing_locations(t2)
            outs.append(ast.unparse(t2))
        except Exception:
            continue
    return outs


class _StripCall(ast.NodeTransformer):
    """Replace the k-th sorted(X)/set(X)/reversed(X) call with plain X."""

    def __init__(self, k):
        self.k = k
        self.count = -1

    def visit_Call(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in ("sorted", "set", "reversed")
            and len(node.args) == 1
            and not node.keywords
        ):
            self.count += 1
            if self.count == self.k:
                return node.args[0]
        return node


def _strip_call_candidates(source):
    outs = []
    if not re.search(r"\b(sorted|set|reversed)\s*\(", source):
        return outs
    for k in range(6):
        try:
            t2 = ast.parse(source)
            tr = _StripCall(k)
            t2 = tr.visit(t2)
            if tr.count < k:
                break
            ast.fix_missing_locations(t2)
            outs.append(ast.unparse(t2))
        except Exception:
            break
    return outs


def _is_to_eq_candidates(source):
    """Replace identity comparisons with value comparisons."""
    outs = []
    if re.search(r"\bis\s+not\b", source):
        outs.append(re.sub(r"\bis\s+not\b", "!=", source))
    if re.search(r"\bis\b", source):
        outs.append(
            re.sub(r"\bis\b(?!\s+not\b)", "==", re.sub(r"\bis\s+not\b", "!=", source))
        )
    return outs


def _insert_copy_candidates(source):
    """Insert `lst = list(lst)` at the top of the function (aliasing/mutation bugs)."""
    outs = []
    try:
        tree = ast.parse(source)
    except Exception:
        return outs
    param = _param_name(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            try:
                stmt = ast.parse("%s = list(%s)" % (param, param)).body[0]
                node.body.insert(0, stmt)
                ast.fix_missing_locations(tree)
                outs.append(ast.unparse(tree))
            except Exception:
                pass
            break
    return outs


def _specific_candidates(source):
    """All problem-specific rewrites, deduplicated, in priority order."""
    try:
        tree = ast.parse(source)
        param = _param_name(tree)
    except Exception:
        return []
    cands = []
    for rule in (
        lambda s: _rename_candidates(s),
        lambda s: _seed_init_candidates(s, param),
        lambda s: _guard_candidates(s),
        lambda s: _dedent_return_candidates(s),
        lambda s: _sentinel_candidates(s),
        lambda s: _strip_call_candidates(s),
        lambda s: _is_to_eq_candidates(s),
        lambda s: _insert_copy_candidates(s),
    ):
        try:
            cands.extend(rule(source))
        except Exception:
            continue
    seen = set()
    out = []
    for c in cands:
        if not isinstance(c, str) or c == source or c in seen:
            continue
        if not _parses(c):
            continue
        seen.add(c)
        out.append(c)
    return out


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def repair(source):
    try:
        if not isinstance(source, str) or not _parses(source):
            return None

        # Stage 0: maybe the submission already passes (validated, rps == 0).
        ok = first_passing(iter([source]), ENTRY, TESTS, source,
                           max_rps=0.35, max_checks=5)
        if ok is not None:
            return ok

        # (failing pattern is available for inspection; validation below is
        # what actually decides, so we simply try rules in priority order.)
        try:
            failing_tests(source, ENTRY, TESTS)
        except Exception:
            pass

        specific = _specific_candidates(source)

        # Stage 1: specific rewrites first, then generic 1-edit, then 2-edit.
        gens = chain(
            _safe(iter(specific)),
            _safe(candidates_generic(source, max_edits=1, budget=2000)),
            _safe(candidates_generic(source, max_edits=2, budget=3000)),
        )
        fixed = first_passing(gens, ENTRY, TESTS, source,
                              max_rps=0.35, max_checks=800)
        if fixed is not None:
            return fixed

        # Stage 2: a specific rewrite combined with one generic edit.
        stage2 = []
        for cand in specific[:8]:
            try:
                stage2.append(_safe(candidates_generic(cand, max_edits=1, budget=250)))
            except Exception:
                continue
        if stage2:
            fixed = first_passing(chain(*stage2), ENTRY, TESTS, source,
                                  max_rps=0.35, max_checks=400)
        return fixed
    except Exception:
        return None
```
