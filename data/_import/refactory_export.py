"""Export Codeforces problems into the Refactory tool's data format.

Refactory's executor (baselines/refactory) runs programs as *function calls*:
an ``ans/input_x.txt`` is a Python expression exec'd against the submission's
top-level ``def``s, captured stdout is string-compared to
``str(eval(output_x.txt)) + "\\n"``. It strips every import line and every
top-level non-def statement, breaks on nested ``def``s, never feeds stdin, and
dies on ``SystemExit``. Codeforces submissions are whole-file stdin->stdout
scripts, so we adapt the *data*, not their code:

* ``code/global.py`` (read raw, never regularized) installs module-level
  ``print``/``input`` shims that collect/serve tokens — covering helper
  functions too — plus the imports submissions lose to regularization.
* Each submission keeps its original top-level ``def``s at top level (nested
  defs break their hole-injection) and its script body is re-indented into
  ``def main(s)``, with ``sys.stdin.*`` idioms rewritten onto the shims and
  ``exit()``/``sys.exit()`` rewritten to a catchable local exception.
* ``ans`` files: ``input_x`` = ``_flush(main(<stdin repr>)) #print(`` (the
  comment defeats their auto-print wrap); ``output_x`` = ``repr`` of the
  expected stdout normalized to a single token stream — the same whitespace-
  insensitive comparison our own judge uses, so both systems face one oracle.

One environment-compat patch is applied to the tool itself (algorithm
untouched): ``basic_framework/exec.py`` wraps its RLIMIT_AS call in
try/except, since macOS refuses to set that limit (their MemoryGuarder
otherwise crashes at import).

Usage:  python3 data/_import/refactory_export.py cf_125A [--wrong-limit N]
Writes: baselines/refactory/data_cf/<pid>/{ans,code/{reference,correct,wrong}}
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import re
import signal
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

GLOBAL_PY = '''\
import sys as _sys
import sys
import math, re, string, itertools, functools, operator, heapq, bisect, array
from collections import Counter, defaultdict, deque, OrderedDict
from math import gcd, sqrt, ceil, floor, factorial, log, log2, inf, pi, isqrt, comb
from itertools import permutations, combinations, product, accumulate, groupby, chain
from functools import reduce, lru_cache, cmp_to_key
from heapq import heappush, heappop, heapify, heappushpop, nlargest, nsmallest
from bisect import bisect, bisect_left, bisect_right, insort
import collections, copy, os, io, random
from operator import itemgetter
_OUT = []
_IN = iter([])
print = lambda *a, **k: _OUT.append(str(k.get("sep", " ")).join(map(str, a)))
input = lambda: next(_IN)
_wout = lambda x: (_OUT.append(str(x)), len(str(x)))[1]
_flush = lambda _r=None: _sys.stdout.write(" ".join("\\n".join(_OUT).split()) + "\\n")
'''

# ordered, longest-first textual rewrites of stdin/exit idioms
REWRITES = [
    ("sys.stdin.buffer.read().decode()", "_ALLDATA"),
    ("sys.stdin.buffer.read().split()", "_ALLDATA.split()"),
    ("sys.stdin.buffer.read()", "_ALLDATA"),
    ("sys.stdin.buffer.readline", "input"),
    ("sys.stdin.read().split()", "_ALLDATA.split()"),
    ("sys.stdin.read()", "_ALLDATA"),
    ("sys.stdin.readlines()", "_LINES"),
    ("sys.stdin.readline", "input"),
    ("sys.stdin", "_LINES"),
    ("sys.stdout.write", "_wout"),
    ("sys.stdout.flush()", "None"),
    ("sys.stdout", "_sys.stdout"),
    ("sys.exit", "_exit"),
]


def _rewrite_body(src: str) -> str:
    for a, b in REWRITES:
        src = src.replace(a, b)
    # bare names left behind by `from sys import stdin, stdout`
    src = re.sub(r"(?<![\w.])stdin\.buffer\.read\(\)", "_ALLDATA", src)
    src = re.sub(r"(?<![\w.])stdin\.readline", "input", src)
    src = re.sub(r"(?<![\w.])stdin\.read\(\)", "_ALLDATA", src)
    src = re.sub(r"(?<![\w.])stdin(?![\w])", "_LINES", src)
    src = re.sub(r"(?<![\w.])stdout\.write", "_wout", src)
    src = re.sub(r"(?<![\w.])stdout\.flush\(\)", "None", src)
    # bare exit()/quit() calls (word boundary), incl. exit(0)
    src = re.sub(r"(?<![\w.])exit\s*\(", "_exit(", src)
    src = re.sub(r"(?<![\w.])quit\s*\(", "_exit(", src)
    # __main__ guards -> always true
    src = re.sub(r"__name__\s*==\s*['\"]__main__['\"]", "True", src)
    return src


def _assigned_names(nodes) -> list[str]:
    """Names bound by top-level script statements (not inside defs/classes)."""
    out = set()

    def targets(t):
        if isinstance(t, ast.Name):
            out.add(t.id)
        elif isinstance(t, (ast.Tuple, ast.List)):
            for e in t.elts:
                targets(e)
        elif isinstance(t, ast.Starred):
            targets(t.value)

    for node in nodes:
        for sub in ast.walk(node):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(sub, ast.Assign):
                for tg in sub.targets:
                    targets(tg)
            elif isinstance(sub, (ast.AugAssign, ast.AnnAssign, ast.For, ast.AsyncFor)):
                targets(sub.target)
            elif isinstance(sub, ast.NamedExpr):
                targets(sub.target)
            elif isinstance(sub, ast.withitem) and sub.optional_vars:
                targets(sub.optional_vars)
            elif isinstance(sub, ast.Delete):
                for tg in sub.targets:
                    targets(tg)
    return sorted(n for n in out if n.isidentifier())


def wrap(source: str) -> str | None:
    """Refactory-format module for one CF submission, or None if unadaptable."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    lines = source.splitlines()

    def seg(node):  # verbatim source segment incl. decorators
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        return "\n".join(lines[start - 1:node.end_lineno])

    defs, body, body_nodes = [], [], []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue                                   # global.py supplies these
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs.append(seg(node))
        else:
            body.append(seg(node))
            body_nodes.append(node)
    user_globals = [n for n in _assigned_names(body_nodes)
                    if n not in ("_IN", "_ALLDATA", "_LINES")]

    head = _rewrite_body("\n\n".join(defs))
    script = _rewrite_body("\n".join(body)) or "pass"
    if re.search(r"^def\s+main\s*\(", head, re.M):   # collision with our wrapper
        head = re.sub(r"(?<![\w.])main(?![\w])", "_umain", head)
        script = re.sub(r"(?<![\w.])main(?![\w])", "_umain", script)
    if re.search(r"^\s+def\s", head, re.M) or re.search(r"^\s*def\s", script, re.M):
        return None                                    # nested def: breaks their holes
    if "input(" in head or "print(" in head:
        pass                                           # fine: shims are module-global

    indented = "\n".join("        " + l if l.strip() else l
                         for l in script.splitlines())
    gdecl = "global _IN, _ALLDATA, _LINES" + \
        ("".join(", " + n for n in user_globals) if user_globals else "")
    out = (head + "\n\n" if head.strip() else "") + f'''\
def main(_coep_s):
    {gdecl}
    _ALLDATA = _coep_s
    _LINES = _coep_s.split("\\n")
    _IN = iter(_LINES)
    class _Exit(Exception): pass
    _exit = lambda *a: (_ for _ in ()).throw(_Exit())
    try:
{indented}
    except _Exit:
        pass
'''
    try:
        compile(out, "<wrapped>", "exec")
    except SyntaxError:
        return None
    return out


