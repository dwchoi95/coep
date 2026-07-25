"""Build-time calibration of the escalation threshold.

The local tool's acceptance test is "the patch passes the instructor's tests",
which says nothing about patch size, so reference transplant can and does return
patches larger than the student's whole program. The rule layer has the opposite
contract -- a rule that cannot express a targeted edit must abstain -- and this
module gives the transplant layer the same one: a patch that is anomalously
large *for this assignment* is not claimed, it is escalated.

The threshold is a property of the assignment, computed once at build time from
the tool's own behaviour and frozen with it:

    tau_p = median(RPS_p) + K * MAD(RPS_p)

over the patches the freshly built tool produces for the assignment's own buggy
programs, counting only those that pass the tests. Running the tool costs no API
call, so calibration does not touch the once-per-assignment claim.

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
from pathlib import Path

from src.core.reference_repair import ReferenceIndex, local_repair
from src.core.repair import SearchBudget
from src.utils.metrics import rps

K = 3.0
# MAD scaled to estimate sigma (for a normal distribution MAD = 0.6745 sigma).
MAD_TO_SIGMA = 1.4826
# Below this many test-passing patches the median and MAD are too unstable to
# define an outlier; the gate stays off and escalation reverts to local failure
# only, which is also what happens when the tool repairs nothing at all.
MIN_CALIBRATION = 20


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mad(xs: list[float]) -> float:
    """Median absolute deviation, scaled to be comparable to a std deviation."""
    m = _median(xs)
    return MAD_TO_SIGMA * _median([abs(x - m) for x in xs])


def threshold(rps_values: list[float], k: float = K) -> float | None:
    """``median + k*MAD``; ``None`` when there is too little to calibrate on."""
    if len(rps_values) < MIN_CALIBRATION:
        return None
    return _median(rps_values) + k * mad(rps_values)


def calibrate(problem: dict, rules, buggy: list[str], correct: list[str],
              budget: SearchBudget | None = None, k: float = K) -> dict:
    """Run the built tool over the assignment's own buggy programs and derive
    the escalation threshold from the patches that pass the tests."""
    budget = budget or SearchBudget(max_candidates=150, max_combo=2,
                                    candidate_timeout=3)
    index = ReferenceIndex(correct)
    values: list[float] = []
    repaired = noop = 0
    for src in buggy:
        res = local_repair(src, problem, rules, index, budget)
        if res.source == "noop":
            noop += 1
            continue
        if res.repaired:
            repaired += 1
            values.append(rps(src, res.patch))
    tau = threshold(values, k)
    rec = {"rps_tau": tau, "rps_tau_k": k, "calibration_n": len(values),
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


def load_threshold(tool_fixer: Path) -> float | None:
    """The frozen threshold for a built tool, or ``None`` if uncalibrated."""
    path = Path(tool_fixer).parent / "cost.json"
    if not path.exists():
        return None
    v = json.loads(path.read_text()).get("rps_tau")
    return float(v) if v is not None else None
