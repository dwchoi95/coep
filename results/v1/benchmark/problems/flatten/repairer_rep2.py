"""Local, LLM-free automatic repair for the `flatten` assignment.

Strategy:
  * Parse the student's submission (syntax error -> None).
  * Apply a small set of problem-specific rewrites that target the common
    misconceptions for THIS task:
      - swapped `isinstance` arguments, e.g. `isinstance(list, x)`;
      - a list branch that appends the sublist itself instead of recursing;
      - a shallow inner `for`-loop copy instead of recursion;
      - a bare `.extend(item)` with no type check / no recursion.
  * Every candidate is validated with `first_passing`, which enforces the
    full visible test suite AND the relative-patch-size cap (rps <= 0.35),
    so the student's own approach is preserved and no fixed reference
    solution is ever returned.
  * Fall back to the generic edit search (1 then 2 edits with a budget).

Round-3 fix
-----------
Round 2 tried to shrink the ``.extend`` guard from a multi-line ``if/else``
block down to a one-line conditional expression::

    total.extend(flatten(item) if isinstance(item, list) else [item])

reasoning that the relative patch size was *line*-based.  It was not enough,
and ``crafted_08`` still returned ``no_patch``::

    def flatten(nested):
        total = []
        for item in nested:
            total.extend(item)
        return total

Tracing it by hand: the swap / for-append / list-branch transforms all no-op
on this source; only ``_t_extend`` fires and produces a semantically correct
candidate that passes every test.  So the *only* thing rejecting it is the
``rps`` cap.  The real culprit was not the number of lines but the way the
candidate is emitted: it was produced with ``ast.unparse(tree)``, which
**reformats the entire function and discards the original layout** -- trailing
blank lines, comments, and the student's own spacing all vanish.  On a tiny
five-line submission that whole-file reformat, together with the inherently
large ``flatten(...) if isinstance(...) else [...]`` insertion, pushes the
*character-level* relative patch size past 0.35 even though only one line
"really" changed.  The one-liner cut the line count but not the character
footprint, so ``first_passing`` kept rejecting it.

The fix stops routing the extend-guard through ``ast.unparse``.  It is now
applied as a **surgical, formatting-preserving text edit**: only the argument
span of the offending ``L.extend(<arg>)`` call is spliced, leaving every other
byte of the submission byte-for-byte identical (no dropped blank lines, no
re-spacing, no lost comments).  In addition several increasingly compact but
equivalent guard spellings are offered smallest-first, so ``first_passing``
selects the minimal patch that survives the rps cap.  This keeps the patch
small on short submissions like ``crafted_08`` while remaining correct on the
longer ones, and it generalises: any submission that accumulates with a bare
``.extend`` now gets the tightest possible fix instead of a reformatted whole
file.  The previous ``ast.unparse``-based transforms are retained as a
fallback for the shapes they still handle best, and the generic edit search
remains the final safety net.  ``repair`` never raises.
"""

import ast
import copy
import itertools

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "flatten"

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, [2, 3]]], "expected": [1, 2, 3]},
    {"args": [[[1, 2], [3, 4]]], "expected": [1, 2, 3, 4]},
    {"args": [[[[[1]]]]], "expected": [1]},
    {"args": [[1, [2, [3, [4, [5]]]]]], "expected": [1, 2, 3, 4, 5]},
    {"args": [[[], [], []]], "expected": []},
    {"args": [[0]], "expected": [0]},
    {"args": [[1, [], 2]], "expected": [1, 2]},
    {"args": [[[1], [2], 3, [4, [5, 6]]]], "expected": [1, 2, 3, 4, 5, 6]},
    {"args": [[-1, [-2, [-3]]]], "expected": [-1, -2, -3]},
    {"args": [[[[]], [[[]]], 5]], "expected": [5]},
    {"args": [[10, [20], [30, [40]], 50]], "expected": [10, 20, 30, 40, 50]},
    {"args": [[[1, [2]], 3]], "expected": [1, 2, 3]},
]

_TYPE_NAMES = {"list", "tuple", "int", "float", "str", "dict", "set", "bool"}


# --------------------------------------------------------------------------
# Small AST helpers.
# --------------------------------------------------------------------------

def _is_flatten_call(node):
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "flatten")


def _guarded_arg(arg):
    """Build ``flatten(arg) if isinstance(arg, list) else [arg]`` as an AST.

    Used only by the ``ast.unparse`` fallback transform; the primary path
    emits the guard as source text (see ``_surgical_extend_candidates``).
    """
    return ast.IfExp(
        test=ast.Call(
            func=ast.Name(id="isinstance", ctx=ast.Load()),
            args=[copy.deepcopy(arg), ast.Name(id="list", ctx=ast.Load())],
            keywords=[]),
        body=ast.Call(
            func=ast.Name(id="flatten", ctx=ast.Load()),
            args=[copy.deepcopy(arg)], keywords=[]),
        orelse=ast.List(elts=[copy.deepcopy(arg)], ctx=ast.Load()))


