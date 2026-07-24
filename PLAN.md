# CoEP v2 — Rebuild Plan

Confirmed decisions: **SFT deferred**; **no train/test split** (see "Evaluation
set" below).

- **Dataset**: Refactory + Codeforces.
- **Baselines**: `Refactory`, `PyDex`, `PyDex + prompt caching`, `CoEP`.

## Status (updated 2026-07-24)

**The CoEP pipeline runs end to end.** Stages 1–4 (selection, synthesis, local
rule-combination repair, fallback + self-learning) are implemented, plus the
`run.py build|repair|evaluate` drivers and a hardened runner. Smoke test on
`refactory_q1`: the `claude-haiku` builder reaches 83% sample coverage for
$0.041 (cost.json written); `gpt-5.4-nano` builds for $0.004 but its rules do
not repair the samples (0%) — a real capability floor for the cheapest model.
Known tuning gap: the 6-sample tool overfits (83% sample → ~9% held-out) with
large patches (RPS ~0.5); the structural no-rewrite guard and a larger sample
budget are the levers (still open, below), not a completeness gap.

What is implemented:

- **Dataset: Refactory + Codeforces, 11 problems** (Refactory 5 + Codeforces 6,
  one per rating band), **2,970 buggy**. The Codeforces subset is verifiable ∩
  Python3 ∩ WA≥1 & AC≥1 ∩ `official_tests_complete` ∩ no special-checker,
  verified by executing every submission against the full official suites
  (0.16% oracle false-positive).
- **Two builder models, the two cheapest**: `claude-haiku-4-5` and
  `gpt-5.4-nano`. CoEP builds one tool per model:
  `tools/<p_id>/{claude,gpt}/fixer.py`, each with a `cost.json` recording build
  tokens/USD.
- **Stage-1 selection is implemented** (`src/core/synthesis.select_samples`):
  structural clustering + per-cluster **min-edit-to-nearest-correct** sample
  (not medoid), references = structural medoids. See METHODOLOGY §1.
- **Stage-2 synthesis is implemented** (`src/core/synthesis.build`):
  generate–validate–refine, harness re-validation, `class Fixer.rules() ->
  list[Rule]` contract, **wholesale rewrites forbidden**.
- **Fallback** uses `LLM(d, T, b, r)` with a strategy-matched reference
  (`src/core/fallback`, `src/core/cluster.nearest_reference`).
- Cost is tracked via official SDKs; `src/utils/llm` handles the newer-model API
  contract (no `temperature`; GPT-5 `max_completion_tokens`; stream on large
  `max_tokens`; text past extended-thinking blocks).

**Evaluation set.** No held-out split. Prior work in this setting (CLARA,
Refactory) assumes the whole submission pool exists at feedback time — Refactory
consumes *all* correct solutions before repairing — so building a tool from
buggy programs drawn from that same pool is temporally sound, and our resource
ask (N representatives) is strictly smaller than Refactory's (thousands of
correct solutions). What this argument does *not* cover is builder memorization:
v1 builders demonstrably hard-coded corrected sources for build-set programs
(four repairers contain verbatim fixes keyed by normalized source). We therefore
evaluate on **every** buggy program and additionally report the figure with the
N build programs excluded. Same run, two aggregations, zero extra cost; the gap
matters where N/|eval| is large.

---

## 0. Reconnaissance results (verified, not assumed)

| Item | Finding |
|---|---|
| RPS formula | Take it from the **reference implementation** in `dwchoi95/refactory` (authoritative over prose); cross-validated node-for-node against our `src/utils/metrics.rps`. |
| Execution model | Two modes needed: **function-entry** (Refactory) and **stdin/stdout judge** (Codeforces). `src/runner/testing.py` supports both, per-test SIGALRM. |
| Hardware | Apple M1 Ultra, 64 GB, **no CUDA**; torch/mlx not installed. (Why SFT is deferred.) |

