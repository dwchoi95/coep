"""Build the AAAI Code and Data Package.

Reviewers are told to assume anything not in the submission will never exist,
so the package has to carry the harness, the logs and the synthesized tools
rather than promise them. Two things are stripped on the way out: the Korean
glosses that sit above every paragraph of main.tex, which are a
deanonymisation surface, and .git, whose messages carry an address and a
session URL.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifact" / "code_and_data"
INCLUDE = ["src", "run.py", "results", "tools", "README.md", "requirements.txt",
           "LICENSE", ".env.example"]
KOREAN = re.compile(r"^% \[번역\].*$", re.M)


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name in INCLUDE:
        src = ROOT / name
        if not src.exists():
            print(f"  missing: {name}")
            continue
        dst = OUT / name
        if src.is_dir():
            shutil.copytree(src, dst,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dst)
        print(f"  {name}")

    # the paper sources, minus the glosses
    (OUT / "paper").mkdir()
    for f in ("main.tex", "supplementary.tex", "references.bib"):
        text = (ROOT / "paper" / f).read_text()
        (OUT / "paper" / f).write_text(KOREAN.sub("", text))
    print("  paper/*.tex (Korean glosses stripped)")

    # a representative subset of the corpora if the whole thing is too large
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"\npackage: {size / 1e6:.1f} MB before data")
    data = ROOT / "data"
    shutil.copytree(data, OUT / "data",
                    ignore=shutil.ignore_patterns("__pycache__"))
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"package: {size / 1e6:.1f} MB with data")

    leaks = []
    for p in OUT.rglob("*"):
        if not p.is_file() or p.suffix in {".pdf", ".pyc"}:
            continue
        try:
            t = p.read_text(errors="ignore")
        except Exception:
            continue
        for pat in ("dwchoi", "skku", "성균관", "claude.ai/code/session"):
            if pat in t:
                leaks.append((p.relative_to(OUT), pat))
    print("identity leaks:", leaks or "none")

    zf = ROOT / "artifact" / "code_and_data.zip"
    if zf.exists():
        zf.unlink()
    subprocess.run(["zip", "-qr", str(zf), "."], cwd=OUT, check=True)
    print(f"\n{zf.relative_to(ROOT)}  {zf.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
