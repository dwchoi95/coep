"""Does the builder's rule layer matter when the reference pool is thin?

The tool is held fixed; only the pool the transplant may draw on at repair time
is restricted. That isolates the substrate's dependence on pool depth without
paying to rebuild a tool per pool size. A full cold start would also rebuild,
and costs money; this does not.

Two things this gets right that the obvious version does not:

* **Submissions the builder saw are excluded.** Roughly half of each
  assignment's buggy pool ends up in the build set, and on those the authored
  rules are answering a program they were written from. Scoring them measures
  memorisation, not the layer.
* **Pool draws are repeated.** For k > 0 the pool is a sample of the correct
  programs, and one draw is one accident; each k is run over several seeds.

For each pool size k we run two arms over the same submissions:
  full   = the frozen tool as shipped (builder rules + always-on + transplant)
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-problem", type=int, default=15)
    ap.add_argument("--ks", default="0,1,2,5,-1")   # -1 = the whole pool
    ap.add_argument("--seeds", type=int, default=3, help="pool draws per k > 0")
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    ks = [int(x) for x in args.ks.split(",")]
    from src.core.synthesis import select_sample_pairs
    budget = SearchBudget()
    rows = []
    for pid in ORDER:
        prob = load_problem(pid)
        correct = load_pool(pid, "correct")
        buggy = load_pool(pid, "buggy")
        names = sorted(p.stem for p in (ROOT / "data" / pid / "buggy").glob("*.py"))
        # the builder was shown roughly half of these; scoring them would
        # measure whether a rule remembers the program it was written from.
        # Submissions are deduplicated by text, so one source can carry several
        # names and every one of them has to go, not just the last.
        by_src: dict[str, list[str]] = {}
        for src_text, name in zip(buggy, names):
            by_src.setdefault(src_text, []).append(name)
        seen = {n for b, _f, _n in select_sample_pairs(buggy, correct)
                for n in by_src.get(b, ())}
        pool_of = [n for n in names if n not in seen]
        rng = random.Random(args.seed)
        pick = (pool_of if len(pool_of) <= args.per_problem
                else rng.sample(pool_of, args.per_problem))
        srcs = [(n, (ROOT / "data" / pid / "buggy" / f"{n}.py").read_text()) for n in pick]
        rules_all = load_fixer(tool_path(pid, MODEL, "tools"))
        rules_fw = [r for r in rules_all if r.name.startswith("generic_")]
        for k in ks:
            # k = 0 and the whole pool are deterministic; only a sampled pool
            # needs repeating
            seeds = [args.seed] if k <= 0 else range(args.seeds)
            for sd in seeds:
                if k < 0:
                    pool = correct
                elif k == 0:
                    pool = []
                else:
                    pool = random.Random(sd).sample(correct, min(k, len(correct)))
                index = ReferenceIndex(pool) if pool else ReferenceIndex([])
                for arm, rules in (("full", rules_all), ("fw", rules_fw)):
                    t0 = time.time()
                    for name, src in srcs:
                        res = local_repair(src, prob, rules, index, budget)
                        rows.append({"pid": IDS[pid], "k": k, "seed": sd,
                                     "arm": arm, "buggy": name,
                                     "fixed": bool(res.repaired),
                                     "source": res.source if res.repaired else "none",
                                     "rps": rps(src, res.patch) if res.repaired else None})
                    print(f"  {IDS[pid]:<3} k={k:<3} s{sd} {arm:<5} {len(srcs)} subs "
                          f"in {time.time()-t0:5.1f}s", flush=True)
    if args.out:
        open(args.out, "w").write(json.dumps(rows))
    print(f"{len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