### Scientific risk to state up front
Codeforces problems are competitive-programming tasks, not CS1. Rule-based local
repair will likely cover a **smaller fraction** on the harder rating bands than
on Refactory. That is a real possibility, not a setback to hide: the paper's
claim becomes *where* per-problem amortization pays off and where it does not,
with the self-learning loop and fallback carrying the tail. We measure it and
report it either way.

---

## Phase 1 — Repository restructure

```
src/                       # all CoEP methodology
  prompts/                 # every prompt as a .md file (builder, refine, fallback)
  experiments/             # experiment drivers (former scripts/*)
  utils/
    llm.py                 # all LLM API calls live here
    metrics.py             # RR, RPS, ATT, InT, OuT, Cost
  runner/
    testing.py             # shared test runner (function-entry AND stdin/stdout)
  core/
    cluster.py             # build-set / reference selection   <- new contribution
    synthesis.py           # generate-validate-refine loop
    repair.py              # rule-combination search driver + RULE PROVENANCE
    fallback.py            # LLM fallback + self-learning rule induction
run.py                     # entrypoint: build | repair | evaluate (dispatch only)
tools/<p_id>/<model>/      # one tool per builder model (claude / gpt)
  fixer.py                 # synthesized rules; class Fixer.rules() -> list[Rule]
  cost.json                # build tokens / USD / rounds / sample coverage
data/<p_id>/               # unified schema (problem.json, buggy/, correct/)
baselines/
  refactory/  pydex/       (sft/ later)
results/v1/                # archive of the current (v1) experiments
```

- Migrate `coep/*` → `src/core|runner|utils`; **`scripts/*` move into
  `src/experiments/*`** and `run.py` only dispatches to them (no logic in `run.py`).
- Prompts stop being Python string literals: each becomes a `.md` file under
  `src/prompts/` and is rendered with explicit parameters.
- `src/runner/testing.py` is importable by `tools/<p_id>/<model>/fixer.py`.

### `tools/<p_id>/<model>/fixer.py` contract
- One file per (problem, model), a standalone artifact exposing `class Fixer`
  whose `rules()` returns `list[Rule]` (candidate generators consumed by
  `src/core/repair.py`). The one required import is ensured on disk.
- **Rule provenance is mandatory**: every applied rule records its identifier, so
  each repair carries the list of rules that produced it. `src/core/repair.py`
  logs this alongside the outcome (v1 discarded it: results only held
  `bug/repaired/status/rps/seconds`, which is why per-rule statistics were
  impossible).
- **Design constraint learned from v1**: locate edits on the AST, but *apply*
  them as byte-range splices on the original source. Rendering patches through
  `ast.unparse` reformats untouched lines and inflates patch size; in v1 this was
  the single largest builder failure mode (one builder went 0/5 → 5/5 only after
  switching to surgical line edits). `NodeTransformer` is the locator, not the
  printer.

## Phase 2 — Datasets

Import scripts live in `data/_import/` (one-off data preparation, deliberately
outside `src/`, which holds methodology only). Unified schema per problem:
`data/<p_id>/{problem.json, buggy/, correct/}`.

1. **Refactory import** → `mode: call`, re-using the v1 importer's test-suite
   parsing. 5 problems.
2. **Codeforces import** (open-r1/codeforces) → `mode: stdio` (or `file` where
   the reference uses `input.txt`/`output.txt`), official tests only. One
   representative per rating band by most WA submissions → 6 problems. Every AC
   submission is executed against the full official suite to bound the oracle
   false-positive rate.
3. **Split**: none. Build = N clustered representatives (Phase 3.2), eval = every
   buggy program (no cap), also reported with the N build programs excluded.

## Phase 3 — Methodology

### 3.1 Drop the RPS gate
Termination = *all tests pass*. RPS becomes a **reported quality metric**, not
an acceptance filter. LLM fallback fires **only on failure**. (This also
retires the τ-provenance objection raised in earlier reviews.)

### 3.2 Cluster-driven build-set and reference selection ← core new contribution
Only build-time-available information is used: buggy programs (unlabeled), the
test suite, and correct programs.

