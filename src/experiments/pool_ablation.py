"""Does the authored rule layer matter when the reference pool is thin?

The tool is held fixed; only the pool the transplant may draw on at repair time
is restricted. That isolates the substrate's dependence on pool depth without
paying to rebuild a tool per pool size. A full cold start would also rebuild,
and costs money; this does not.

For each pool size k we run two arms over the same submissions:
  full   = the frozen tool as shipped (authored rules + always-on + transplant)
  fw     = the same tool with the builder's rules removed
"""
import argparse, json, random, time

from src.core.reference_repair import ReferenceIndex, local_repair
from src.core.repair import SearchBudget
from src.core.synthesis import load_fixer
from src.experiments._common import load_pool, load_problem, tool_path
from src.experiments.tables import ORDER, IDS, ROOT
from src.utils.metrics import rps

MODEL = "claude-sonnet-5"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-problem", type=int, default=20)
    ap.add_argument("--ks", default="0,1,2,5,10,-1")   # -1 = the whole pool
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    ks = [int(x) for x in args.ks.split(",")]
    budget = SearchBudget()
    rows = []
    for pid in ORDER:
        prob = load_problem(pid)
        correct = load_pool(pid, "correct")
        names = sorted(p.stem for p in (ROOT / "data" / pid / "buggy").glob("*.py"))
        rng = random.Random(args.seed)
        pick = names if len(names) <= args.per_problem else rng.sample(names, args.per_problem)
        srcs = [(n, (ROOT / "data" / pid / "buggy" / f"{n}.py").read_text()) for n in pick]
        rules_all = load_fixer(tool_path(pid, MODEL, "tools"))
        rules_fw = [r for r in rules_all if r.name.startswith("generic_")]
        for k in ks:
            if k < 0:
                pool = correct
            elif k == 0:
                pool = []
            else:
                pool = random.Random(args.seed).sample(correct, min(k, len(correct)))
            index = ReferenceIndex(pool) if pool else ReferenceIndex([])
            for arm, rules in (("full", rules_all), ("fw", rules_fw)):
                t0 = time.time()
                for name, src in srcs:
                    res = local_repair(src, prob, rules, index, budget)
                    rows.append({"pid": IDS[pid], "k": k, "arm": arm, "buggy": name,
                                 "fixed": bool(res.repaired),
                                 "source": res.source if res.repaired else "none",
                                 "rps": rps(src, res.patch) if res.repaired else None})
                print(f"  {IDS[pid]:<3} k={k:<3} {arm:<5} {len(srcs)} subs "
                      f"in {time.time()-t0:5.1f}s", flush=True)
    if args.out:
        open(args.out, "w").write(json.dumps(rows))
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main()
