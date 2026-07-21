# AAAI Topic / Keyword Research for "Synthesize Once, Repair Many"

Research date: 2026-07-21. Note on timing: AAAI-26 took place Jan 20-27, 2026 (Singapore; 23,680
submissions, 4,167 accepted, 17.6% — https://www.bohrium.com/en/blog/research-notes/aaai-2026-accepted-papers-highlights/).
The **live CFP is AAAI-27** (https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/), which uses a
revised "areas and topics" taxonomy. Both are covered below.

Sandbox caveat: aaai.org, ojs.aaai.org, openreview, dblp, and web.archive.org are all blocked by the proxy
(HTTP 403 at CONNECT). Keyword lists below were reconstructed from (a) a GitHub mirror of the AAAI keyword
taxonomy, (b) the AAAI-21 reviewer-matching repo of AAAI's own PC chairs' tooling, and (c) search-engine
snippets of the official pages; accepted-paper placements come from the papercopilot/paperlists JSON dumps of
the official AAAI proceedings (which record each paper's proceedings technical track = its primary keyword area).

---

## 1. The AAAI keyword taxonomy (AAAI-25/26) and candidate keywords for us

AAAI-26 asks for **one mandatory primary keyword + up to five secondary keywords**, from a list of ~300
keywords grouped into areas (APP, CMS, CV, CSO, DMKM, GTEP, HAI, ROB, KRR, ML, MAS, PEAI, PRS, RU, SO, NLP)
(official page, proxy-blocked: https://aaai.org/conference/aaai/aaai-26/keywords/; structure confirmed via
search snippets). Guidance from the CFP: pick the area of the paper's *primary contribution* and the community
that benefits most (https://aaai.org/conference/aaai/aaai-26/main-technical-track-call/).

Mirrors used for the verbatim keyword strings:
- https://raw.githubusercontent.com/CMBAgents/cmbagent/main/cmbagent/utils/keywords/aaai.md (AAAI keyword list, 297 lines)
- https://raw.githubusercontent.com/ChrisCameron1/LargeConferenceMatching/master/scorers/keyword-scorer/helper_data/SecondaryAreas_track1_.txt
  (AAAI PC reviewer-matching data; full APP list)

Candidate keywords relevant to our paper (verbatim):

**Application Domains (APP)** — the family every AAAI program-repair paper to date has used:
- `APP: Software Engineering`  <-- strongest candidate
- `APP: Education`             <-- second candidate (exists in APP list per matching-repo mirror)
- `APP: Other Applications`

**Natural Language Processing (NLP)** — where most code-LLM papers land:
- `NLP: (Large) Language Models`
- `NLP: Applications`
- `NLP: Generation`
- `NLP: Learning & Optimization for NLP`
- Note: there is **no** "NLP: Code Generation" keyword in the AAAI taxonomy (unlike ACL ARR's
  "NLP Applications / code generation" — http://aclrollingreview.org/areas). Code papers use the NLP keywords above.

**Humans and AI (HAI)**:
- `HAI: Applications`, `HAI: Human-in-the-loop Machine Learning` (weak fit — HAI track is small, ~39 papers in AAAI-25)

**Special tracks** (separate submission tracks, not keywords): *AI for Social Impact* (AISI) — education papers
appear here (see below; AAAI-27 AISI call: https://aaai.org/conference/aaai/aaai-27/aisi-call/); *AI Alignment* (since AAAI-25).

### AAAI-27 (live CFP) revised topic names
AAAI-27 uses ">200 topics"; areas page: https://aaai.org/conference/aaai/aaai-27/areas-and-topics/ (proxy-blocked;
via search snippets). Confirmed via snippets:
- `APP: Software Engineering` still exists at AAAI-27.
- `APP: AI for Education & Learning Technologies` (renamed/expanded education topic).
- Other APP topics: AI for Science, Climate/Sustainability & Environment, Healthcare & Bioinformatics,
  Humanities & Computational Social Science, IoT/Sensor Networks & Smart Cities, Mobility/Transportation & Autonomous...
- Area codes at AAAI-27: APP, AUD (new Audio/Speech), CMS, CSO, CV, DMKM, GTEP, HAI, KRR, MAS, ML, NLP, PEAI, PRS, ROB, RU, SO.

---

## 2. What actually gets accepted, and where (verified placements)

Placement = proceedings technical-track (issue) of the accepted paper, from papercopilot dumps of ojs.aaai.org:
https://raw.githubusercontent.com/papercopilot/paperlists/main/aaai/aaai2023.json (idem 2024, 2025).
AAAI-25 main track = 3,182 papers; "Application Domains" track = 139 papers; NLP tracks = 308; AISI = 88.

### Program repair (our exact task family) — ALL in the APP / "Domain(s) of Application" track
1. **RING — "Repair Is Nearly Generation: Multilingual Program Repair with LLMs" (AAAI-23)** — track
   "Domain(s) of Application"; 155 citations. LLM few-shot repair over 6 languages; "last-mile" errors.
   https://ojs.aaai.org/index.php/AAAI/article/view/25642
2. **"Counterexample Guided Program Repair Using Zero-Shot Learning and MaxSAT-based Fault Localization"
   (Orvalho, Janota, Manquinho, AAAI-25)** — track "Application Domains". *Explicitly about Automated Program
   Repair for Introductory Programming Assignments (IPAs)*: MaxSAT-based fault localization + LLM in a CEGIS
   loop; motivated by faculty feedback burden. This is our closest neighbor and proof AAAI accepts IPA-repair
   papers. https://ojs.aaai.org/index.php/AAAI/article/view/32046
3. **"Less Is More: Adaptive Program Repair with Bug Localization and Preference Learning" (AAAI-25)** — track
   "Application Domains". Introduces a new task (AdaPR: minimal-modification patches) + a 3-stage preference-
   learning framework. Patch-minimality framing = same axis as our "patch size" metric.
   https://ojs.aaai.org/index.php/AAAI/article/view/31988
4. **"Hot or Cold? Adaptive Temperature Sampling for Code Generation with Large Language Models" (AAAI-24)** —
   track "Application Domains"; 38 citations. https://ojs.aaai.org/index.php/AAAI/article/view/27798
5. **"Uncovering LLM-Generated Code: A Zero-Shot Synthetic Code Detector via Code Rewriting" (AAAI-25)** —
   track "Application Domains"; education-misuse motivation. https://ojs.aaai.org/index.php/AAAI/article/view/32082
6. **"Themis: Automated Constraint-Aware Test Synthesis Framework for Code" (AAAI-26)** — accepted in AAAI-26
   technical tracks (Vol. 40 No. 17). https://ojs.aaai.org/index.php/AAAI/article/view/40741

### Code-LLM papers in NLP tracks (method-of-LLM contributions)
7. **CodeHalu** (execution-based code-hallucination benchmark+detector, AAAI-25, NLP track) — https://ojs.aaai.org/index.php/AAAI/article/view/34717
8. **DOMAINEVAL** (auto-constructed multi-domain code-gen benchmark, AAAI-25, NLP track) — https://ojs.aaai.org/index.php/AAAI/article/view/34811
9. **InverseCoder** (self-improving instruction-tuned code LLMs, AAAI-25, NLP track) — https://ojs.aaai.org/index.php/AAAI/article/view/34742
10. **Hierarchical Context Pruning for repo-level code completion** (AAAI-25, NLP track) — https://ojs.aaai.org/index.php/AAAI/article/view/34782
11. **Security Attacks on LLM-based Code Completion Tools** (AAAI-25, NLP track) — https://ojs.aaai.org/index.php/AAAI/article/view/34537
12. **Can LLM Replace Stack Overflow? Robustness/Reliability of LLM Code Generation** (AAAI-24, Safe/Robust/
    Responsible AI special track) — https://ojs.aaai.org/index.php/AAAI/article/view/30185

### AI-for-education papers
13. **Agent4Edu** (generative agents simulate learner responses, AAAI-25, NLP track) — https://ojs.aaai.org/index.php/AAAI/article/view/34565
14. **iLLuMinaTE** (LLM-XAI student-performance feedback, AAAI-25, **AI for Social Impact track**) — https://ojs.aaai.org/index.php/AAAI/article/view/35065
15. **Towards Automatic Boundary Detection for Human-AI Collaborative Hybrid Essay in Education** (AAAI-24,
    **AISI track**) — https://ojs.aaai.org/index.php/AAAI/article/view/30258
16. **Symbolic Cognitive Diagnosis for Intelligent Education Systems** (AAAI-24, ML track — accepted in ML
    because contribution = new hybrid-optimization method) — https://ojs.aaai.org/index.php/AAAI/article/view/29413
17. **When to Show a Suggestion? Integrating Human Feedback in AI-Assisted Programming** (AAAI-24, Humans-and-AI
    track; Copilot telemetry) — https://ojs.aaai.org/index.php/AAAI/article/view/28878

### LLM cost/efficiency papers
18. **BLADE: black-box LLM + small domain model** (AAAI-25, NLP track) — https://ojs.aaai.org/index.php/AAAI/article/view/34620
19. **Trigger3: adaptive small-model/LLM selector for query correction** (AAAI-25, DMKM track) — cascade
    "small model first, LLM only when needed" = structurally identical to our rules-first/LLM-fallback design.
    https://ojs.aaai.org/index.php/AAAI/article/view/33447
20. **Frugal LMs Trained to Invoke Symbolic Solvers** (AAAI-24, NLP track) — neuro-symbolic delegation for
    cost reduction. https://ojs.aaai.org/index.php/AAAI/article/view/29750

Also note: AAAI-26 tutorial "Computational Optimization in LLM Inference: Reuse and Delegation"
(https://aaai.org/conference/aaai/aaai-26/tutorial-and-lab-forum/) — reuse/delegation-for-cost is a recognized,
timely AAAI theme; our amortization story fits it.

---

## 3. Common characteristics of accepted papers in these topics

- **Framing: AI contribution first, SE/edu domain second.** Every accepted paper above leads with a general
  AI-methodological idea (CEGIS loop with zero-shot LLMs; preference learning for minimal patches; adaptive
  decoding; agentic simulation; model cascading) and treats repair/education as the application domain.
  Pure "we built a tool and it works" SE papers do not appear in the APP track; even APP-track papers carry a
  named, reusable technique. Our framing should be: *amortized neuro-symbolic synthesis — an LLM agent distills
  its repair capability into a reusable symbolic artifact (rule-based repairer) whose marginal inference cost is
  zero* — not "a grading tool for instructors".
- **Novel method > empirical study.** 16 of the 20 papers propose a named new method/framework/task; the
  empirical-study papers that got in (Can-LLM-Replace-Stack-Overflow, CodeHalu, DOMAINEVAL) each contribute a
  new benchmark or evaluation methodology as the artifact. A study without a new artifact/method is a red flag.
- **Evaluation scale.** Typical: 2-4 benchmarks/datasets and 3-6 LLMs/baselines. RING: 6 languages;
  CodeHalu: 699 tasks x 17 LLMs; DOMAINEVAL: ~2.5k samples, 10+ LLMs; Orvalho AAAI-25: C introductory-assignment
  benchmark (C-Pack-IPAs) vs symbolic (Clara/Verifix-class) and LLM baselines; Less-Is-More: multiple languages,
  new AdaPR task. For us: >=2 assignment corpora (e.g., our course data + a public IPA benchmark like
  Codeforces/refactory/C-Pack-IPAs), >=3 backbone LLMs, and both symbolic-APR and pure-LLM baselines.
- **Cost/efficiency framing is present and rewarded, but always paired with quality parity.** Trigger3, BLADE,
  Frugal-LMs all argue "small/cheap component handles most cases; LLM invoked selectively" and report both
  quality and cost. None reports dollar cost alone; they show accuracy >= LLM-only at a fraction of calls.
  Our repair-rate-vs-$ Pareto curve matches this template exactly.
- **Education-specific papers cluster in the AI for Social Impact special track** (iLLuMinaTE, hybrid-essay
  detection, knowledge tracing), which expects deployment/stakeholder framing; technical education papers with
  a general method go to ML/NLP/APP instead.
- **Patch minimality/consistency is an accepted evaluation axis** (Less-Is-More's whole premise), so our
  patch-size metric is well-precedented; tie it to pedagogical value (small patches = comprehensible feedback,
  cf. Orvalho's feedback-burden motivation).

---

## 4. Recommendation

**For AAAI-27 main track (live CFP, https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/):**
- **Primary keyword: `APP: Software Engineering`** — the demonstrated home of every AAAI program-repair paper
  (RING AAAI-23; Orvalho AAAI-25; Less-Is-More AAAI-25; Hot-or-Cold AAAI-24 all published in the
  Application-Domains/Domain-of-Application track). Reviewers there know APR, IPAs, and code LLMs.
- **Secondary keywords: `NLP: (Large) Language Models`** (LLM-agent synthesis component),
  **`APP: AI for Education & Learning Technologies`** (AAAI-27 name; at AAAI-25/26 use `APP: Education`),
  and optionally `NLP: Applications` or (if arguing the neuro-symbolic angle) a KRR/program-synthesis keyword.
- Alternative primary if we reposition the contribution as a general LLM-cost/distillation method evaluated on
  repair: `NLP: (Large) Language Models` — but our evaluation (repair rate, patch size, $ on student
  submissions) is domain-anchored, so APP: Software Engineering is the honest and safest choice.
- The **AI for Social Impact special track** is a viable plan-B (education-access framing, real course
  deployment), but AISI expects stakeholder/deployment evidence and problem-novelty over method benchmarking.

**What accepted papers in this topic do that we must do too:**
- Name the framework and lead with the general AI idea (amortized synthesis of a symbolic repairer by an LLM
  agent; "synthesize once, repair many" as a general recipe, instantiable beyond education).
- Compare against BOTH families of baselines: symbolic IPA repairers (Clara, Refactory, Verifix,
  Orvalho AAAI-25) and direct-LLM repair (RING-style prompting, GPT-4-class), on >=2 benchmarks, >=3 LLMs.
- Report quality-cost jointly: repair rate at matched or better quality vs LLM-per-submission, plus $-per-
  submission amortization curves and fallback-invocation rate (Trigger3/BLADE template).
- Justify patch size pedagogically (minimal edits = student-comprehensible feedback; cite Less-Is-More AdaPR
  and Orvalho's feedback-burden motivation).
- Include ablations of the agent loop (rule-synthesis iterations, fallback threshold, generalization of a
  synthesized repairer across semesters/assignments).

**Red flags:**
- Pure-SE tool-paper framing ("we built a system, here are engineering details") — no such paper appears in
  AAAI-24/25/26 main-track lists; SE venues (ICSE/FSE/ASE) absorb those. AAAI needs a generalizable AI method.
- Do not pick an HAI primary: HAI track is tiny (~39/3,182 at AAAI-25) and our paper has no human-subject study.
- Do not claim an "NLP: Code Generation" keyword — it does not exist at AAAI; the NLP-side keyword is
  `NLP: (Large) Language Models`.
- Dollar-cost-only evaluation without quality parity is not the accepted pattern; always pair cost with
  repair-rate parity or superiority.
- EAAI (AI-education symposium, https://aaai.org/conference/aaai/aaai-27/eaai-27-call/) is about *teaching AI*,
  not AI for programming education — wrong venue despite the name overlap.