# --------------------------------------------------------------------------
# Primary path: surgical, formatting-preserving guard on `L.extend(<arg>)`.
#
# Instead of reformatting the whole function with `ast.unparse` (which drops
# the student's layout and inflates the character-level patch size on short
# submissions), we splice only the argument span of the offending extend
# call, leaving every other byte identical.  Several equivalent spellings are
# tried smallest-first so the minimal patch that clears the rps cap wins.
# --------------------------------------------------------------------------

# Spellings ordered from most compact to most readable.  `{A}` is the exact
# original source text of the extend argument, so we recurse on nested lists
# and wrap scalars while touching only the one call.
_GUARD_SPELLINGS = [
    "flatten({A})if type({A})==list else[{A}]",
    "flatten({A}) if type({A}) == list else [{A}]",
    "flatten({A}) if isinstance({A}, list) else [{A}]",
]


def _bare_extend_args(tree):
    """Return the arg nodes of `X.extend(arg)` calls that need guarding.

    Skips calls that already recurse (`flatten(...)`), are already guarded
    (an `IfExp`), already wrap a literal list, or whose argument spans more
    than one line (which we cannot splice safely).
    """
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "extend"
                and len(node.args) == 1
                and not node.keywords):
            arg = node.args[0]
            if _is_flatten_call(arg) or isinstance(arg, ast.IfExp):
                continue
            if isinstance(arg, ast.List):
                continue
            lineno = getattr(arg, "lineno", None)
            end_lineno = getattr(arg, "end_lineno", None)
            col = getattr(arg, "col_offset", None)
            end_col = getattr(arg, "end_col_offset", None)
            if (lineno is None or end_lineno is None
                    or col is None or end_col is None):
                continue
            if lineno != end_lineno:
                continue
            out.append((lineno, col, end_col))
    return out


def _surgical_extend_candidates(source):
    """Yield sources where every bare `L.extend(arg)` is guarded, smallest
    spelling first, preserving all other formatting exactly."""
    try:
        tree = ast.parse(source)
    except Exception:
        return

    spots = _bare_extend_args(tree)
    if not spots:
        return

    lines = source.splitlines(keepends=True)
    seen = set()

    for spelling in _GUARD_SPELLINGS:
        try:
            new_lines = list(lines)
            # Apply from the bottom-most, right-most span first so earlier
            # column offsets on the same line stay valid.
            for (lineno, col, end_col) in sorted(
                    spots, key=lambda t: (t[0], t[1]), reverse=True):
                idx = lineno - 1
                if idx < 0 or idx >= len(new_lines):
                    raise ValueError("line out of range")
                line = new_lines[idx]
                argsrc = line[col:end_col]
                if not argsrc.strip():
                    raise ValueError("empty argument span")
                guard = spelling.format(A=argsrc)
                new_lines[idx] = line[:col] + guard + line[end_col:]
            cand = "".join(new_lines)
            ast.parse(cand)  # must stay syntactically valid
        except Exception:
            continue
        if cand and cand != source and cand not in seen:
            seen.add(cand)
            yield cand


# --------------------------------------------------------------------------
# Fallback problem-specific AST transforms (via ast.unparse).  Each mutates
# `tree` in place and returns True if it changed anything.
# --------------------------------------------------------------------------

def _t_swap_isinstance(tree):
    """`isinstance(list, x)` -> `isinstance(x, list)` (swapped arguments)."""
    changed = False
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "isinstance"
                and len(node.args) == 2):
            a, b = node.args
            first_is_type = isinstance(a, ast.Name) and a.id in _TYPE_NAMES
            second_is_type = isinstance(b, ast.Name) and b.id in _TYPE_NAMES
            if first_is_type and not second_is_type:
                node.args = [b, a]
                changed = True
    return changed


class _ForAppendFix(ast.NodeTransformer):
    """`for v in it: L.append(v)` -> `L.extend(flatten(it))` (shallow copy)."""

    def __init__(self):
        self.changed = False

    def visit_For(self, node):
        self.generic_visit(node)
        if (isinstance(node.target, ast.Name)
                and not node.orelse
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Expr)):
            call = node.body[0].value
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "append"
                    and len(call.args) == 1
                    and isinstance(call.args[0], ast.Name)
                    and call.args[0].id == node.target.id):
                listname = call.func.value
                new = ast.Expr(value=ast.Call(
                    func=ast.Attribute(value=copy.deepcopy(listname),
                                       attr="extend", ctx=ast.Load()),
                    args=[ast.Call(
                        func=ast.Name(id="flatten", ctx=ast.Load()),
                        args=[copy.deepcopy(node.iter)], keywords=[])],
                    keywords=[]))
                self.changed = True
                return ast.copy_location(new, node)
        return node


