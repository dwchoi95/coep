"""`run.py package [main|first]` — build a track's AAAI Code and Data Package.

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

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ["src", "run.py", "results", "tools", "README.md", "requirements.txt",
           "LICENSE", ".env.example"]
KOREAN = re.compile(r"^% \[번역\].*$", re.M)

# The two papers are separate submissions and ship separate packages. They share
# the harness and the logs; what differs is which .tex sources go in, since a
# package that carried both would tell a reviewer of one about the other.
TRACKS = {
    "main": ("main.tex", "supplementary.tex", "ReproducibilityChecklist.tex"),
    "first": ("first.tex", "supplementary.tex",
              "ReproducibilityChecklist.tex"),
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    track = argv[0] if argv else "main"
    if track not in TRACKS:
        raise SystemExit(f"track must be one of {', '.join(TRACKS)}")
    papers = TRACKS[track]
    OUT = ROOT / f"artifact_{track}" / "code_and_data"
    print(f"track: {track}")
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
            # This file is excluded from what it builds. It is a submission tool
            # rather than part of the harness, and it carries the identity
            # patterns it greps for, which would themselves be the leak.
            shutil.copytree(src, dst,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                          "make_package.py"))
        else:
            shutil.copy2(src, dst)
        print(f"  {name}")

    # this track's sources only, minus the glosses, plus the shared assets they
    # reference: the two papers are separate submissions, so a package that
    # carried both would tell a reviewer of one about the other
    (OUT / "paper" / track).mkdir(parents=True)
    for f in papers:
        src = ROOT / "paper" / track / f
        if not src.exists():
            print(f"  missing: paper/{track}/{f}")
            continue
        (OUT / "paper" / track / f).write_text(KOREAN.sub("", src.read_text()))
    for name in ("aaai2027.sty", "aaai2027.bst"):
        shutil.copy2(ROOT / "paper" / track / name, OUT / "paper" / track / name)
    for shared in ("references.bib", "build.sh"):
        shutil.copy2(ROOT / "paper" / shared, OUT / "paper" / shared)
    # only the side tables this track's sources actually \input: shipping the
    # others would put a typeset table for a claim the paper never makes in
    # front of a reviewer
    wanted, figs = set(), set()
    for f in papers:
        src = ROOT / "paper" / track / f
        if src.exists():
            text = src.read_text()
            wanted |= set(re.findall(r"\\input\{\.\./tables/([A-Za-z0-9_]+)\}", text))
            figs |= set(re.findall(r"\\includegraphics\[[^]]*\]\{\.\./figures/([^}]+)\}",
                                   text))
    (OUT / "paper" / "figures").mkdir()
    for name in sorted(figs):
        shutil.copy2(ROOT / "paper" / "figures" / name,
                     OUT / "paper" / "figures" / name)
    print(f"  paper/figures/: {len(figs)} used by this track")
    (OUT / "paper" / "tables").mkdir()
    for name in sorted(wanted):
        shutil.copy2(ROOT / "paper" / "tables" / f"{name}.tex",
                     OUT / "paper" / "tables" / f"{name}.tex")
    print(f"  paper/tables/: {', '.join(sorted(wanted)) or 'none'}")
    print(f"  paper/{track}/: {', '.join(papers)} (Korean glosses stripped)")

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

    zf = ROOT / f"artifact_{track}" / "code_and_data.zip"
    if zf.exists():
        zf.unlink()
    subprocess.run(["zip", "-qr", str(zf), "."], cwd=OUT, check=True)
    print(f"\n{zf.relative_to(ROOT)}  {zf.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
