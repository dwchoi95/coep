# Review — "Synthesize Once, Repair Many: Amortizing LLM Costs in Automated Repair of Programming Assignments" (CoEP)

**Reviewer role:** AAAI, SE+LLM area. I read the full draft (`paper/main.tex`), re-derived every headline number from `runs/summary.json`, and additionally verified the fine-grained claims against the raw per-instance artifacts (`runs/baseline/results.json`, `runs/coep/results/*.json`, `runs/coep/build_eval/*.json`) and the released code (`coep/`, `scripts/`, `benchmark/`).

---

## Summary of the paper

The paper argues that LLM-based repair of programming assignments is deployed in a wasteful "one query per submission" paradigm: ~79% of prompt tokens are assignment-constant, and provider caching recovers only ~49% of cost. It proposes changing the unit of LLM investment from the submission to the assignment: an LLM "builder" synthesizes, once per assignment, a deterministic Python repairer (problem-specific AST rewrite rules over a generic edit-search library, with mandatory test-suite validation and a relative-patch-size cap τ=0.35), refined for ≤3 feedback rounds on 5 sample bugs, then deployed locally at zero marginal LLM cost with per-submission LLM repair as fallback. On a new synthetic benchmark (10 CS1 Python assignments, 229 buggy programs, 179 held-out), the local repairers fix 74.9%, the hybrid matches the 100% baseline repair rate and quality, build cost is $0.126/assignment, break-even ≈56 submissions, asymptotic marginal-cost reduction 4.0×.

---

## Scores (AAAI form)

### 1. Significance & novelty — 6/10
The framing — "many instances, one specification ⇒ amortize LLM reasoning into a verifiable symbolic artifact" — is crisp, well-argued, and to my knowledge not previously instantiated for assignment repair. It is a genuinely useful reframing that connects classical per-assignment APR (CLARA, Refactory) with LLM repair, and the paper positions it honestly against Voyager/LATM-style tool synthesis and template APR (TBar/PAR).

Two things temper significance:
- **The absolute economics are tiny.** By the paper's own numbers, a 300-submission assignment saves ≈$0.55 per offering (300×$2.99e-3 vs $0.126 + 300×$0.75e-3). A 40-section department saves a few hundred dollars a semester. The operational arguments (no rate limits, offline, deterministic, auditable) are arguably the real payoff, but they are asserted in one paragraph rather than measured (no baseline latency numbers, no throughput/rate-limit experiment).
- **Novelty is at the paradigm/deployment level, not the technique level.** Each component (generate–validate–refine, mutation-inversion search, test-driven patch validation) is standard; the contribution is their composition plus a cost model.

### 2. Soundness of claims — 7/10
This is the strongest aspect of the paper *within its stated scope*. I verified essentially every number:

- Abstract/intro: 79% shared prefix = 583/740 ✓; 49% cache saving = (2.992−1.53)/2.992 ✓; 74.9% = 134/179 ✓; $0.126 = 1.2586/10 ✓; break-even 56 = 0.1259/(0.002992×0.7486) ✓; 4.0× = 1/0.2514 ✓; 21%→50% crafted = 17/80 → 40/80 ✓; 95% mutants = 94/99 ✓; p=2.4e-7 with discordant 23:0 ✓.
- Table 1: all cells match summary.json, including Wilson CIs ([68.0, 80.6] etc.) ✓. Table 2: all token/USD figures reproduce exactly from token counts × ($3/$15 per Mtok, cache 0.1×/1.25×) — I recomputed baseline $0.535644, cached $0.273821, build $1.258584, fallback $0.135969 to the cent ✓. 15 build calls = Σ builder_rounds ✓.
- The subtle RQ1 claims that summary.json does *not* contain also check out against raw per-instance data: on the 134 locally-repaired instances, paired baseline mean RPS is 0.0584 vs CoEP 0.0578 (paper: "0.058 for both"); all 13 over-cap baseline "repairs" fall on instances CoEP escalates (13/13, so "entirely" is literally true); build-sample success 38/50 → 48/50, is_palindrome 0/5→5/5 at round 2, flatten 3/5→4/5 and unique_in_order 0/5→4/5 by round 3 — all confirmed ✓.

