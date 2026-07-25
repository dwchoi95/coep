"""Stage 2: synthesize a problem's repair tool (``tools/<p_id>/fixer.py``).

The builder LLM is called **once per problem** with the problem, a strategy of
reference solutions, and a chosen sample of buggy submissions. It emits a single
module exposing ``class Fixer`` whose ``rules()`` returns candidate-generating
:class:`~src.core.repair.Rule` objects. The harness then *re-validates* that
module against the sample (a tool cannot self-report success) and, if some
samples are still uncovered, refines it — at most ``r_max`` builder calls total.

Build cost is exactly the tokens of those ``<= r_max`` calls, measured
uniformly through :mod:`src.utils.llm`. An ``llm_fn`` hook lets this run without
an API key in tests.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from src.core.cluster import cluster, structural_features
from src.core.repair import Rule, SearchBudget, repair
from src.prompts import render
from src.utils import llm as llm_mod
from src.utils.metrics import rps

_TOOLS = Path(__file__).resolve().parents[2] / "tools"


# --------------------------------------------------------------- Stage-1 samples
def select_samples(buggy: list[str], correct: list[str], n_samples: int = 8,
                   k_per_cluster: int = 6, max_sample_edit: int = 12) -> list[str]:
    """Just the buggy sources from :func:`select_sample_pairs` (compat)."""
    return [b for b, _f in select_sample_pairs(
        buggy, correct, n_samples, k_per_cluster, max_sample_edit)]


def select_sample_pairs(buggy: list[str], correct: list[str], n_samples: int = 8,
                        k_per_cluster: int = 6,
                        max_sample_edit: int = 12) -> list[tuple[str, str]]:
    """Choose build-time (buggy, fixed) pairs: frequent, learnable, and diverse.

    Three forces, learned from watching the builder waste effort on rare tangled
    programs while the common misconceptions went uncovered:

    * **Frequency** — walk clusters largest-first, so the common misconceptions
      (big clusters) are represented before the rare ones.
    * **Learnability** — each cluster contributes the member with the smallest
      **absolute** tree-edit distance to its nearest correct program: a clean,
      single-misconception exemplar a targeted rule can be learned from, not the
      medoid (the most *typical* shape, often a multi-issue mess). Absolute edit,
      not RPS: RPS is normalized by program size, so a 25-line tangle looks
      "close" to a 25-line correct program even when dozens of nodes differ.
    * **Fixability filter** — skip a cluster whose cleanest member still needs
      more than ``max_sample_edit`` node edits: no small-edit rule exists for it,
      so showing it to the builder only invites a wholesale rewrite. Let those
      escalate to the fallback instead.

    Each sample is paired with its **minimum-edit correct program** (the correct
    solution nearest to it by *actual* tree-edit distance, over a shortlist of
    the structurally-closest ``n_targets``). Showing the builder the pair —
    buggy AND its targeted fix — turns "infer the fix, then generalize it" into
    just "generalize this shown repair", which a weak model does far better. No
    LLM call: the fix is a real correct submission, picked locally.

    Returns up to ``n_samples`` ``(buggy, fixed)`` pairs, cleanest first.
    """
    from sklearn.metrics import pairwise_distances

    from src.utils.metrics import ast_size

    if not correct:
        clusters, _ = cluster(buggy)
        return [(buggy[c.medoid], "") for c in clusters[:n_samples]]

    matrix, vec = structural_features(buggy + correct)   # shared vocabulary
    if vec is None:
        clusters, _ = cluster(buggy)
        return [(buggy[c.medoid], "") for c in clusters[:n_samples]]
    X = matrix.toarray() if hasattr(matrix, "toarray") else matrix
    B, C = X[:len(buggy)], X[len(buggy):]
    dist = pairwise_distances(B, C, metric="cosine")     # buggy x correct
    nearest_c = dist.argmin(axis=1)                       # structural nearest fix

    _edit: dict[int, float] = {}
    def edit_to(bi: int) -> float:                        # abs tree edits, cached
        if bi not in _edit:
            ci = int(nearest_c[bi])
            _edit[bi] = rps(buggy[bi], correct[ci]) * ast_size(buggy[bi])
        return _edit[bi]

    csizes = sorted(ast_size(c) for c in correct)
    size_cap = 3 * csizes[len(csizes) // 2]              # 3x median correct size
    clusters, _ = cluster(buggy)                         # largest-first

    picked: list[tuple[float, str, str]] = []
    fallback: list[tuple[float, str, str]] = []
    for cl in clusters:
        # cheap prefilter: members structurally closest to some correct, then
        # pick the true min absolute-edit one among them.
        cands = sorted(cl.members, key=lambda i: dist[i, nearest_c[i]])[:k_per_cluster]
        best = min(cands, key=edit_to)
        e = edit_to(best)
        entry = (e, buggy[best], correct[int(nearest_c[best])])
        fallback.append(entry)
        if e <= max_sample_edit and ast_size(buggy[best]) <= size_cap:
            picked.append(entry)
        if len(picked) >= n_samples:
            break

    # A sparse correct pool makes min-edit-to-nearest-correct a measure of
    # strategy mismatch rather than bug size, so the cap can reject every
    # cluster and leave the builder with no exemplars at all. Degrade to the
    # cleanest clusters available instead: the build loop validates each rule
    # against the samples, so unlearnable exemplars cost one cheap call rather
    # than a tool that was never given anything to generalize from.
    if not picked:
        picked = fallback

    picked.sort(key=lambda t: t[0])                      # cleanest first
    return [(b, f) for _e, b, f in picked[:n_samples]]


# --------------------------------------------------------------- loading a tool
def _exec_module(path: Path, tag: str):
    """Import a standalone tool file with ``Rule`` provided in its namespace."""
    name = f"_{tag}_{path.parent.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__.setdefault("Rule", Rule)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(name, None)
    return mod


def load_fixer(path: str | Path) -> list[Rule]:
    """Import a generated ``fixer.py`` and return its rules, plus any
    self-learned rules in a sibling ``learned.py`` (Stage-4 absorption).

    Raised exceptions (syntax error, bad import, ``rules()`` blowing up) are the
    caller's signal that this build round failed and needs refinement.
    """
    from src.core.generic_rules import generic_rules

    path = Path(path)
    rules = _exec_module(path, "fixer").Fixer().rules()
    if not isinstance(rules, list) or not all(isinstance(r, Rule) for r in rules):
        raise TypeError("Fixer().rules() must return a list[Rule]")
    learned_path = path.parent / "learned.py"
    if learned_path.exists():
        learned = getattr(_exec_module(learned_path, "learned"), "LEARNED", [])
        rules = rules + [r for r in learned if isinstance(r, Rule)]
    # every tool also carries the shared small-edit operators (METHODOLOGY §2.1)
    return rules + generic_rules()


# --------------------------------------------------------------- validation
def _validate(rules: list[Rule], problem: dict, samples: list[str],
              budget: SearchBudget):
    """Repair each sample once; return the per-sample RepairResults."""
    return [repair(b, problem, rules, budget) for b in samples]


# --------------------------------------------------------------- prompt inputs
def _render_tests(problem: dict, limit: int = 8) -> str:
    lines = []
    for t in (problem.get("tests") or [])[:limit]:
        if "stdin" in t:
            lines.append(f"- input {t['stdin']!r} -> {t['expected']!r}")
        else:
            entry = t.get("entry", problem.get("entry"))
            lines.append(f"- {entry}({', '.join(map(repr, t.get('args', [])))}) "
                         f"= {t.get('expected')!r}")
    return "\n".join(lines)


def _render_block(sources: list[str]) -> str:
    return "\n\n".join(f"```python\n{s.strip()}\n```" for s in sources)


def _render_pairs(samples: list[str], fixes: list[str]) -> str:
    """buggy → fixed pairs for the builder to generalize."""
    out = []
    for i, (b, f) in enumerate(zip(samples, fixes), 1):
        out.append(f"### Repair {i}\nBuggy:\n```python\n{b.strip()}\n```\n"
                   f"Fixed:\n```python\n{f.strip()}\n```")
    return "\n\n".join(out)


def _feedback(uncovered: list[str], load_error: str | None) -> str:
    if load_error:
        return ("## This is a refinement round\n"
                "Your previous module failed to load:\n"
                f"```\n{load_error}\n```\nFix it and re-emit the whole module.")
    if not uncovered:
        return ""
    bugs = _render_block(uncovered)
    return ("## This is a refinement round\n"
            "Your previous module loaded but did NOT repair these sample "
            "submissions. Add or fix rules so they pass, keeping the ones that "
            f"already work:\n\n{bugs}")


# --------------------------------------------------------------- the build loop
@dataclass
class BuildResult:
    pid: str
    path: Path | None
    model: str = ""
    seconds: float = 0.0             # build wall-clock (ATT_build, per assignment)
    rules: int = 0
    coverage: float = 0.0            # fraction of sample bugs repaired
    rounds: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    usd: float = 0.0
    n_samples: int = 0
    last_error: str | None = None
    provenance: list[list[str]] = field(default_factory=list)  # rules per sample

    def cost_record(self) -> dict:
        """What gets written to ``cost.json`` next to the tool — the audited
        build cost of this (problem, model) tool."""
        return {"pid": self.pid, "model": self.model, "rules": self.rules,
                "rounds": self.rounds, "n_samples": self.n_samples,
                "sample_coverage": round(self.coverage, 4),
                "in_tokens": self.in_tokens, "out_tokens": self.out_tokens,
                "usd": round(self.usd, 6),
                "build_seconds": round(self.seconds, 2)}


def build(problem: dict, references: list[str], samples: list[str],
          model: str = "claude-sonnet", r_max: int = 3, llm_fn=None,
          out_path: str | Path | None = None,
          budget: SearchBudget | None = None,
          sample_fixes: list[str] | None = None) -> BuildResult:
    """Generate–validate–refine a ``fixer.py`` for one problem.

    ``sample_fixes[i]`` is a correct fix for ``samples[i]``; when given, the
    builder is shown (buggy → fixed) pairs to generalize, which a weak model
    handles far better than inferring the fix itself.
    """
    pid = problem["pid"]
    budget = budget or SearchBudget()
    out = (Path(out_path) if out_path
           else _TOOLS / pid / model / "fixer.py")
    out.parent.mkdir(parents=True, exist_ok=True)

    import time as _time
    _t0 = _time.time()
    res = BuildResult(pid=pid, path=None, model=model, n_samples=len(samples))
    uncovered_srcs: list[str] = []
    load_error: str | None = None
    best_code: str | None = None
    best_cov: float = -1.0
    call = llm_fn or llm_mod.complete
    # The builder emits a whole module; with extended thinking the response needs
    # generous headroom or it truncates before the code block. Only the real API
    # takes this kwarg (test stubs keep their (prompt, model) signature).
    extra = {} if llm_fn else {"max_tokens": 32000}

    sample_block = (_render_pairs(samples, sample_fixes) if sample_fixes
                    else _render_block(samples))
    for rnd in range(r_max):
        prompt = render("build_fixer",
                        description=problem.get("description", ""),
                        tests=_render_tests(problem),
                        references=_render_block(references) or "(none provided)",
                        samples=sample_block,
                        feedback=_feedback(uncovered_srcs, load_error))
        comp = call(prompt, model=model, **extra)
        res.in_tokens += comp.in_tokens
        res.out_tokens += comp.out_tokens
        res.usd += comp.usd
        res.rounds = rnd + 1

        code = comp.code
        if not code:
            load_error = "no python code block in the response"
            continue
        if "import Rule" not in code:             # keep the artifact standalone
            code = "from src.core.repair import Rule\n" + code
        out.write_text(code)

        try:
            rules = load_fixer(out)
        except Exception as e:                       # noqa: BLE001 - fed back
            load_error = f"{type(e).__name__}: {e}"
            res.last_error = load_error
            continue

        load_error = None
        results = _validate(rules, problem, samples, budget)
        cov = sum(r.repaired for r in results) / len(results) if results else 0.0
        if cov > best_cov:                           # keep the best round's tool,
            best_cov, best_code = cov, code          # not whichever ran last
            res.path = out
            res.rules = len(rules)
            res.coverage = cov
            res.provenance = [list(r.rules) for r in results]
        uncov_idx = [i for i, r in enumerate(results) if not r.repaired]
        if not uncov_idx:                            # all samples repaired
            break
        uncovered_srcs = [samples[i] for i in uncov_idx]

    res.seconds = _time.time() - _t0
    # A later round can regress or emit an unloadable module; persist the BEST
    # round's code, never whatever happened to run last (which may not parse).
    if best_code is not None:
        out.write_text(best_code)
    # Persist the audited build cost next to the tool (even if it never loaded,
    # so a failed build's spend is still on the record).
    (out.parent / "cost.json").write_text(json.dumps(res.cost_record(), indent=2))
    return res
