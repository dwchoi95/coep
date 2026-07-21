# AAAI Submission Notes (AAAI-26 conventions)

Compiled 2026-07-21 for the CoEP paper (cost-effective LLM-based APR for programming assignments).
All facts below are sourced; URLs are given inline.

---

## 1. AAAI-26 format facts

Primary sources:
- Main Technical Track CFP: https://aaai.org/conference/aaai/aaai-26/main-technical-track-call/
- Submission instructions: https://aaai.org/conference/aaai/aaai-26/submission-instructions/
- Reproducibility checklist: https://aaai.org/conference/aaai/aaai-26/reproducibility-checklist/
- Supplementary material: https://aaai.org/conference/aaai/aaai-26/supplementary-material/
- Camera-ready info: https://proceedings.aaai.org/info
- (Note: aaai.org pages were read via search-engine snapshots because direct fetches of aaai.org are blocked by this sandbox's egress proxy; the LaTeX kit itself was obtained — see Section 2.)

### Page limits
- **Submission:** up to **7 pages of technical content**, plus **additional pages solely for references and the reproducibility checklist** (checklist goes after the references and does not count toward the limit).
- **Camera-ready:** accepted Main Track papers get **7 pages + references/acknowledgements**, with the option to **purchase up to 2 extra technical pages at $300/page**.
- Supplementary material (appendix, code) is submitted separately; reviewers are **not required** to read it.

### Style/format
- **Two-column, AAAI camera-ready style is mandatory at submission time** (AAAI reviews in camera-ready format, unlike *SE venues).
- Style files (from the 2026 Author Kit, https://aaai.org/authorkit26/): **`aaai2026.sty`** and **`aaai2026.bst`**. The `.sty` header reads: `\ProvidesPackage{aaai2026}[2026/04/29 AAAI 2026 Submission format]`.
- The sty may **not be modified** ("MODIFICATIONS ... WILL RESULT IN REJECTION OF YOUR PAPER" — comment inside `aaai2026.sty`).

### Required preamble (from the official template, verbatim "DO NOT CHANGE THIS" lines)
```latex
\documentclass[letterpaper]{article}
\usepackage[submission]{aaai2026}   % anonymous review version
% \usepackage{aaai2026}             % camera-ready version
\usepackage{times}
\usepackage{helvet}
\usepackage{courier}
\usepackage[hyphens]{url}
\usepackage{graphicx}
\urlstyle{rm}  \def\UrlFont{\rm}
\usepackage{natbib}    % no options allowed
\usepackage{caption}   % no options allowed
\frenchspacing
\setlength{\pdfpagewidth}{8.5in}
\setlength{\pdfpageheight}{11in}
\pdfinfo{ /TemplateVersion (2026.1) }
```
- Bibliography: `\bibliographystyle{aaai2026}` with natbib `\cite/\citep/\citet`.
- **Explicitly forbidden packages** (list in the template): `authblk`, `balance`, `CJK`, `float`, `flushend`, `fontenc`, `fullpage`, `geometry`, `grffile`, **`hyperref`** (or any link-embedding package), `navigator`, `indentfirst`, `layout`.
- Layout constants baked into `aaai2026.sty` (useful sanity checks, not to be re-set manually): text block 7.0in x 9.0in, `\columnsep` 0.375in, `\topmargin` -0.25in, `\oddsidemargin` -0.25in, body font 10pt on 11pt leading, captions/footnotes 9pt, `\parindent` 10pt, title box 2.25in.
- Algorithms: `algorithm` + `algorithmic` recommended; listings via `newfloat` + `listings` with the `ruled` caption style defined in the template.

### Section conventions (from the template's "Headings and Sections")
1. Main content sections (section numbers are **optional** at AAAI; off by default)
2. Appendices (optional; lettered if sections are numbered)
3. **Ethical Statement** (optional, unnumbered)
4. **Acknowledgements** (optional, unnumbered, ≤ ~3 sentences, camera-ready only)
5. **References** (unnumbered, flows directly after text — no page break before it)

### Anonymity (double-blind)
- Submissions are **fully anonymous**: no author names/affiliations; use the `[submission]` option of `aaai2026.sty`.
- Self-citations must be anonymized "whenever the reader can infer that they are to the authors' previous work" (template text).
- Don't include acknowledgements, grant numbers, or identifying repo links at submission time (use anonymized repos, e.g. anonymous.4open.science).

### Reproducibility checklist
- Mandatory; appended **after the references** inside the main PDF; does not count toward 7 pages. Official LaTeX template ships in the Author Kit folder `ReproducibilityChecklist` (mirror: https://github.com/QuenithAI/aaai-26-reproduction-checklist).
- Answer "yes" per question if the info is in the paper **or** in a technical appendix explicitly referenced from the main paper; free-text elaboration goes in a "Reproducibility Checklist" section at the end of the appendix.
- Question categories (from the official template mirror): **General paper structure** (3 Qs: pseudocode/conceptual outline of methods; opinions vs. facts delineated; pedagogical references), **Theoretical contributions** (7 Qs: assumptions, formal claims, proofs, tools cited), **Datasets** (6 Qs: motivation, novelty, public availability, citations, justification if private), **Computational experiments** (12 Qs: hyperparameter search, preprocessing + source code released, seeds, compute infrastructure, metrics defined, number of runs, statistics beyond averages, significance tests, final hyperparameters).
- **Reviewers explicitly score reproducibility and it is weighed in decisions** (https://aaai.org/conference/aaai/aaai-26/reproducibility-checklist/).
- For CoEP: this means we should report model versions + API snapshot dates, temperature/sampling settings, seeds, number of repetitions, exact per-query token/cost accounting, and release prompts + code.

---

## 2. Author-kit download status: **SUCCESS (via GitHub mirror)**

- Direct downloads from `aaai.org` (AuthorKit26.zip) and `ctan.org` failed: the sandbox egress proxy returns `CONNECT tunnel failed, response 403` / "Host not in allowlist" for those hosts (also for arxiv.org and api.github.com). `raw.githubusercontent.com` **is** allowed.
- The real files were therefore fetched from the faithful mirror **https://github.com/lizhemin15/AAAI-2026-Latex-Unified** (raw.githubusercontent.com) and saved to `/home/user/coep/paper/`:
  - `aaai2026.sty` (11,802 B — official AAAI 2026 submission style, header verified)
  - `aaai2026.bst` (30,207 B — official BibTeX style)
  - `aaai2026.bib` (sample bibliography)
  - `aaai2026-unified-template.tex` (template containing the full official formatting-instructions text; toggle `\def\aaaianonymous{true}` for the anonymous version)
- No fallback approximation is needed. (If it ever were: `\documentclass[letterpaper]{article}` + Times/Helvetica/Courier, 10/11pt body, 7x9in text block, 0.375in column sep, two-column — per the constants listed in Section 1.)
- Note: `aaai2026.sty` forbids modification; treat these files as read-only inputs.

---

## 3. Structure/style study: 5 comparable papers

### (a) ChatRepair — "Automated Program Repair via Conversation: Fixing 162 out of 337 Bugs for $0.42 Each using ChatGPT" (Xia & Zhang, ISSTA 2024)
- https://dl.acm.org/doi/10.1145/3650212.3680323 ; arXiv: https://arxiv.org/abs/2304.00385
- **The** model for cost framing: the headline number ($0.42/bug, 162/337 Defects4J bugs) is *in the title and abstract*. Our abstract should likewise carry one repair-rate number and one cost number.
- Structure: Intro -> Background & Related Work -> Approach (with a running conversation example figure early) -> Experimental Design (RQs + benchmarks + metrics) -> Results (one subsection per RQ) -> Threats to Validity -> Conclusion.
- RQ framing: RQ1 = effectiveness vs. state of the art; RQ2 = contribution of each component (ablation); RQ3 = cost analysis. Roughly 5 figures (workflow + prompt examples) and 5-6 tables (per-benchmark comparisons, ablations, cost).
- Intro recipe: (1) APR matters, (2) prior LLM-APR wastes information by sampling independently and re-querying from scratch, (3) key insight — keep the conversation going with test-failure feedback, (4) contributions bullet list ending with headline numbers.

### (b) MMAPR — "Repairing Bugs in Python Assignments Using Large Language Models" (Zhang, Cambronero, Gulwani, Le, Piskac, Soares, Verbruggen; Microsoft Research, arXiv 2022)
- https://arxiv.org/abs/2209.14876 ; https://www.microsoft.com/en-us/research/publication/repairing-bugs-in-python-assignments-using-large-language-models/
- Closest domain match (LLM repair of *student* programs). Framing: reduce instructor/TA burden; feedback via smallest possible patch.
- Structure: Intro -> Overview with a **worked student-assignment example** walked end-to-end (motivating example gets its own early section, before the technique) -> Approach (multimodal prompts, iterative querying, test-case-based few-shot selection, program chunking) -> Evaluation (286 real student programs; baseline = BIFI syntax repair + Refactory semantic repair) -> ablations -> related work.
- Evaluation dimensions worth copying: repair rate AND **patch size (token edit distance)** — for education, small patches ~ pedagogically useful feedback.
- Lesson: the pipeline is presented as numbered stages matching one architecture figure; each ablation maps 1:1 to a pipeline stage.

### (c) RING — "Repair Is Nearly Generation: Multilingual Program Repair with LLMs" (Joshi, Cambronero, Gulwani, Le, Radicek, Verbruggen; **AAAI-23**)
- https://ojs.aaai.org/index.php/AAAI/article/view/25642 ; arXiv: https://arxiv.org/abs/2208.11640
- Useful as an *AAAI-formatted* APR paper: shows how SE-style content fits 7 two-column pages — unnumbered sections, no mandated "Threats to Validity" section (limitations folded into Discussion), fewer/denser tables than an ICSE paper, motivating multi-language examples compressed into the Intro + one figure.
- Framing device: one prompt strategy (few-shot "repair as generation" with error-message conditioning) evaluated across 6 languages, arguing generality; per-language results in one consolidated table.
- Lesson for CoEP at AAAI: budget ~1 page intro, ~0.5 page example, ~2 pages method, ~2.5 pages experiments, ~0.5 page related work + conclusion.

### (d) "Automated Program Repair in the Era of Large Pre-trained Language Models" (Xia, Wei, Zhang; ICSE 2023)
- https://dl.acm.org/doi/10.1109/ICSE48619.2023.00129 ; arXiv: https://arxiv.org/abs/2210.14179
- Model empirical-study skeleton: Intro -> Background -> **Study design** (explicit RQ list with rationale, LLM/benchmark/metric selection) -> per-RQ result sections each ending in a boxed/bolded **"Answer to RQn"** takeaway -> Implications/Discussion -> Threats to Validity -> Related Work -> Conclusion.
- RQs cover effectiveness, **efficiency/cost (patches per time budget, sampling cost)**, and design-choice sensitivity — a good template for our cost-effectiveness RQs.
- Threats handled as the classic 3-way split: internal (implementation, data leakage/memorization of benchmarks — especially important for LLMs on public assignment datasets), external (benchmark/language generalization), construct (metric validity, plausible vs. correct patches).

### (e) FrugalGPT — "How to Use Large Language Models While Reducing Cost and Improving Performance" (Chen, Zaharia, Zou; Stanford, 2023; TMLR 2024)
- https://arxiv.org/abs/2305.05176
- Model for **cost-efficiency framing**: opens with a table of commercial LLM API prices spanning two orders of magnitude — a "cost anatomy" exhibit that immediately legitimizes the problem. Headline: matches GPT-4 accuracy with **up to 98% cost reduction**, or +4% accuracy at the same cost.
- Contribution structured as a small **taxonomy of cost-reduction strategies** (prompt adaptation, LLM approximation, LLM cascade) followed by a deep dive on one (cascade with a learned scorer deciding when to escalate to a pricier model).
- Signature figure: **accuracy-vs-cost Pareto frontier** with the proposed method dominating individual LLMs. CoEP should have exactly this plot (repair rate vs. $ per assignment/student).

### Cross-cutting takeaways for CoEP
- Put one repair-rate number and one cost number in the abstract (and consider the title, a la ChatRepair).
- Intro formula: societal/instructor cost of manual feedback -> LLM APR works but naive use is expensive at classroom scale (quantify: N students x M submissions x $/query) -> insight -> contributions with numbers.
- Motivating example: 1 figure with a real (anonymized) student program + buggy/fixed diff, placed end of Intro or its own half-page "Motivating Example" section (MMAPR style).
- RQs: RQ1 effectiveness vs. baselines; RQ2 cost/efficiency (Pareto plot); RQ3 ablation of the cost-saving components; optionally RQ4 patch quality/pedagogical value (patch size, RelativePatchSize).
- AAAI has no mandatory Threats section — use a short "Limitations" or fold into Discussion, and put the classic internal/external/construct threats content there plus a data-contamination note; societal/educational-integrity concerns go in the optional unnumbered "Ethical Statement".
- Typical exhibit budget in these papers: 4-6 figures + 4-6 tables; at AAAI-26's 7 pages plan for ~4 figures + ~4 tables.

---

## 4. AAAI review criteria (self-check rubric)

Source: AAAI-26 Main Technical Track CFP (https://aaai.org/conference/aaai/aaai-26/main-technical-track-call/), AAAI-26 reviewing/reproducibility pages (https://aaai.org/conference/aaai/aaai-26/reproducibility-checklist/, https://aaai.org/conference/aaai/aaai-26/submission-instructions/).

Per the CFP, submissions are scored on:
1. **Significance & novelty of the contributions** — of the research questions, methods, experiments, and analyses. Self-check: is "cost-effective APR for education" argued as an open problem with quantified stakes, and is the delta over ChatRepair/MMAPR-style baselines explicit?
2. **Soundness (theoretical and/or empirical) of claims** — highest-weight item in practice. Self-check: every claim in abstract/intro maps to a table/figure; multiple runs with variance + significance tests (the reproducibility checklist explicitly asks for statistics beyond averages and significance testing); fair baseline budgets (same token/query budget when comparing cost).
3. **Relevance to the AAAI community** — position the work as AI (LLM reasoning/inference-cost trade-offs), not purely an SE tool paper; cite prior AAAI/NeurIPS LLM-for-code work (e.g., RING, AAAI-23).
4. **Clarity of exposition** — AAAI reviewers read 7-page camera-ready-format papers quickly: front-load contributions, one idea per figure, boxed RQ answers.
5. **Reproducibility** — separately assessed and "weighed when making final decisions": checklist answers must be honest "yes"es; release code, prompts, seeds, model versions/dates, and per-experiment cost accounting; anonymized repo at submission.
6. **Responsible research practice / societal impact** — CFP calls out human-subject data, sensitive data, and bias; for CoEP: student-data privacy/consent, and an Ethical Statement covering feedback-automation risks (over-reliance, fairness across student populations, academic integrity).

Practical form note: recent AAAI review forms ask reviewers for numeric sub-scores along these axes plus an overall recommendation, and (since AAAI-24/25/26) reviewers must justify scores w.r.t. reproducibility; a paper can be rejected for unsupported empirical claims even with a novel idea.