I found no number that does not map to data. That is rare and commendable. The score is not higher because of **construct-level soundness problems**:

- **(Major) The mutant half of the benchmark is solvable by the generic search *by shared implementation*, not merely "by construction."** `coep/repairlib.py` imports `_sites` and `mutate` from `coep/mutation.py` — the *identical module* `scripts/make_dataset.py` uses to generate the mutant bugs. The 94/99 generic result on mutants is close to tautological, and mutants are 55% of the eval set. The paper discloses the in-space property (RQ3, benchmark section) and even uses it as an instrument, but the abstract's headline "74.9% locally" is substantially an artifact of benchmark composition. On the bug class where assignment understanding is actually needed (crafted), the local rate is 50% — which would put the fallback fraction at ~0.5, the asymptotic reduction at ~2× (not 4×), and break-even at ~84 (not 56). None of the headline claims survive unchanged under a crafted-dominated mix, and real distributions are unknown.
- **(Moderate) "All cost ratios are tokenizer-independent" is overclaimed.** The chars/3.6 approximation is applied to both arms, but the arms have opposite in/out mixes (baseline: 740 in / 51 out; build: 4,749 in / 7,441 out per assignment) and output is priced 5× input. A tokenizer bias that differs between prose-heavy prompts and code-heavy responses shifts C relative to c and moves the break-even point. Ratios are price-weighted sums, not pure ratios of token counts.
- **(Minor) A few phrasings outrun the data.** "Exactly as minimal" is 0.0584 vs 0.0578; Table 1's hybrid $0.75e-3 is the formula f·c, while the measured value is $0.7596e-3 (0.135969/45×... = 0.135969/179) — trivial, but sits oddly next to "exact accounting." "~2s on a CPU": mean over successful repairs is 1.67s, over all local attempts 2.13s; gcd averages 9.75s and one instance hit the 60s timeout.

### 3. Relevance to AAAI — 8/10
Squarely relevant: LLM agents synthesizing verifiable programs, AI for education, cost-aware deployment. The paper cites two AAAI-25 papers in the same problem setting (Orvalho et al.; AdaPR) and differentiates from both. No concerns.

### 4. Clarity — 8/10
Very well written. The cost-anatomy section is an effective motivation device; RQ answer boxes, the crafted/mutant instrument, and the break-even algebra are all clean. Deductions: the benchmark section under-emphasizes that mutants dominate the eval set (55%) while the abstract leads with the pooled 74.9%; the uneven per-assignment n (10–20, flatten has 10) is never surfaced; several load-bearing numbers are hardcoded rather than macro-generated (7.3%, 13/179, 134, 94/99, 21%, 50%, "42 baseline repairs", "⊥ (25%)" in Fig. 1) — currently consistent, but fragile.

### 5. Reproducibility — 7/10
Strong on artifacts: benchmark generation is seeded and scripted (`scripts/make_dataset.py`, SEED=7), prompts/responses/raw results are all in `runs/`, metrics recompute exactly, and the checklist is filled honestly (including admitting no cross-run variance). Weaknesses: the model is identified only as "Claude, July 2026 snapshot" priced "at a representative tier" — no exact model ID, no decoding parameters (temperature?), and the "agent harness constrained to behave as a stateless single-shot endpoint" is unusual and underdescribed (how was tool use / test access provably disabled?). Every LLM-dependent result is a single run: builder synthesis is stochastic and n=10; no seed-variance for the arm that carries the paper.

### 6. Overall recommendation — **6/10 (marginally above threshold; weak accept)**
**Justification.** The paper does one clear thing and does it with unusual empirical hygiene — every claim I checked, down to paired-subset means, maps to released data, and the limitations section preempts several of my objections. The paradigm framing is novel and the RQ3 crafted/mutant decomposition is honest about where the power comes from. What keeps it at 6: the evaluation universe is entirely synthetic and small; the headline numbers (74.9%, 4×, break-even 56) depend on a bug mix that is 55% mutants generated by the same code the repairer inverts; the missing cheap-model-cascade baseline means the paper never establishes that *repairer synthesis* is the right amortization rather than merely *an* amortization; and the absolute dollar stakes are small enough that the significance case leans on unmeasured operational benefits. A strong rebuttal on weaknesses 1–2 below could move me to 7.

