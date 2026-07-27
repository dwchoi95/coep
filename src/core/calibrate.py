"""Build-time calibration of the escalation threshold.

The local tool's acceptance test is "the patch passes the instructor's tests",
which says nothing about patch size, so reference transplant can and does return
patches larger than the student's whole program. The rule layer has the opposite
contract -- a rule that cannot express a targeted edit must abstain -- and this
module gives the transplant layer the same one: a patch that is anomalously
large *for this assignment* is not claimed, it is escalated.

The threshold is a property of the assignment, computed once at build time from
the tool's own behaviour and frozen with it:

    tau_p = min( median(RPS_p) + K * MAD(RPS_p),  RPS_CAP )

over the patches the freshly built tool produces for the assignment's own buggy
programs, counting only those that pass the tests. Running the tool costs no API
call, so calibration does not touch the once-per-assignment claim.

The cap is there because a purely relative threshold reads a bad distribution as
normal. On cf_131A the outlier rule puts tau at 1.71, so 78 submissions whose
patch is *larger than the program it repairs* are accepted as typical. RPS above
1 is not a repair under any assignment's standards -- it is a rewrite -- so the
threshold never sits above it. Escalating that band on cf_131A pulled its mean
from 1.316 to 1.115 and the assignment's from 0.832 to 0.804 for $0.06. On five
of the eleven assignments the cap never binds, because the outlier rule is
already below it: it sleeps where the pool is dense and wakes where it is
sparse.

Two choices are worth stating plainly. ``MAD`` rather than the standard
deviation, because the outliers being detected inflate the standard deviation
enough to hide themselves: on refactory_q1, ``mean + 3*sd`` flags 5 of 557
patches where ``median + 3*MAD`` flags 45. And the median as the anchor rather
than a bare multiple of MAD, because MAD is a spread, not a location -- on
cf_11B (median 0.839, MAD 0.199) the threshold ``3*MAD = 0.597`` sits *below*
the median and would flag most of the corpus.

``K = 3`` is the conventional outlier cutoff, the robust counterpart of
three-sigma. It is not fitted: the distributions here are right-skewed and
heavy-tailed, so it flags 6.5% of patches rather than the 0.3% a normal
distribution would give, and the rate is left to the data -- 0.0% on
refactory_q3, 13.7% on refactory_q4.
"""
from __future__ import annotations

import json
import zlib
from pathlib import Path

from src.core.reference_repair import ReferenceIndex, local_repair
from src.core.repair import SearchBudget
from src.utils.metrics import rps

K = 3.0
# A patch at least as large as the program it repairs is a rewrite, not a
# repair; the threshold never exceeds this regardless of the distribution.
RPS_CAP = 1.0
# MAD scaled to estimate sigma (for a normal distribution MAD = 0.6745 sigma).
MAD_TO_SIGMA = 1.4826
# Below this many test-passing patches the median and MAD are too unstable to
# define an outlier; the gate stays off and escalation reverts to local failure
# only, which is also what happens when the tool repairs nothing at all.
MIN_CALIBRATION = 20
# Cross-fitting folds. Each submission is judged by a threshold estimated from
# the other folds, so no submission's own patch size enters the rule that
# decides whether it is escalated, while the evaluation set stays whole.
FOLDS = 5


def fold_of(stem: str, k: int = FOLDS) -> int:
    """Deterministic fold for a submission id (``hash`` is salted per process)."""
    return zlib.crc32(stem.encode()) % k


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mad(xs: list[float]) -> float:
    """Median absolute deviation, scaled to be comparable to a std deviation."""
    m = _median(xs)
    return MAD_TO_SIGMA * _median([abs(x - m) for x in xs])


def threshold(rps_values: list[float], k: float = K) -> float | None:
    """``min(median + k*MAD, RPS_CAP)``; ``None`` when too little to calibrate."""
    if len(rps_values) < MIN_CALIBRATION:
        return None
    return min(_median(rps_values) + k * mad(rps_values), RPS_CAP)


def calibrate(problem: dict, rules, buggy: list[str], correct: list[str],
              budget: SearchBudget | None = None, k: float = K,
              stems: list[str] | None = None) -> dict:
    """Run the built tool over the assignment's own buggy programs and derive
    the escalation threshold from the patches that pass the tests.

    Records two thresholds. ``rps_tau`` is estimated from every patch and is
    what a deployment ships, where the calibration cohort is last term's
    submissions rather than the ones being repaired. ``rps_tau_folds`` holds one
    threshold per cross-fitting fold, each estimated with that fold held out, so
    a single-cohort evaluation can report numbers no submission influenced the
    rule for.
    """
    budget = budget or SearchBudget(max_candidates=150, max_combo=2,
                                    candidate_timeout=3)
    index = ReferenceIndex(correct)
    stems = stems or [str(i) for i in range(len(buggy))]
    values: list[float] = []
    per_fold: dict[int, list[float]] = {i: [] for i in range(FOLDS)}
    repaired = noop = 0
    for stem, src in zip(stems, buggy):
        res = local_repair(src, problem, rules, index, budget)
        if res.source == "noop":
            noop += 1
            continue
        if res.repaired:
            repaired += 1
            v = rps(src, res.patch)
            values.append(v)
            per_fold[fold_of(stem)].append(v)
    tau = threshold(values, k)
    # fold f is judged by a threshold fitted on everything except fold f
    folds = {f: threshold([v for g, vs in per_fold.items() if g != f for v in vs], k)
             for f in range(FOLDS)}
    rec = {"rps_tau": tau, "rps_tau_k": k, "rps_cap": RPS_CAP,
           "rps_tau_folds": {str(f): (round(t, 4) if t is not None else None)
                             for f, t in folds.items()},
           "rps_fold_k": FOLDS,
           "calibration_n": len(values),
           "calibration_noop": noop,
           "calibration_repaired": repaired}
    if values:
        rec["rps_median"] = round(_median(values), 4)
        rec["rps_mad"] = round(mad(values), 4)
        rec["rps_gate_rate"] = (round(sum(v > tau for v in values) / len(values), 4)
                                if tau is not None else 0.0)
    if tau is not None:
        rec["rps_tau"] = round(tau, 4)
    return rec


def write_into_cost(tool_fixer: Path, record: dict) -> Path:
    """Merge the calibration into the tool's ``cost.json``."""
    path = Path(tool_fixer).parent / "cost.json"
    d = json.loads(path.read_text()) if path.exists() else {}
    d.update(record)
    path.write_text(json.dumps(d, indent=2))
    return path


def load_threshold(tool_fixer: Path, mode: str = "pool"):
    """The frozen threshold for a built tool, or ``None`` if uncalibrated.

    ``mode="pool"`` returns the single deployed threshold. ``mode="crossfit"``
    returns a callable ``stem -> tau`` that serves each submission the
    threshold fitted without its fold.
    """
    path = Path(tool_fixer).parent / "cost.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    if mode == "crossfit":
        folds = d.get("rps_tau_folds")
        if not folds:
            return None
        table = {int(f): (float(t) if t is not None else None)
                 for f, t in folds.items()}
        k = int(d.get("rps_fold_k", FOLDS))
        return lambda stem: table.get(fold_of(stem, k))
    v = d.get("rps_tau")
    return float(v) if v is not None else None