**Implemented** (`src/core/synthesis.select_samples`, `src/core/cluster`):
- **Structural view** `φ_str(b)`: TF-IDF over normalized-AST path n-grams
  (identifiers/literals folded, as in the RPS labeler). Cluster with
  average-linkage agglomerative clustering under a cosine-distance threshold
  (count derived from the data, no `k`).
- **Representative = min-edit member, not medoid**: for each of the largest
  clusters, take the member with the smallest tree-edit distance (RPS) to its
  nearest correct program — a clean, learnable single-misconception exemplar.
  (Medoid samples left both cheap builders at 0% sample coverage; min-edit
  samples are learnable.)
- **References**: cluster *correct* programs on the structural view (they are
  behaviorally identical), take **medoids** → strategy-diverse, typical
  references. The same featurizer drives the fallback's reference pick.

**Deferred (open knob)**: the richer selector — add the behavioral view
`φ_beh(b)` (failing-test outcome signature, one run per program), an `α` weight
`[α·φ̂_beh ; (1−α)·φ̂_str]`, and a density clusterer (HDBSCAN) that labels and
**keeps outliers** (top-`m` rare misconceptions) as extra representatives.

**Ablation that proves the contribution**: random-`N` vs clustered-`N` at
*matched* `N`, measured by held-out RR. Secondary: cluster count as a
predictor of assignment difficulty (a routing signal).

### 3.3 Rule-combination repair loop
Rules are composable; search applies combinations, validating after each
candidate, until all tests pass or the combination space is exhausted.
- Combinatorial bound: order rules by match against the program's failure
  signature; beam/priority search with a budget rather than blind `2^|rules|`.

### 3.4 Self-learning fallback
When the LLM fallback repairs a program the local tool failed on, diff
(buggy, fixed) → generalize into a new rule → append to
`tools/<p_id>/<model>/fixer.py`. Measure RR as a function of accumulated
fallbacks (does the tool improve across a term?).

## Phase 4 — Baselines
- **Refactory**: re-clone, re-run excluding the N build programs.
- **PyDex**: run the per-submission LLM repair pipeline driven by **our own
  model**, so model choice is not a confound and ATT/InT/OuT/Cost are measurable.
- **PyDex + prompt caching**: same runs re-priced with cache read/write.
- **CoEP**: this work.

## Phase 5 — Metrics (replacing v1)
| Metric | Definition |
|---|---|
| **RR (%)** | fraction of eval programs repaired (all tests pass). Replaces "test-pass rate"; **quality repair rate is retired**. |
| **RPS** | per the Refactory reference implementation. Reported, not gated. |
| **ATT** | average time to repair one buggy program, **end to end** (local search + any LLM API latency), seconds. |
| **InT / OuT** | mean prompt input / output tokens per repaired program. |
| **Cost** | USD per repaired program (and per problem, with build cost). |

## Phase 6 — Experiments
Build tools for the 11 problems (Refactory 5 + Codeforces 6), one per builder
model → evaluate every arm on every buggy program (RR/RPS/ATT/InT/OuT/Cost) →
cluster-selection ablation (random-`N` vs min-edit clustered-`N`) →
self-learning curve → cost/break-even.

## Phase 7 — Paper
Rewrite Setup/Results/Method around v2; keep the intro's three-generation
framing and the scale/cost argument; fresh reviewer rounds.

---

## Order of work and gating

1. **Phase 1 + `src/runner/testing.py` dual-mode support** — everything blocks on this. *(done)*
2. **Phase 2 Refactory + Codeforces import** → smoke-test end to end. *(done)*
3. **Phase 3.2 selection + 3.3 synthesis** → validate on Refactory (where v1
   numbers give a reference point) *before* scaling to all problems.
4. Then Phase 3.4, Phase 4, Phase 6.

Checkpoint after step 3: if clustered selection does not beat random at matched
N on Refactory, revisit the design before spending the full build budget.
