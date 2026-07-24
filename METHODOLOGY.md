# CoEP Methodology (v2)

The consolidated method, as decided through the dataset and design discussions.
This supersedes the scattered notes in PLAN.md §3 and is the reference for the
Phase-3 implementation and the paper's Approach section.

---

## 0. The one idea

Per-submission LLM repair spends the model **once per submission**. CoEP spends
it **once per problem**: an LLM agent reads a problem and writes a deterministic,
executable *repair tool*; that tool then fixes every subsequent submission
locally at zero marginal LLM cost. The tool is an artifact — readable,
auditable, versionable, improvable — not a service call.

Formally, for a problem `A = (d, T, R_pool, B_pool)` — description, test suite,
pool of correct programs, pool of buggy programs — CoEP produces a tool
`ρ_A : program → patch ∪ {⊥}`, and deploys the hybrid

```
repair(b) = ρ_A(b)            if ρ_A(b) ≠ ⊥      (local, ~0 cost)
          = LLM(d, T, b)      otherwise           (escalation)
```

Everything below is how `ρ_A` gets built, what it contains, and how it runs.

---

## 1. Build-time input selection (Stage 1) — core contribution

The builder does **not** see the whole pool. It sees a small, *chosen* sample.
How that sample is chosen is a contribution, not a detail: a random `N` bugs
waste the LLM's attention on near-duplicates and miss rare misconceptions.

**Cluster the buggy pool for diversity, take the most *learnable* member of
each cluster.** Two forces: clustering gives one representative per
misconception; the per-cluster pick makes that representative one the builder
can actually turn into a small, targeted rule.

Only build-time-available information is used (buggy programs are unlabeled; we
never look at held-out submissions). The implemented pipeline
(`src/core/synthesis.select_samples`, `src/core/cluster`):

- **Structural view** `φ_str(b)` — TF-IDF over normalized-AST path n-grams
  (identifiers/literals folded, as in the RPS labeler); captures *what shape a
  program has*. Cluster with average-linkage agglomerative clustering under a
  cosine-distance threshold (no `k` needed; count derived from the data).
- **Representative = the min-edit member, not the medoid.** For each of the
  largest clusters, pick the member with the **smallest tree-edit distance (RPS)
  to its nearest correct program**. The medoid is the most *typical* shape but
  is often a tangled, multi-issue program; the min-edit member is a clean
  single-misconception exemplar a targeted rule can be learned from. (We saw
  this directly: medoid samples left both cheap builders at 0% sample coverage;
  min-edit samples are learnable.) Nearest correct is found on the same
  structural view; RPS is computed only for a small structurally-closest
  shortlist per cluster, so selection stays cheap.
- `N` = number of clusters kept (a small budget, e.g. 6 in the smoke tests).

**References** are chosen on the structural view too, but as **medoids** (a
*typical* correct solution per strategy is what we want to show the builder, not
an edge case): cluster `R_pool`, take medoids → a strategy-diverse reference set
rather than `k` arbitrary solutions. The same structural featurizer also drives
the fallback's strategy-matched reference (§4).

**Deferred, not discarded.** A richer selector — adding the behavioral view
(per-test outcome signature from `TestResult.signature()`), a density clusterer
that labels and keeps outliers, and an `α` weight between the two views — is a
natural extension left as an open knob (§7); the structural + min-edit selector
is what is implemented and evaluated now.

**Why this earns its keep (ablation):** random-`N` vs clustered-`N` at *matched*
`N`, held-out RR. Secondary result: the cluster count is itself a cheap,
build-time predictor of how hard an assignment is to cover by rules — a routing
signal for spending a larger build budget where it pays.

---

## 2. Tool synthesis (Stage 2) — generate–validate–refine

The builder LLM receives: `d`, `T`, the chosen references, and the chosen sample
bugs, plus a span-splice helper and a worked example (`src/prompts/build_fixer.md`).
It emits a single module exposing `class Fixer` whose `rules()` returns a list of
`Rule` objects — the *candidate generators* consumed by `src/core/repair.py`.
The generated file is a standalone artifact (the one required import,
`from src.core.repair import Rule`, is ensured on disk).