class _ListBranchAppendFix(ast.NodeTransformer):
    """Inside `if isinstance(v, list): L.append(v)` recurse instead."""

    def __init__(self):
        self.changed = False

    def visit_If(self, node):
        self.generic_visit(node)
        t = node.test
        if (isinstance(t, ast.Call)
                and isinstance(t.func, ast.Name)
                and t.func.id == "isinstance"
                and len(t.args) == 2
                and isinstance(t.args[0], ast.Name)
                and isinstance(t.args[1], ast.Name)
                and t.args[1].id == "list"):
            varname = t.args[0].id
            if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
                call = node.body[0].value
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "append"
                        and len(call.args) == 1
                        and isinstance(call.args[0], ast.Name)
                        and call.args[0].id == varname):
                    listname = call.func.value
                    node.body = [ast.Expr(value=ast.Call(
                        func=ast.Attribute(value=copy.deepcopy(listname),
                                           attr="extend", ctx=ast.Load()),
                        args=[ast.Call(
                            func=ast.Name(id="flatten", ctx=ast.Load()),
                            args=[ast.Name(id=varname, ctx=ast.Load())],
                            keywords=[])],
                        keywords=[]))]
                    self.changed = True
        return node


class _ExtendFix(ast.NodeTransformer):
    """`L.extend(x)` -> `L.extend(flatten(x) if isinstance(x, list) else [x])`.

    Fallback for cases the surgical splicer cannot handle (e.g. a multi-line
    argument).  Emits a one-line conditional expression.
    """

    def __init__(self):
        self.changed = False

    def visit_Expr(self, node):
        self.generic_visit(node)
        v = node.value
        if (isinstance(v, ast.Call)
                and isinstance(v.func, ast.Attribute)
                and v.func.attr == "extend"
                and len(v.args) == 1
                and not v.keywords):
            arg = v.args[0]
            if _is_flatten_call(arg) or isinstance(arg, ast.IfExp):
                return node
            if isinstance(arg, ast.List):
                return node
            v.args = [_guarded_arg(arg)]
            self.changed = True
        return node


def _run_transformer(cls, tree):
    f = cls()
    f.visit(tree)
    ast.fix_missing_locations(tree)
    return f.changed


def _t_forappend(tree):
    return _run_transformer(_ForAppendFix, tree)


def _t_listbranch(tree):
    return _run_transformer(_ListBranchAppendFix, tree)


def _t_extend(tree):
    return _run_transformer(_ExtendFix, tree)


# Order matters: smaller / more targeted fixes first so minimal patches win.
_TRANSFORMS = [_t_swap_isinstance, _t_forappend, _t_listbranch, _t_extend]


def _specific_candidates(source):
    """Yield source strings produced by combinations of the fix transforms.

    Single-transform (minimal) candidates are yielded first, then pairs, etc.
    These are reformatted by ``ast.unparse`` and act as a fallback behind the
    surgical splicer.
    """
    try:
        base = ast.parse(source)
    except SyntaxError:
        return
    except Exception:
        return

    seen = set()
    for r in range(1, len(_TRANSFORMS) + 1):
        for combo in itertools.combinations(_TRANSFORMS, r):
            try:
                tree = copy.deepcopy(base)
                changed = False
                for t in combo:
                    if t(tree):
                        changed = True
                if not changed:
                    continue
                src = ast.unparse(tree)
            except Exception:
                continue
            if src and src != source and src not in seen:
                seen.add(src)
                yield src


def _all_specific_candidates(source):
    """Surgical (formatting-preserving) candidates first, then the
    ast.unparse-based transforms."""
    seen = set()
    try:
        for src in _surgical_extend_candidates(source):
            if src not in seen:
                seen.add(src)
                yield src
    except Exception:
        pass
    try:
        for src in _specific_candidates(source):
            if src not in seen:
                seen.add(src)
                yield src
    except Exception:
        pass


def repair(source):
    """Return a corrected `flatten` submission passing all tests, or None."""
    if not isinstance(source, str):
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    original = source

    # 1) Problem-specific rewrites (validated + rps-capped by first_passing).
    #    Surgical, format-preserving patches are tried first so the smallest
    #    correct change is selected on short submissions.
    try:
        result = first_passing(
            _all_specific_candidates(source), ENTRY, TESTS, original,
            max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    except Exception:
        pass

    # 2) Generic single-edit search.
    try:
        result = first_passing(
            candidates_generic(source, max_edits=1, budget=2000),
            ENTRY, TESTS, original, max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    except Exception:
        pass

    # 3) Generic two-edit search (larger; bounded by budget/checks).
    try:
        result = first_passing(
            candidates_generic(source, max_edits=2, budget=2000),
            ENTRY, TESTS, original, max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    except Exception:
        pass

    return None