def _norm(text: str) -> str:
    return " ".join(text.split())


class _Alarm(Exception):
    pass


def simulate(wrapped: str, stdin: str, expected: str, timeout: float = 3.0) -> bool:
    """Mimic Refactory's exec pipeline (sans hole injection) for one test."""
    entry = f"_flush(main({stdin!r})) #print("
    final = GLOBAL_PY + "\n\n" + wrapped + "\n\n" + entry
    buf = io.StringIO()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(_Alarm()))
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        with redirect_stdout(buf):
            exec(final, {})                            # noqa: S102 - sandboxed data prep
    except (_Alarm, Exception):                        # noqa: BLE001
        return False
    except BaseException:                              # SystemExit etc.
        return False
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    return buf.getvalue() == _norm(expected) + "\n"


def export(pid: str, wrong_limit: int = 0, sim_tests: int = 3) -> None:
    prob = json.loads((ROOT / "data" / pid / "problem.json").read_text())
    tests = prob["tests"]
    out = ROOT / "baselines" / "refactory" / "data_cf" / pid
    (out / "ans").mkdir(parents=True, exist_ok=True)
    for sub in ("reference", "correct", "wrong", "fail"):
        (out / "code" / sub).mkdir(parents=True, exist_ok=True)
    (out / "code" / "global.py").write_text(GLOBAL_PY)

    for i, t in enumerate(tests, 1):
        (out / "ans" / f"input_{i:03d}.txt").write_text(
            f"_flush(main({t['stdin']!r})) #print(")
        (out / "ans" / f"output_{i:03d}.txt").write_text(repr(_norm(t["expected"])))

    stats = {"correct_ok": 0, "correct_unadaptable": 0, "correct_sim_fail": 0,
             "wrong_ok": 0, "wrong_unadaptable": 0}
    sample = tests[:sim_tests]

    corr_dir = ROOT / "data" / pid / "correct"
    for f in sorted(corr_dir.glob("*.py")):
        w = wrap(f.read_text())
        if w is None:
            stats["correct_unadaptable"] += 1
            continue
        if not all(simulate(w, t["stdin"], t["expected"]) for t in sample):
            stats["correct_sim_fail"] += 1
            continue
        (out / "code" / "correct" / f.name).write_text(w)
        stats["correct_ok"] += 1

    # reference = shortest exported correct (their pool always includes it)
    kept = sorted((out / "code" / "correct").glob("*.py"),
                  key=lambda p: len(p.read_text()))
    if not kept:
        raise SystemExit(f"{pid}: no adaptable correct solutions")
    (out / "code" / "reference" / "reference.py").write_text(kept[0].read_text())

    wrong_dir = ROOT / "data" / pid / "buggy"
    files = sorted(wrong_dir.glob("*.py"))
    if wrong_limit:
        files = files[:wrong_limit]
    for f in files:
        w = wrap(f.read_text())
        if w is None:
            stats["wrong_unadaptable"] += 1
            continue
        (out / "code" / "wrong" / f.name).write_text(w)
        stats["wrong_ok"] += 1

    print(f"[{pid}] tests={len(tests)}  {stats}  reference={kept[0].name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pids", nargs="+")
    ap.add_argument("--wrong-limit", type=int, default=0)
    args = ap.parse_args()
    for pid in args.pids:
        export(pid, wrong_limit=args.wrong_limit)
