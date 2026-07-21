# Paper plan (AAAI-26 target)

**Title:** Synthesize Once, Repair Many: Amortizing LLM Costs in Automated Repair of Programming Assignments

**Working name of technique:** CoEP (Cost-Effective Program repair). Paradigm name: *per-assignment repairer synthesis* / amortized APR.

**Headline numbers (abstract):** hybrid repairs 100% of 179 held-out buggy submissions — identical to a frontier-LLM per-submission baseline — while resolving 74.9% locally at zero marginal LLM cost; break-even after ~56 submissions per assignment; asymptotic ~4.0x cost reduction (2.0x vs. prompt-cached baseline); patches 2.3x smaller (RPS 0.058 vs 0.133).

**Budget (7 pages, AAAI two-col): ~4 figures + 4 tables**
- Fig 1: architecture / lifecycle (build phase vs deploy phase) [TikZ or matplotlib schematic]
- Fig 2: cumulative cost vs #submissions (the money plot; includes cached baseline + build-cost line)
- Fig 3: per-problem repair rates (baseline vs generic-only vs CoEP-local)
- Fig 4: RPS distributions (box)
- Tab 1: cost anatomy of the per-submission prompt (tokens; 79% shared prefix)
- Tab 2: main results (repair rate, quality rate, RPS, $/submission, marginal cost) with CIs
- Tab 3: per-problem detail (rounds, build/eval rates, ablation column)
- Tab 4: cost model / token accounting (build tokens, per-inst tokens, break-even)

## Section plan
1. **Introduction** (~1p). Instructor feedback burden -> LLM APR works (PyDex 96.5% few-shot; ChatRepair $0.42/bug) -> BUT deployed per-submission: every query re-sends assignment ctx; classroom scale math; MOOC scale. Insight: programming-assignment APR is a *many instances, one specification* regime; the right unit of LLM investment is the assignment, not the submission. Contributions.
2. **Motivation: The Cost Anatomy of Per-Submission Repair** (~0.5p). Prompt decomposition, 79% invariant tokens; caching helps 49% but floors at per-submission inference; Tab 1.
3. **Approach: CoEP** (~1.75p). Formulation; builder inputs (spec, tests, refs, k=5 historical buggy); repair-operator library (mutation-inversion space, test-driven validation, RPS cap <= 0.35 w/ justification from Refactory/PyDex patch-size metric); generate–validate–refine loop (<=3 rounds, Self-Refine/Reflexion grounding); repairer contract; independent re-validation (no self-reporting); hybrid escalation. Algorithm 1.
4. **Experimental Setup** (~1p). RQ1 effectiveness+quality; RQ2 cost; RQ3 what makes it work (ablation: generic-only, refinement rounds). Benchmark: why new (contamination of public ITSP/Refactory sets; Xia et al. ICSE'23 memorization threat), construction = misconception-crafted (taxonomy from lit) + mutation-based (Just et al. FSE'14 validity; IntroClass/Codeflaws precedent), independent validation harness; splits. Baselines: per-submission LLM prompting = the deployment mode of PyDex/MMAPR/ChatRepair, same model both arms to isolate paradigm; + prompt-cached variant (Anthropic pricing). Metrics: repair rate (Refactory/PyDex), RPS token edit distance (PyDex/Refactory), $ + tokens per fix (ChatRepair). Model: single frontier model (Claude), tokenizer & pricing disclosed; LLM-as-harness protocol.
5. **Results** (~2p). RQ1: Tab 2 + Fig 3 + Fig 4; boxed answers. RQ2: Tab 4 + Fig 2, break-even formula N* = C_build/(c_inst*(1-f)); Pareto statement. RQ3: ablation Tab 3 (generic-only 51.4%? pending; rounds analysis: 7/10 problems 5/5 at round 1; feedback with failing sources needed for the rest).
6. **Discussion & Limitations** (~0.4p). internal/external/construct threats folded here + contamination note + synthetic-benchmark caveat + single-model caveat.
7. **Related Work** (~0.5p). APR for assignments (CLARA/Refactory/Verifix/Sarfgen/ITSP); LLM APR (AlphaRepair/ChatRepair/RING/PyDex/FastFixer/CREF); cost-efficient LLM inference (FrugalGPT, caching, SRepair); LLM tool synthesis (Voyager, LLMs-as-tool-makers, Self-Refine).
8. **Conclusion** (~0.15p) + Ethical statement (unnumbered; student data, feedback fairness) + Reproducibility checklist.

## Writing process
- Draft each section -> self-review pass (clarity, claims<->evidence mapping, AAAI criteria) -> revise -> next section.
- After full draft: 2 independent reviewer agents (AAAI review form) -> triage: accept fixes that strengthen; counter weak objections with added evidence/argument, NOT claim-narrowing.
