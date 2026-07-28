"""Measure whether a rule's local edit appears in the reference pool.

This is a diagnostic of patch shape, not evidence that reference-guided repair
cannot fix a bug. A transplant may repair the same misconception by importing a
guard and its surrounding structure even when the rule's exact in-place rewrite
is absent. The comparison helps explain why authored rules can produce smaller
patches.

Operationally, diff p_b against p_f, parse the statements the patch introduces,
normalise them by folding identifiers and constants to placeholders, and ask
whether that normalised form occurs among the statements of any correct program
for the same problem. Folding identifiers makes the comparison about structure
rather than whether a student happened to name a variable `s`.

Limitations:
1. Compound statements are excluded. Counting a changed FunctionDef (and its
   body) would make nearly every patch appear absent, so the measurement compares
   simple statements and branch tests instead.
2. Constants are folded. A repair whose essential edit is a constant change can
   therefore collapse to the buggy form and be missed by this analysis.
"""
from __future__ import annotations

import ast
import difflib
import json
import sys
from collections import defaultdict
from pathlib import Path

# Running this file directly puts ``src/experiments`` first on sys.path, where
# numbers.py would shadow Python's standard-library ``numbers`` module while
# pandas imports. Use the repository root instead, as module execution does.
_HERE = Path(__file__).resolve().parent
_ROOT = Path(__file__).resolve().parents[2]
sys.path = [p for p in sys.path if Path(p or ".").resolve() != _HERE]
sys.path.insert(0, str(_ROOT))
import pandas as pd

from src.experiments.tables import ORDER, IDS, ROOT, _cell, _summary

MODEL = "claude-sonnet-5"


class _Fold(ast.NodeTransformer):
    """Identifiers and literals become placeholders; structure survives."""

    def visit_Name(self, node):
        return ast.copy_location(ast.Name(id="_", ctx=node.ctx), node)

    def visit_arg(self, node):
        return ast.copy_location(ast.arg(arg="_", annotation=None), node)

    def visit_Attribute(self, node):
        self.generic_visit(node)
        return node                      # keep .isupper vs .upper: that is the point

    def visit_Constant(self, node):
        v = node.value
        keep = v if isinstance(v, int) and -1 <= v <= 1 else "_"
        return ast.copy_location(ast.Constant(value=keep), node)


def norm(node) -> str:
    try:
        return ast.dump(_Fold().visit(ast.parse(ast.unparse(node)).body[0]))
    except Exception:
        return ""


COMPOUND = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.For,
            ast.AsyncFor, ast.While, ast.If, ast.With, ast.AsyncWith, ast.Try)


def statements(src: str) -> set[str]:
    """The transplantable units of a program.

    Compound statements are excluded on purpose. A FunctionDef whose body
    changed is itself a changed statement, so counting it would make every
    patch "absent from the pool" and the measurement would say nothing. What a
    reference-guided method actually needs to find is the simple statement or
    the branch condition it would copy, so those are what we compare.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.stmt) and not isinstance(n, COMPOUND):
            d = norm(n)
            if d:
                out.add(d)
        elif isinstance(n, (ast.If, ast.While)):
            d = norm(ast.Expr(value=n.test))
            if d:
                out.add("TEST:" + d)
        elif isinstance(n, ast.IfExp):
            d = norm(ast.Expr(value=n.test))
            if d:
                out.add("TEST:" + d)
    return out


def introduced(before: str, after: str) -> list[str]:
    """Statements present in the fixed program that the buggy one did not have."""
    a, b = statements(before), statements(after)
    return sorted(b - a)


def main() -> None:
    print(f"{'ID':<4}{'rule':<38}{'M':>4}{'absent':>8}{'%':>6}{'pool':>6}{'lines':>6}")
    rows = []
    for pid in ORDER:
        loc_f = ROOT / "results" / "v2" / pid / "coep_l.csv"
        if not loc_f.exists():
            continue
        authored = set(json.loads(_cell(_summary("v2", pid), "CoEP_L",
                                        MODEL)["Rules_build"]))
        pool_stmts: set[str] = set()
        pool = sorted((ROOT / "data" / pid / "correct").glob("*.py"))
        for f in pool:
            pool_stmts |= statements(f.read_text())
        loc = pd.read_csv(loc_f, keep_default_na=False)
        loc = loc[loc.Model == MODEL]
        by = defaultdict(list)
        for _i, r in loc.iterrows():
            if not (r["Fixed"] and r["Source"] == "rules"):
                continue
            names = json.loads(r["Rules_L"])
            for nm in names:
                if nm in authored:
                    by[nm].append(r)
        for nm, rs in by.items():
            if len(rs) < 5:
                continue
            absent = 0
            for r in rs:
                src = (ROOT / "data" / pid / "buggy" / f"{r['Buggy']}.py").read_text()
                new = introduced(src, r["Patch"])
                if new and all(s not in pool_stmts for s in new):
                    absent += 1
            lens = [len((ROOT / "data" / pid / "buggy" /
                         f"{r['Buggy']}.py").read_text().strip().splitlines())
                    for r in rs]
            rows.append((100 * absent / len(rs), len(rs), absent, IDS[pid], pid, nm,
                         len(pool), sorted(lens)[len(lens) // 2]))
    rows.sort(key=lambda t: (-t[0], -t[1]))
    for pct, m, absent, ident, pid, nm, pool, ml in rows:
        print(f"{ident:<4}{nm[:37]:<38}{m:>4}{absent:>8}{pct:>5.0f}%{pool:>6}{ml:>6}")


if __name__ == "__main__":
    main()
