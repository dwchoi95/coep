# Evaluation metrics used by the starred papers

Notes compiled from web-search-verified abstracts, official paper pages, and tool repositories (2026-07-21).
All bibliographic entries in `references.bib` were verified by search except where flagged below.

## refactory2019 — Refactory (Hu et al., ASE 2019)
Reports **repair rate** (fraction of ~1,800 incorrect Python submissions from 361 students that are patched to pass all tests), **average repair time**, **relative patch size** (patch size relative to the buggy program, used to argue ~30% of its patches are smaller than Clara's), and sensitivity to the **number of available correct reference solutions** (often needs only one).

## clara2018 — CLARA (Gulwani, Radicek, Zuleger, PLDI 2018)
Measures **repair rate** (% of incorrect attempts for which a repair is generated from clustered correct student solutions), **running time/scalability**, and **feedback quality** via manual comparison of generated repairs against instructor/expert feedback. Patch "locality"/minimality is discussed qualitatively rather than as a normalized patch-size metric.

## verifix2022 — Verifix (Ahmed et al., TOSEM 2022)
Primary metric is the **verified repair rate**: the fraction of assignments (up to 58%) for which a *provably correct* (MaxSMT-verified) repair is produced, compared head-to-head against Clara's repair rate; also reports **repair time**. Distinctive in requiring verification against a reference solution rather than only test passing.

## itsp2017 — Feasibility study / ITSP (Yi et al., ESEC/FSE 2017)
Applies four APR tools (GenProg, AE, Angelix, Prophet) to student C programs (IIT Kanpur CS-101) and reports **full repair rate** and introduces **partial repair rate** (patches that pass more tests than the original). Also runs a **user study** relating generated repairs to student learning outcomes, finding raw test-based repair rates too low and patches often unsuitable as direct feedback.

## pydex2024 — PyDex (Zhang et al., OOPSLA 2024)
On 286 real student Python programs, reports **fix rate** (program passes all instructor tests) against three baselines (incl. Refactory and BIFI), **average patch size** measured by token-level edit distance to the student's program (smaller = better pedagogically), and ablation of **iterative querying / number of LLM attempts** and few-shot selection.

## mmapr2022 — MMAPR (Zhang et al., arXiv 2022)
**Not published as-is**: arXiv:2209.14876 is the preprint whose archival version became PyDex (the authors' site serves the PyDex paper under the `mmapr` publication URL) — cite pydex2024 for the archival version. Metrics: **repair rate** on 286 student programs (67.13% baseline vs 86.71% zero-shot vs 96.5% few-shot) and **average token edit distance** of patches vs the Refactory baseline.

## chatrepair2024 — ChatRepair (Xia & Zhang, ISSTA 2024)
Reports **number of correct and plausible fixes** on Defects4J 1.2/2.0 and QuixBugs (162/337 correct on Defects4J), and — key for a cost-effectiveness paper — **monetary API cost per fixed bug** ($0.42/bug computed from ChatGPT token pricing), plus token/request budgets per bug (patch attempts and conversation rounds capped). Note the published ISSTA title differs from the arXiv title (see summary below).

## srepair2024 — SRepair (Xiang et al., arXiv 2024)
**Verified only as an arXiv preprint** (arXiv:2404.12833); no archival venue found by search — flagged as unverified-venue, best-effort @misc entry. Metrics: **correct function-level fixes** on Defects4J (300 single-function bugs, +85% over prior work; first 32 multi-function bugs) and **cost per fixed bug** (~$0.029/bug, per its repo) using open-source LLMs in a dual-LLM (suggestion + patch) pipeline.

## fastfixer2024 — FastFixer (Liu et al., ASE 2024)
Targets efficiency of LLM repair for programming assignments: reports **repair/fix rate on student assignments** (+20.46% over the SOTA baseline) and **repair-generation latency/throughput**, with an inference-acceleration technique exploiting the overlap between buggy and fixed code (speedup reported as a time-per-patch metric).

## cref2024 — CREF (Yang et al., ISSTA 2024)
Introduces the **TutorCode** benchmark (real student C++ submissions with tutor guidance) and evaluates conversational repair using **TOP-5 and AVG-5 repair rates** (repair success within 5 sampled attempts / averaged over 5 runs), studying how test feedback and human-tutor guidance in the conversation change the repair rate; also discusses token/interaction rounds.

## Verification caveats
- **mmapr2022**: preprint only; superseded by PyDex (see above).
- **srepair2024**: arXiv only; the "$0.029/fixed bug" figure comes from the authors' GitHub description, and no peer-reviewed venue could be confirmed.
- Page numbers/DOIs were included in `references.bib` only where a search result explicitly confirmed them (e.g., Refactory, PAR, Sarfgen, Self-Refine pages omitted); nothing was fabricated.
- **anthropiccaching / openaicaching**: living documentation pages, cited as @misc with access date; exact discount multipliers are model-dependent (Anthropic: 0.1x base input price for cache reads, 1.25x/2x for 5-min/1-h cache writes; OpenAI: automatic prefix caching with a model-dependent cached-input discount, 50% at launch and larger for newer models).
