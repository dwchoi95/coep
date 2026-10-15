"""Shared helpers for the experiment drivers (data loading, .env, arg parsing)."""
from __future__ import annotations

import json
import os
from pathlib import Path


def load_env(path: str = ".env") -> None:
    """Load KEY=VALUE lines from .env into os.environ (llm.py reads os.environ)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_problem(pid: str, root: str = "benchmark", amplified: str | None = None) -> dict:
    """<root>/<pid>/problem.json: the description and the instructor's tests T.

    With ``amplified=<model>``, the tests are T+ = T plus the suite that
    builder's generator produced (benchmark/<pid>/amplified/<model>/tests.json,
    R1-R5); where none exists, T+ = T.
    """
    prob = json.loads((Path(root) / pid / "problem.json").read_text())
    amp = Path(root) / pid / "amplified" / str(amplified) / "tests.json"
    if amplified and amp.exists():
        prob = dict(prob, tests=prob["tests"] + json.loads(amp.read_text()))
    return prob


def load_pool(pid: str, kind: str, root: str = "benchmark") -> list[str]:
    """Read every .py under benchmark/<pid>/<kind> (kind = 'buggy' | 'correct')."""
    d = Path(root) / pid / kind
    return [f.read_text() for f in sorted(d.glob("*.py"))]


def tool_path(pid: str, model: str, root: str = "tools") -> Path:
    """tools/<pid>/<model>/fixer.py — the tool directory is the model name."""
    return Path(root) / pid / model / "fixer.py"