**One tool per (problem, model).** We build with the two cheapest models —
`claude-haiku-4-5` and `gpt-5.4-nano` — writing `tools/<p_id>/claude/fixer.py`
and `tools/<p_id>/gpt/fixer.py` from the *same* Stage-1 selection, so the only
variable between them is the builder LLM. Every builder call is priced through
`src/utils/llm` (official SDK usage, not `litellm`), and the build cost is
recorded next to the tool (§5).

### 2.1 What a rule is
A rule maps a source string to zero or more edited source strings, and carries:
- a **name** stating the misconception it targets (e.g. `off_by_one_range`,
  `wrong_return_reversed`), and
- declared **symptoms** (failure classes it addresses), used only for search
  ordering, never for correctness.

**No wholesale rewrites.** A rule must make a *small, local* edit — a changed
operator, one rewritten expression, an inserted/removed statement. A rule that
replaces an entire function or module with a fixed "canonical" solution is
forbidden even though it passes tests: it inflates RPS to that of a full rewrite
and collapses the misconception profile to a single meaningless label (an early
builder did exactly this — 99.5% RR at mean RPS 0.64, every repair attributed to
one "canonical rewrite" rule). If no targeted edit fits, the tool abstains and
the submission escalates (§4). The builder prompt states this, and the intended
final guard is structural (reject a candidate whose edit span covers a whole
`FunctionDef` body or the module).

Two kinds compose in every tool:
- **Problem-specific rules** — the builder's creative work: rewrites that
  anticipate *this* problem's misconceptions (a wrong base case, an
  order-destroying dedup, a copied-from-last-exercise helper). These generate
  edits far outside any fixed operator set, and v1 showed *they*, not the
  generic search, carry the paradigm.
- **Generic edit search** — a shared library (`candidates_generic`): operator
  swaps, off-by-one shifts, boolean flips, index/argument shifts, singly and in
  pairs. The mutation-inversion baseline that catches simple slips.

### 2.2 The hard-won constraint: locate on AST, apply as source splice
`NodeTransformer` **locates** edits; it must not **print** them. Rendering a
patched tree with `ast.unparse` reformats untouched lines and inflates patch
size — in v1 this was the single largest builder failure mode (one builder went
0/5 → 5/5 only after switching to byte-range splices on the original source).
The `fixer.py` contract therefore requires: find the span on the AST, replace
that span in the original text, leave every other byte identical.

### 2.3 Generate–validate–refine loop
A single-shot module can contain its own defects, so the harness closes the
loop (≤ `R_max = 3` rounds):

```
ρ ← LLM_build(d, T, refs, sample_bugs, lib)         # single shot
repeat up to R_max−1 times:
    outcomes ← {(b, run ρ on b) for b in sample_bugs}   # independent re-validation
    if all repaired: stop
    ρ ← LLM_refine(ρ, outcomes + failing sources)   # single shot
```

Re-validation is done by the harness, never self-reported — a tool cannot claim
success. Refinement feedback includes the *still-failing sample sources*, which
is what unstuck the hardest v1 builders. Build cost is therefore exactly the
token count of ≤ `2·R_max` message payloads, measured from the raw strings.

---

## 3. Deployment-time repair (Stage 3) — rule-combination search

Given a new buggy program, the frozen tool searches rule combinations until the
tests pass:

```
signature ← run tests once (also the behavioral view)
order rules by symptom-match against signature       # promising rules first
for k = 1 … max_combo:                                # 1 rule, then pairs, …
    for each ordered rule combination of length k:
        for each candidate the combination emits:
            if candidate passes ALL tests (stop_early): return it, with provenance
return ⊥                                              # abstain → escalate
```

- **Termination = all tests pass.** There is *no* RPS gate. RPS is measured and
  reported afterward, never used to reject a repair. (This retires the
  τ-provenance objection from earlier reviews.)
- **Bounded, not blind.** Symptom-ordered priority/beam search under an explicit
  candidate/time budget, not a `2^|rules|` sweep.
- **Provenance is recorded.** Every returned patch carries the ordered list of
  rule names that produced it. Aggregated across a class, this is a
  *misconception profile* — how often each rule fired, on which programs — the
  diagnostic an instructor gets for free and an LLM API never produces. (v1
  discarded this; recovering it after the fact was impossible.)
- **Safety.** A tool's patch is re-validated by the grading harness before a
  student sees it, so a defective tool degrades to ⊥ (escalation), never to a
  wrong "repair". Escalated submissions take the conventional LLM path and their
  cost is counted against CoEP in every comparison.

