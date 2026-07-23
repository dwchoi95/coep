#!/usr/bin/env python3
"""Generate per-instance repair prompts for the baseline (conventional
LLM-per-submission APR). One prompt file per evaluation instance."""
import json
import pathlib
import sys

V1 = pathlib.Path(__file__).resolve().parent      # v1 package (coep/)
ROOT = V1.parents[2] / "results" / "v1"            # v1 data archive
sys.path.insert(0, str(V1))
from coep.prompts import baseline_repair_prompt  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
OUT = ROOT / "runs" / "baseline"


def main():
    splits = json.loads((ROOT / "benchmark" / "splits.json").read_text())
    (OUT / "prompts").mkdir(parents=True, exist_ok=True)
    (OUT / "responses").mkdir(parents=True, exist_ok=True)
    manifest = []
    for pid, split in sorted(splits.items()):
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        for name in split["eval"]:
            src = (PROBLEMS / pid / "buggy" / name).read_text()
            key = f"{pid}__{name[:-3]}"
            (OUT / "prompts" / f"{key}.md").write_text(baseline_repair_prompt(p, src))
            manifest.append({"key": key, "pid": pid, "bug": name})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote {len(manifest)} prompts to {OUT / 'prompts'}")


if __name__ == "__main__":
    main()
