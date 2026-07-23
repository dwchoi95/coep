# CoEP v2 — Rebuild Plan

Confirmed decisions (2026-07-23): **SFT deferred**; **LSGen 20/problem + CodeNet
harvest**; **LSGen reproduced directly with our own model**.

Baselines for v2: `Refactory`, `LSGen`, `LSGen + prompt caching`, `CoEP`.
(`SFT (Qwen2.5-Coder-7B)` is a later phase.)

---

## 0. Reconnaissance results (verified, not assumed)

| Item | Finding |
|---|---|
| LSGen data | `PandaAB/LSGen` ships **only `test.json`**: 110 problems, **1,668 (WA→Accepted) pairs**, Python, CodeNet (AIZU/AtCoder). Capped at **20 buggy per problem** (59 problems have exactly 20; 83 have ≥10). Mean 19.8 lines. |
| LSGen tests | `dataset/repairDataset/merged_test_cases/<pid>/input.N.txt` + outputs — 60–200+ cases per problem. Descriptions in `English_Program_Question_StringVersion.json` (10 MB). |
| **Execution model** | **99% of LSGen programs read stdin and print stdout** (1,653/1,668). Our harness is function-entry only. **This is the single largest engineering item.** |
| RPS formula | Not extractable from the ASE'19 PDF (text layer corrupted). Take it from the **reference implementation** in `dwchoi95/refactory` (authoritative over prose). |
| Hardware | Apple M1 Ultra, 64 GB, **no CUDA**; torch/mlx not installed. (Why SFT is deferred.) |
| Lost asset | `/workspace/refactory` gone with the old container → re-clone `dwchoi95/refactory`. |

### Scientific risk to state up front
LSGen problems are competitive-programming tasks, not CS1. Rule-based local
repair will very likely cover a **much smaller fraction** than the 47–51% we
measured on Refactory. That is a real possibility, not a setback to hide: the
paper's claim becomes *where* per-problem amortization pays off and where it
does not, with the self-learning loop and fallback carrying the tail. We
measure it and report it either way.

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
tools/<p_id>/
  fixer.py                 # synthesized rules + tool entrypoint; class Fixer(ast.NodeTransformer);
                           # imports src.runner.testing for validation
data/<p_id>/               # unified schema (problem.json, buggy/, refs/)
baselines/
  refactory/  lsgen/       (sft/ later)
results/v1/                # archive of the current (v1) experiments
```

- Migrate `coep/*` → `src/core|runner|utils`; **`scripts/*` move into
  `src/experiments/*`** and `run.py` only dispatches to them (no logic in `run.py`).
- Prompts stop being Python string literals: each becomes a `.md` file under
  `src/prompts/` and is rendered with explicit parameters.
- `src/runner/testing.py` is importable by `tools/<p_id>/fixer.py` (requirement 4).

### `tools/<p_id>/fixer.py` contract
- One file per problem, exposing `class Fixer(ast.NodeTransformer)`.
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

1. **LSGen import** → `data/<pid>/{problem.json, buggy/, refs/}` (LSGen source)
   - `problem.json`: description, **I/O-based tests** (stdin → expected stdout), time limit.
   - `refs/`: the paired `code2` (same student's accepted submission) of *build-set* programs only, never of eval programs.
2. **CodeNet harvest** for the same 110 problems (volume for the cost analysis):
   pull additional rejected submissions per problem from the public CodeNet
   release; target ≥200/problem where available.
3. **Refactory import**: re-clone `dwchoi95/refactory`, reuse the existing
   importer → `data/<pid>/` (Refactory source).
4. **Split rule (per requirement)**: build = N clustered representatives;
   **eval = every remaining buggy program** (no 40-cap).

## Phase 3 — Methodology

### 3.1 Drop the RPS gate
Termination = *all tests pass*. RPS becomes a **reported quality metric**, not
an acceptance filter. LLM fallback fires **only on failure**. (This also
retires the τ-provenance objection raised in earlier reviews.)

### 3.2 Cluster-driven build-set and reference selection ← core new contribution
Only build-time-available information is used: buggy programs (unlabeled), the
test suite, and correct programs.

Two views per buggy program `b`:
- **Behavioral** `φ_beh(b)`: failing-test bit-vector over the suite + outcome
  class per test (wrong-output / exception type / timeout). One test run per
  program — already needed. Captures *what symptom the bug produces*.
- **Structural** `φ_str(b)`: TF-IDF over normalized-AST paths/n-grams (+ CFG
  shape descriptor). Captures *what shape the program is*.

Combine as `[α·φ̂_beh ; (1−α)·φ̂_str]` (L2-normalized per view).

- **Cluster count is decided dynamically** with HDBSCAN (density-based, no `k`,
  and it labels outliers). **Outliers are kept, not discarded**: a rare
  misconception is exactly what a rule set would otherwise miss — include the
  top-`m` outliers as extra representatives.
- **Representative = cluster medoid** (most typical instance of that class).
- `N` is therefore *derived from the data*, not fixed at 5.
- **References**: cluster *correct* programs on the structural view alone (they
  are behaviorally identical), take medoids → strategy-diverse references.

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
(buggy, fixed) → generalize into a new rule → append to `tools/<p_id>/fixer.py`.
Measure RR as a function of accumulated fallbacks (does the tool improve
across a term?).

## Phase 4 — Baselines
- **Refactory**: re-clone, re-run excluding the N build programs (requirement 3-1).
- **LSGen**: reproduce the pipeline (UniXcoder embeddings → vector retrieval →
  solution-guided repair → iterative enhancement) driven by **our own model**,
  so model choice is not a confound and ATT/InT/OuT/Cost are measurable.
- **LSGen + prompt caching**: same runs re-priced with cache read/write.
- **CoEP**: this work.

## Phase 5 — Metrics (replacing v1)
| Metric | Definition |
|---|---|
| **RR (%)** | fraction of eval programs repaired (all tests pass). Replaces "test-pass rate"; **quality repair rate is retired**. |
| **RPS** | per the Refactory reference implementation (read from source, then documented in the paper). Reported, not gated. |
| **ATT** | average time to repair one buggy program, **end to end** (local search + any LLM API latency), seconds. |
| **InT / OuT** | mean prompt input / output tokens per repaired program. |
| **Cost** | USD per repaired program (and per problem, with build cost). |

## Phase 6 — Experiments
Build tools for 110 (LSGen) + 5 (Refactory) problems → evaluate all four arms
on every held-out buggy program → cluster-selection ablation → self-learning
curve → cost/break-even with CodeNet volumes.

## Phase 7 — Paper
Rewrite Setup/Results/Method around v2; keep the intro's three-generation
framing and the scale/cost argument; fresh reviewer rounds.

---

## Order of work and gating

1. **Phase 1 + `src/runner/testing.py` stdin/stdout support** — everything blocks on this.
2. **Phase 2.1 LSGen import** → smoke-test 3 problems end to end.
3. **Phase 3.2 clustering** → validate on Refactory (where v1 numbers give a
   reference point) *before* scaling to 110 problems.
4. Then Phase 3.3/3.4, Phase 4, Phase 6.

Checkpoint after step 3: if clustered selection does not beat random at matched
N on Refactory, revisit the design before spending the 110-problem build budget.
