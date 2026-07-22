# Comparison vs. AAAI-26 APR Papers and Award-Winning Papers (verified 2026-07-22)

## 1. AAAI-26 accepted APR papers (dblp, AAAI vol. 40)

Full-paper APR hits in AAAI-26 proceedings (dblp title search "repair"):

| Paper | What it is | Relation to ours |
|---|---|---|
| **Learner-Tailored Program Repair: A Solution Generator with Iterative Edit-Driven Retrieval Enhancement** (Dai, Zhao, Wang, Tang, Wu, Yao, Gao, Chen; pp. 30467-30475) = **LSGEN** | Introduces the LPR task (repair + bug explanations for learners). Builds a per-assignment *solution retrieval database*, edit-driven retrieval to pick guiding solutions, solution-guided repair, iterative retrieval enhancement from evaluation feedback. | **Closest AAAI-26 work; now cited (`lsgen2026`).** Same group as AdaPR (AAAI-25). Key structural difference: LSGEN amortizes *data* (a retrieval index) but still spends one frontier LLM call per submission — its "iterative retrieval enhancement" adds calls. CoEP amortizes *reasoning* (an executable repairer); marginal LLM cost only on escalation. Our PyDex-style arm (per-submission repair guided by real same-assignment example fixes) is the closest same-corpus proxy for retrieval-guided repair: 85.5% quality at $6.53e-3/sub — worse than the plain prompt on quality and 2.4x its cost, and both are dominated by CoEP hybrids on our corpus. Positioning sentence added to Related Work. |
| Automated Repair of Totally-Ordered HTN Domains via CFGs with LLM Support (Lutalo, Bercher; pp. 36316-36324) | Planning-domain repair, not program repair for assignments. | Different problem; no action. |
| GlitchCleaner (glitch-token repair in LLMs), EvDiff3D (3D reconstruction "repair"), Self-Guided Planning and Repair for Code Generation (student abstract) | Not assignment-APR (or non-archival). | No action. |

Conclusion: **AAAI-26's only full-paper assignment-APR work is LSGEN**, and it stays firmly in the per-submission paradigm — which strengthens our framing that the cost *structure* (not the per-call technique) is the unaddressed axis. The paper now cites AAAI-25 (orvalho2025, adapr2025) **and** AAAI-26 (lsgen2026), i.e., the setting's most recent two years at the venue itself.

## 2. Award papers examined

### AAAI-26 Outstanding Papers (Main Track, announced 2026-01-22; aihub.org)
Five winners incl. **"Model Change for Description Logic Concepts"** (the KR paper),
LLM2CLIP, ReconVLA, a causal-structure-learning paper, and a hypergraph-NN paper.
None is APR/code-generation, so the comparison is about *what award papers do*:

- **Model Change (KR)**: one crisp formal problem (eviction/reception/revision),
  completeness of results over the design space, zero over-claiming. Lesson we
  applied: our composition finding is stated as a tight, falsifiable property
  ("fronting any protocol preserves its quality set while diverting traffic";
  verified discordant 0:0) rather than a vague "synergy" claim, and every
  headline claim now has an explicit scope qualifier.
- Common features across the five: (i) a single load-bearing idea named early;
  (ii) evaluation that *exhausts* the obvious alternative-explanations space;
  (iii) claims calibrated to exactly what tables show. Our round-3 revisions
  (enforcement-parity arm, tau-sweep, full-corpus re-run, claim scoping) were
  precisely this kind of alternative-explanation exhaustion.

### ACL 2025 Best Papers (NLP venue; efficiency-adjacent anchor)
- **Native Sparse Attention** (DeepSeek + PKU): the award-level template for an
  efficiency claim — quality parity demonstrated *first*, then hardware-real
  speedups, no efficiency-for-quality trade hidden. Our analogue: quality
  parity/superiority per fallback protocol (identical 197/200 under
  enforcement parity) before any cost claim, and costs reported as raw token
  counts with released strings. Gap vs. that bar: our costs are modeled
  (chars/3.6) not billed — disclosed in Protocol/Discussion; billed-API
  replication is the camera-ready upgrade.

### Fit to our submission
- vs. AAAI-25/26 accepted APR bar (orvalho2025, adapr2025, lsgen2026): same
  dataset family (Refactory corpus), same-model controls and cost accounting
  exceed what those papers report; scale (5 assignments) is at par with
  orvalho2025's benchmark breadth but smaller than LSGEN's.
- vs. award bar: the single-idea crispness and claim calibration are in
  place after round 3; what separates us from award-level is breadth
  (one course, one language, modeled costs) — documented honestly in
  Discussion as priced extensions.

## 3. Reviewer-freshness protocol (standing rule)

Every review round is executed by **fresh subagent sessions**: a newly spawned
agent has no memory of this conversation, prior rounds, or edits. Each reviewer
is instructed to read ONLY `paper/main.tex` + `paper/numbers.tex`, is
explicitly forbidden from opening any `review_*.md` or other repo files, and is
told to judge the submission fresh. Verified in round 3 (reviewers re-derived
all statistics from the PDF sources alone). Residual limitation, disclosed:
reviewer agents share the underlying model family with the authorship pipeline;
mitigations are adversarial instructions, per-reviewer specialty personas, and
fact-checking against tables rather than taste.
