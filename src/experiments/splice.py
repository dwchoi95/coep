"""Rewrite a generated block inside the paper in place.

The paper is a single main.tex plus references.bib, so generated tables and
macros live inside it rather than in \\input files. Each block is delimited by

    % BEGIN GENERATED <name> -- rewritten by `run.py ...`; do not edit
    ...
    % END GENERATED <name>

and the generators replace what is between the markers. Nothing outside a
marked block is ever touched, so hand-written prose and generated numbers can
share the file without either overwriting the other.
"""
from __future__ import annotations

from pathlib import Path

PAPER = Path(__file__).resolve().parents[2] / "paper"
MAIN = PAPER / "main.tex"
# A table lives wherever the paper puts it, and floats move between the paper
# and the supplement as the page budget shifts, so the generator follows the
# fence rather than assuming a file.
TARGETS = (MAIN, PAPER / "supplementary.tex")


def splice(name: str, body: str, by: str) -> Path:
    """Replace the ``name`` block wherever its fence lives, and say where."""
    begin = f"% BEGIN GENERATED {name}"
    end = f"% END GENERATED {name}"
    for target in TARGETS:
        if not target.exists():
            continue
        s = target.read_text()
        i = s.find(begin)
        j = s.find(end)
        if i < 0 or j < 0:
            continue
        head = f"{begin} -- rewritten by `{by}`; do not edit\n"
        target.write_text(s[:i] + head + body.rstrip("\n") + "\n" + s[j:])
        return target
    raise SystemExit(
        f"no '{name}' block in {' or '.join(t.name for t in TARGETS)}; "
        f"expected {begin} ... {end}")
