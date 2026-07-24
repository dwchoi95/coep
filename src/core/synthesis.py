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
def select_samples(buggy: list[str], correct: list[str], n_samples: int = 6,
                   k_per_cluster: int = 5) -> list[str]:
    """Choose build-time sample bugs: diverse *and* learnable.

    Cluster the buggy pool structurally (one misconception per cluster), then
    within each of the largest clusters take the member with the **smallest
    edit distance (RPS) to its nearest correct program**. The medoid is the most
    *typical* shape, but often a tangled multi-issue program; the min-edit member
    is a clean single-misconception exemplar the builder can actually learn a
    targeted rule from. Diversity comes from the clustering, learnability from
    the per-cluster min-edit pick.
    """
    from sklearn.metrics import pairwise_distances

    clusters, _ = cluster(buggy)
    clusters = clusters[:n_samples]
    if not correct:
        return [buggy[c.medoid] for c in clusters]

    matrix, vec = structural_features(buggy + correct)   # shared vocabulary
    if vec is None:
        return [buggy[c.medoid] for c in clusters]
    X = matrix.toarray() if hasattr(matrix, "toarray") else matrix
    B, C = X[:len(buggy)], X[len(buggy):]
    dist = pairwise_distances(B, C, metric="cosine")     # buggy x correct
    nearest_c = dist.argmin(axis=1)

    samples = []
    for cl in clusters:
        # cheap prefilter: members structurally closest to some correct, then
        # pick the true min tree-edit-distance one among them.
        cands = sorted(cl.members, key=lambda i: dist[i, nearest_c[i]])[:k_per_cluster]
        best = min(cands, key=lambda i: rps(buggy[i], correct[nearest_c[i]]))
        samples.append(buggy[best])
    return samples


def backend_of(model: str) -> str:
    """Short family label used for the per-model tool directory."""
    if model.startswith("gpt"):
        return "gpt"
    if model.startswith("claude"):
        return "claude"
    return model.split(":", 1)[0]


# --------------------------------------------------------------- loading a tool
def load_fixer(path: str | Path) -> list[Rule]:
    """Import a generated ``fixer.py`` and return its rules.

    Raised exceptions (syntax error, bad import, ``rules()`` blowing up) are the
    caller's signal that this build round failed and needs refinement.
    """
    path = Path(path)
    name = f"_fixer_{path.parent.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # ``Rule`` is the tool's one required symbol; provide it in the namespace so a
    # generated module works whether or not it remembers the import line.
    mod.__dict__.setdefault("Rule", Rule)
    sys.modules[name] = mod                      # so dataclasses/typing resolve
    try:
        spec.loader.exec_module(mod)
        rules = mod.Fixer().rules()
    finally:
        sys.modules.pop(name, None)
    if not isinstance(rules, list) or not all(isinstance(r, Rule) for r in rules):
        raise TypeError("Fixer().rules() must return a list[Rule]")
    return rules


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
    rules: int = 0
    coverage: float = 0.0            # fraction of sample bugs repaired
    rounds: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    usd: float = 0.0
    last_error: str | None = None
    provenance: list[list[str]] = field(default_factory=list)  # rules per sample


def build(problem: dict, references: list[str], samples: list[str],
          model: str = "claude-sonnet", r_max: int = 3, llm_fn=None,
          out_path: str | Path | None = None,
          budget: SearchBudget | None = None) -> BuildResult:
    """Generate–validate–refine a ``fixer.py`` for one problem."""
    pid = problem["pid"]
    budget = budget or SearchBudget()
    out = (Path(out_path) if out_path
           else _TOOLS / pid / backend_of(model) / "fixer.py")
    out.parent.mkdir(parents=True, exist_ok=True)

    res = BuildResult(pid=pid, path=None)
    uncovered_srcs: list[str] = []
    load_error: str | None = None
    call = llm_fn or llm_mod.complete
    # The builder emits a whole module; with extended thinking the response needs
    # generous headroom or it truncates before the code block. Only the real API
    # takes this kwarg (test stubs keep their (prompt, model) signature).
    extra = {} if llm_fn else {"max_tokens": 32000}

    for rnd in range(r_max):
        prompt = render("build_fixer",
                        description=problem.get("description", ""),
                        tests=_render_tests(problem),
                        references=_render_block(references) or "(none provided)",
                        samples=_render_block(samples),
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
        res.path = out
        res.rules = len(rules)
        res.coverage = (sum(r.repaired for r in results) / len(results)
                        if results else 0.0)
        res.provenance = [list(r.rules) for r in results]
        uncov_idx = [i for i, r in enumerate(results) if not r.repaired]
        if not uncov_idx:                            # all samples repaired
            break
        uncovered_srcs = [samples[i] for i in uncov_idx]

    return res