---

## (a) Three weaknesses most likely to cause rejection

**W1 — Synthetic benchmark with a partially circular mutant pool (severity: high; most likely rejection trigger).**
No real student submissions are evaluated — the authors wrote (or generated; the paper does not say which, see Q1) the misconception bugs against their own taxonomy, and the mutation bugs are produced by `coep/mutation.py`, whose operator set the deployed repairer's `candidates_generic` searches over via the *same functions* (`_sites`, `mutate`). So for 99/179 eval instances, the repair method contains the bug generator's inverse by construction. The paper's own instrument shows what happens outside that space: 50% local repair on crafted bugs. The abstract, Table 1, and the cost model all quote the pooled numbers. A reviewer who notices this (and one will) can reasonably argue the headline results measure the benchmark, not the method. Mitigation exists in-text (RQ3, external-validity paragraph) but the headline framing does not reflect it, and no result on even a small sample of real student code is provided.

**W2 — Missing cost-competitor baselines; the contribution is 100% economic, but only one economic alternative (caching) is tested (severity: high).**
Because the frontier baseline saturates at 100% repair rate, the entire contribution is cost/operational. Yet the obvious competing amortization — a FrugalGPT-style cascade with a cheap model (e.g., a Haiku-tier model at roughly 1/10 the price) as the first tier and the frontier model as fallback — is cited but not run. At ~$0.3e-3 per submission it would plausibly beat CoEP's asymptotic $0.75e-3 with zero build cost, no synthesis machinery, and likely near-frontier repair rates on CS1 code. Similarly, the retrieval/patch-cache alternative is dismissed in a paragraph ("Why synthesis beats retrieval") with no experiment, despite the paper's own observation that real distributions are duplicate-heavy — which favors retrieval too. Without at least the cheap-cascade baseline, "spend the LLM once per assignment" is not shown to dominate "spend a cheaper LLM per submission."

