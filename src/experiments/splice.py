"""Rewrite a generated block inside paper/main.tex in place.

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


def splice(name: str, body: str, by: str) -> None:
    """Replace the ``name`` block in main.tex with ``body``."""
    s = MAIN.read_text()
    begin = f"% BEGIN GENERATED {name}"
    end = f"% END GENERATED {name}"
    i = s.find(begin)
    j = s.find(end)
    if i < 0 or j < 0:
        raise SystemExit(f"main.tex has no '{name}' block; expected {begin} ... {end}")
    head = f"{begin} -- rewritten by `{by}`; do not edit\n"
    MAIN.write_text(s[:i] + head + body.rstrip("\n") + "\n" + s[j:])