---

## 4. Fallback and self-learning (Stage 4)

Submissions the tool abstains on go to the LLM. Two things happen:

1. **Escalation.** `LLM(d, T, b, r)` produces the patch, priced normally, where
   `r` is one **reference program guided to the buggy submission**: cluster the
   correct pool `R` on the structural view, and pick `r` at random from the
   cluster whose medoid is closest (structurally) to `b`. This gives the LLM a
   *strategy-matched* worked solution — a correct program that most likely
   solves the problem the same way the student tried to — rather than an
   arbitrary reference. Selection is local (no LLM cost) and reuses the Stage-1
   structural featurizer. This is the tail the hybrid never sacrifices coverage
   on.
2. **Self-learning.** When the LLM repairs a program the tool missed, diff
   (buggy, fixed), and ask the LLM to *generalize that single repair into a new
   rule* (same `fixer.py` contract: AST-located, source-spliced, named,
   symptom-declared). Append it to the tool.

The tool therefore **improves across a term**: coverage as a function of
accumulated fallbacks is a measurable curve. This is the stateful counterpart to
per-submission repair's statelessness — and the LLM-side analogue (accumulating
few-shot examples) we already showed does not help.

---

## 5. What each stage costs (the economic claim)

| Stage | LLM cost | When |
|---|---|---|
| 1. Selection | none (local clustering + RPS) | once per problem |
| 2. Synthesis | ≤ `R_max` builder calls | once per (problem, model) |
| 3. Local repair | **zero** | every covered submission |
| 4. Fallback | one per-submission call | only on abstention |
| 4. Self-learning | one call per absorbed miss | amortized into future coverage |

Stage-2 cost is measured exactly (official-SDK token usage, extended-thinking
tokens included) and **written alongside each tool** as `tools/<p_id>/<model>/
cost.json` — build tokens, USD, rounds, and sample coverage — so `C_build` is an
audited number, not an estimate. As an illustration, `refactory_q1` built for
about **$0.04** with `claude-haiku-4-5` and **$0.004** with `gpt-5.4-nano`.

Break-even against per-submission repair: `N* = C_build / (Δ·(1−f))`, where
`C_build` is Stage-2 cost, `Δ` the per-submission saving, `f` the abstention
rate. Invariant to token price (both `C_build` and `Δ` scale together), so
"just use a cheaper/open model" shrinks both sides equally and does not change
`N*` — the claim is about *how many model calls per specification* (N → 1), not
about the price of a call.

---

## 6. Why a local tool, not just cheaper LLM calls (the defense)

Cost is one axis; the artifact buys five more that a service call cannot:

1. **Diagnosis** — the rule-firing profile is a per-class misconception report.
2. **Statefulness** — the tool accumulates coverage; API calls start from zero
   every term.
3. **Consistency/fairness** — same misconception → same rule → same feedback;
   deterministic and auditable, where an LLM may rewrite one student and
   minimally patch another for the same bug.
4. **Verified search at scale** — thousands of candidates enumerated and checked
   for free; an LLM retry is another inference.
5. **Offline / institutional** — student code never leaves the institution, runs
   with no GPU, and instructors can *edit the rules* (turn off a give-away fix,
   surface the failing test instead). Self-hosting an open model gives none of
   these.

Framing: **repair-as-an-artifact**, not repair-as-a-service. Cost is the
consequence, not the whole thesis.

---

## 7. Open design points

Settled:
- **Sample selection** = structural clustering + per-cluster min-edit-to-nearest-
  correct member (§1). References = structural medoids.
- **Builder models** = the two cheapest, `claude-haiku-4-5` and `gpt-5.4-nano`,
  one tool each.
- **No RPS gate; no wholesale rewrites** (§2.1, §3).

Still open:
- Adding the **behavioral view** and an `α` weight, and a density clusterer that
  keeps outliers (`m`): the richer selector deferred in §1; priced by `N*`.
- `N` (clusters kept / sample budget), `max_combo`, and the Stage-3 candidate
  budget.
- The **structural guard** that hard-rejects whole-`FunctionDef`/module rewrites
  (prompt-level today).
- Whether self-learning rules are kept per-term or reset (report both).
- Gate check (from PLAN): if clustered-`N` does not beat random-`N` at matched
  `N` on Refactory, revisit before spending the Codeforces build budget.