**W3 — Single model, single run, small n; generalization of the builder is asserted from 10 build episodes (severity: medium-high).**
All results come from one frontier model, one seed, n=1 sampling, 10 assignments, 179 eval instances (per-assignment n as low as 10). The reliability claim for the refinement loop ("7/10 usable → 10/10") is based on exactly ten builder runs with no repetition; builder synthesis is the stochastic heart of the method, and its cross-seed variance — and behavior with a weaker/cheaper builder model, which is exactly what a cost-sensitive adopter would use — is unmeasured. The break-even and 4× claims are also point estimates with no sensitivity analysis over f, τ, or bug mix (the crafted-only regime, computable from the paper's own numbers, gives ≈2× and N*≈84 and is never stated).

## (b) Minor issues

1. "Exactly as minimal as the baseline's on the same instances (mean RPS 0.058 for both)" — measured 0.0584 vs 0.0578. Say "statistically indistinguishable" and report both, ideally with a paired test.
2. Table 1 hybrid $/sub is the formula value f·c = 0.75e-3; the measured fallback spend gives 0.76e-3 (0.135969/179). Use the measured value or say the number is derived.
3. "All cost ratios are tokenizer-independent" — false in general; see soundness. Weaken to "unaffected by uniform calibration error" and note the in/out-mix caveat, or re-tokenize with a released tokenizer.
4. "~2s" latency: specify whether the mean is over attempts (2.13s) or successes (1.67s); report the max (43.9s) and the one timeout; gcd's 9.75s mean deserves a mention. No measured baseline latency is given, though latency is claimed as a benefit.
5. Baseline prompts render Python booleans as lowercase `true`/`false` in the test-suite listing (see `runs/baseline/prompts/*`) — cosmetic prompt bug; didn't hurt the 100% baseline, but should be fixed or noted.
6. Table 1 (anatomy) groups "task preamble + instructions" into the 79% shared block, but the minimal-patch "Rules" section appears *after* the submission in the actual prompt, so it is byte-identical yet not part of the cacheable prefix. The cache accounting in the code handles this correctly (550-token prefix); the table conflates "identical" with "cacheable."
7. τ = 0.35 is never justified or sensitivity-tested; the baseline's 7.3% "over-cap" figure is a direct function of this choice.
8. RPS can exceed 1.0 (one baseline repair has RPS 1.06); worth a sentence, since "relative" suggests [0,1].
9. Per-assignment eval sizes vary from 10 (flatten) to 20 and are only recoverable from the artifact; state them, and note Figure 2's per-assignment rates have very wide CIs at n=10–20.
10. Exact model ID, decoding temperature, and the meaning of "agent harness constrained to behave as a stateless single-shot endpoint" must be specified (the checklist says "model version… stated in Experimental Setup," but only "Claude, July 2026 snapshot" appears).
11. Formulation nit: ρ_A : b ↦ p ∪ {⊥} abuses notation (the codomain should be programs ∪ {⊥}, and ↦ maps to an element).
12. "The price of roughly 42 baseline repairs" (RQ2) vs. break-even 56 — both correct (42 ignores fallback traffic) but adjacent enough to confuse; clarify.
13. Fig. 1 hardcodes "⊥ (25%)" and the caption of Table 1 defines an odd `\ex` macro used only once; several result numbers are hardcoded in prose while others are macros — drift hazard.
14. Checklist says the no-variance limitation is "noted in Discussion"; Discussion notes single-attempt matching deployment but never explicitly discusses cross-run variance.
15. Ethical statement says buggy programs are "authored or generated for this study" — say by whom/what (see Q1); if an LLM authored the crafted bugs, that belongs in the benchmark section, not just ethics.
16. "PyDex … up to 96.5%" — double-check this figure and its conditions against the published version (the number and the few-shot qualifier carry weight in the "saturated baseline" argument).

## (c) Questions for the author rebuttal

**Q1.** Who or what authored the 100 misconception-crafted bugs? If an LLM (especially the same model family used in all experiments), how do you rule out a circularity where the evaluated model finds its own bug-generation patterns easy to repair? What external evidence supports the realism of the crafted bugs (mapping to published misconception inventories, or comparison against even a small set of real novice submissions)?

**Q2.** Report a cheap-model cascade baseline: small model per submission (same prompt), frontier fallback on validation failure — repair rate, quality rate, $/submission. If CoEP does not dominate it on cost, what is the argument for repairer synthesis beyond determinism/offline operation?

**Q3.** The generic search inverts the same operator implementation that generated the mutants (shared `coep/mutation.py` code). Recompute the headline economics for a crafted-only distribution: by my arithmetic f≈0.5, asymptotic reduction ≈2×, N*≈84. Do you commit to reporting this regime alongside the pooled numbers?

**Q4.** Builder variance: run the builder ≥3 seeds per assignment (30 runs, ~$4 by your own cost model). How stable are one-shot success (7/10), final success (10/10), local repair rate, and build cost? What happens with a mid-tier builder model?

**Q5.** Overfitting to visible tests: crafted-bug repairs are validated only against the 14 visible tests. Do you have held-out (hidden) tests, and what fraction of local and baseline repairs pass them?

**Q6.** Can you provide any evidence — even a private pilot or instructor-annotated sample — of the fallback fraction f on real course submissions (I/O handling, partial attempts, timeouts), which your own external-validity paragraph identifies as the quantity everything depends on?

**Q7.** Specify the exact model ID and decoding parameters, and explain how the "agent harness as stateless endpoint" provably prevented tool use, retries, or test access during generation.

---

**Recommendation: 6 — Weak accept.** Rigorous, honest, and clearly written instantiation of a genuinely nice idea, evaluated in a universe partly of its own construction. Survives if the rebuttal delivers Q2 and a credible answer to Q1/Q3; rejects if the crafted-bug provenance is circular or the cheap-cascade baseline wins.
