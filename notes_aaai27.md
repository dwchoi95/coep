# AAAI-27 Research Notes (compiled 2026-07-21)

Conference: AAAI-27, Thirty-Ninth+? (41st) AAAI Conference on Artificial Intelligence,
**February 16-23, 2027, Montreal, Canada**.

Access note: the sandbox proxy blocks direct fetches of aaai.org, ojs.aaai.org, arxiv.org,
openreview.net, and docs.google.com (HTTP 403 via proxy). Only raw.githubusercontent.com and
web-search snippets were reachable. All aaai.org facts below were extracted via search-engine
snippets of the official aaai.org pages (URLs cited); style files were downloaded from a
GitHub mirror whose file hashes match the canonical AuthorKit27 blobs found identically in
70+ independent repositories.

---

## 1. Author kit / LaTeX style

**AAAI-27 has its own kit: `AuthorKit27` with `aaai2027.sty` — it does NOT reuse aaai2026.sty.**

- `aaai2027.sty` declares: `\ProvidesPackage{aaai2027}[2027/05/04 AAAI 2027 Submission format]`
- It is a substantive revision of `aaai2026.sty` (~285 changed lines vs our local aaai2026.sty):
  - Fonts are now auto-loaded by the .sty (`newtxtext` Times-like text face, `helvet`, `courier`);
    templates forbid adding `\usepackage{times}` etc. yourself.
  - `[submission]` option now stamps an anonymized-submission notice ("This is an anonymized
    submission for review purposes only. Distribution, citation, or public sharing ... is
    strictly prohibited.") instead of just dropping the copyright line.
  - Adds `placeins` (float barrier before references) and `xcolor` (for the checklist).
- Usage: `\documentclass[letterpaper]{article}` + `\usepackage[submission]{aaai2027}` for
  review; `\usepackage{aaai2027}` for camera-ready.

### Files downloaded into /home/user/coep/paper/ (from a faithful GitHub mirror)

Mirror used: `https://raw.githubusercontent.com/Soumya-Chakraborty/legal-sum/4255655e161e22cad17e08b2cc986a1aee2b32f6/AuthorKit27/`
(git blob SHAs below match the identical canonical blobs in 70+ other repos mirroring the
official AAAI AuthorKit27, e.g. paths named `AuthorKit27/`, `AAAI_AuthorKit27/`, `_official_aaai27/`):

| File | git blob SHA |
|---|---|
| `aaai2027.sty` | `0acc2d8540c3fe891b51a730c6d143c95a87beb0` |
| `aaai2027.bst` | `a4a6129317d9039fefdbea927317f5a9a2d8da48` |
| `aaai2027.bib` (sample bib) | `f7426756c62cadd0a5b2e1d91c5649c7fedc0b63` |
| `AnonymousSubmission2027.tex` (submission template/instructions) | `0ec428c161d47837fae0bc23e64dd94b286a3a96` |
| `CameraReady2027.tex` | `e5e9ede09bc3164706a29692f79af093b1f51757` |
| `ReproducibilityChecklist.tex` | `c02bbd799fab2c3abf61c5b120b2300efd6955f2` |

The official distribution point is the AAAI author kit linked from
https://aaai.org/conference/aaai/aaai-27/submission-instructions/ (aaai.org/authorkit27-style
URL; not fetchable from this sandbox).

---

## 2. Key dates & submission rules (Main Technical Track)

Sources:
- CFP: https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/
- Submission instructions: https://aaai.org/conference/aaai/aaai-27/submission-instructions/
- Review process: https://aaai.org/conference/aaai/aaai-27/review-process/
- Modification guidelines: https://aaai.org/conference/aaai/aaai-27/paper-modification-guidelines/

Timeline (all 11:59 PM UTC-12 where applicable):

| Event | Date |
|---|---|
| OpenReview opens for author registration | June 17, 2026 |
| OpenReview opens for paper submission | June 30, 2026 |
| **Abstract deadline** | **July 21, 2026** |
| **Full paper deadline** | **July 28, 2026** |
| Supplementary material & code | July 31, 2026 |
| Phase 1 rejection notification | September 24, 2026 |
| Author feedback (rebuttal) window | October 19-25, 2026 |
| Final acceptance/rejection notification | November 30, 2026 |
| Conference | February 16-23, 2027 (Montreal) |

Every submission requires both an abstract submission and a corresponding paper submission;
no individual exceptions. (One deadline aggregator, getpaperpilot.com, lists "Jul 27, 2026
(UTC-12)"; the aaai.org-derived snippets consistently say July 28 — trust aaai.org.)

Format/limits:
- **Up to 9 pages total; pages 8-9 exclusively for references; i.e. 7 pages of content.**
- Ethics/impact statements, if included, count inside the 7 content pages.
- Acknowledgements must be omitted from the review version.
- **Double-blind**: remove all author/affiliation info; may substitute paper number/keywords.
  Anonymity per submission instructions; violations handled under paper modification guidelines.
- Reproducibility checklist: required; for AAAI-27 the kit's `ReproducibilityChecklist.tex`
  is uploaded/handled per the conference instructions (kit text says: "Check the instructions
  on your conference's website to see if you will be asked to provide this checklist with your
  paper or separately").
- **Checklist changes vs AAAI-26: none substantive.** Diff of AuthorKit26 vs AuthorKit27
  checklist files shows identical questions/answer options (yes/partial/no/NA) across the same
  4 sections (General Paper Structure; Theoretical Contributions; Dataset Usage; Computational
  Experiments); the only changes are `aaai2026`->`aaai2027` and removal of the now-redundant
  `times/helvet/courier/xcolor` package loads.

---

## 3. Review platform & review form

**Platform: OpenReview — confirmed.**
- AAAI 2027 venue: https://openreview.net/group?id=AAAI.org%2F2027%2FConference
  (also https://openreview.net/submissions?venue=AAAI.org%2F2027%2FConference)
- AAAI-27 pages state authors must use the same OpenReview account (same email) across all
  submissions and review assignments. AAAI-26 was also on OpenReview (record-breaking venue
  per OpenReview's own post:
  https://openreview.net/forum/bok|openreview_hosts_recordbreaking_aaai_2026_conference_with_pioneering_ai_review_system).

### Two-phase review (AAAI-27, per https://aaai.org/conference/aaai/aaai-27/review-process/)
- Phase 1: every paper gets **3 reviewers**. Sufficiently negative Phase-1 reviews =>
  rejection without author feedback (Phase-1 reject notification Sept 24, 2026).
- Phase 2: surviving papers get additional reviewers, **up to 5 reviews total**; Phase-2
  reviewers cannot see Phase-1 reviews until they submit their own.
- Single author-feedback phase (Oct 19-25, 2026) for Phase-2 papers, addressing questions or
  factual mistakes in reviews from both phases; then PC/SPC discussion phase considering the
  feedback.
- In AAAI-26, Phase 1 = 2 human reviews + 1 AI-generated review (AI review carried no
  scores/ratings/recommendations; decisions used human reviews only). Sources:
  https://aaai.org/conference/aaai/aaai-26/review-process/ ,
  "AI-Assisted Peer Review at Scale: The AAAI-26 AI Review Pilot" https://arxiv.org/abs/2604.13940 ,
  FAQ PDF https://aaai.org/wp-content/uploads/2025/08/FAQ-for-the-AI-Assisted-Peer-Review-Process-Pilot-Program.pdf
  Whether AAAI-27 repeats the AI-review component is not explicitly confirmed in accessible
  snippets of the AAAI-27 review-process page.

### Reviewer form fields (AAAI-25 form, documented verbatim in arXiv:2601.06884
"Paraphrasing Adversarial Attack on LLM-as-a-Reviewer", https://arxiv.org/pdf/2601.06884 ;
AAAI-26 reviewer instructions: https://aaai.org/conference/aaai/aaai-26/instructions-for-aaai-26-reviewers/):

1. **Summary** (free text)
2. **Strengths And Weaknesses** (free text; identify strengths, flaws/shortcomings, and
   suggestions for improvement)
3. **Questions For The Authors** (free text)
4. **Significance Of The Problem**
5. **Justification Of Approach**
6. **Quality Of Evaluation**
7. **Reproducibility And Facilitation Of Follow Up Work**
8. **Ethical Considerations**
9. **Overall Evaluation** (numeric, 1-10)
10. **Confidence** (numeric, 1-5)

### Scales
- **Overall evaluation: 1-10**, NeurIPS-style anchors (in use at AAAI since ~AAAI-22; the
  "10" and "1" anchors confirmed for the AAAI-26 cycle via search snippets):
  - 10: Award quality — "Technically flawless paper with groundbreaking impact on one or more
    areas of AI, with exceptionally strong evaluation, reproducibility, and resources, and no
    unaddressed ethical considerations"
  - 9: Very Strong Accept; 8: Strong Accept; 7: Accept; 6: Weak Accept ("technically solid,
    moderate-to-high impact, no major concerns wrt evaluation/resources/reproducibility/ethics");
  - 5: Borderline accept (reasons to accept outweigh reasons to reject, e.g. limited evaluation);
  - 4: Borderline reject; 3: Reject; 2: Strong Reject; 1: Very Strong Reject (e.g. trivial or
    well-known results, unaddressed ethical considerations, poorly written).
  (Cross-referenced with UAI/NeurIPS instructions noting the same scale was used by
  "AAAI 2022, ICLR 2021, ICML 2021, NeurIPS 2021": https://www.auai.org/uai2022/reviewing_instructions)
- **Confidence: 1-5**: 5 = absolutely certain, very familiar with related work and technical
  details; 4 = confident though not absolutely certain; 3 = fairly confident; 2 = willing to
  defend assessment but substantial uncertainty; 1 = educated guess.
- Sub-axes 4-8 above (significance / justification / evaluation quality / reproducibility /
  ethics) are the AAAI analogue of per-axis novelty/soundness/clarity items; exact response
  type (short text vs small ordinal scale) not verifiable from this sandbox — the numeric
  fields extractable from scraped reviews are Overall Evaluation and Confidence.

### Author response (rebuttal) format
- AAAI-26 rules (https://aaai.org/conference/aaai/aaai-26/aaai-26-faq-for-authors-rebuttal/):
  **one single rebuttal covering all reviews, max 2500 characters**, markdown allowed,
  **no URLs** (responses containing URLs may be withheld); may address human and AI reviews.
- AAAI-27 announces the same single author-feedback phase (Oct 19-25, 2026); per-cycle
  character limit for AAAI-27 not yet visible, expect the AAAI-26-style limit.

---

## 4. Reciprocal reviewing / mandatory author reviewing — YES for AAAI-27

- "Given the size of the conference, **all authors of AAAI-27 submissions will be expected to
  join the conference's reviewer pool unless prevented by extenuating circumstances.**"
  (AAAI-27 pages: https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/ ,
  https://aaai.org/conference/aaai/aaai-27/review-process/)
- Each submission **nominates a reciprocal reviewer at abstract submission; after the July 21,
  2026 abstract deadline the nominated reciprocal reviewer cannot be changed** until the end
  of the review process (https://aaai.org/conference/aaai/aaai-27/paper-modification-guidelines/).
- Same design as AAAI-26, where the PC recruiting process explicitly included "reciprocal
  reviewers, nominated by coauthors of submitted papers", authors were "expected to be
  available to review (light load)... Failure to meet this expectation may result in sanctions
  such as paper rejection", and Phase-1 allocations capped reciprocal reviews per paper
  (https://aaai.org/conference/aaai/aaai-26/review-process-update/ ,
  https://aaai.org/conference/aaai/aaai-26/review-process/).
- Distinct but related integrity rule: AAAI prohibits collusive "reciprocal reviewing to
  inflate scores" (coordinated bidding/reviewing), with penalties from desk rejection up to
  multi-year bans (AAAI-27 main-track call / policies pages).

---

## Source index

- https://aaai.org/conference/aaai/aaai-27/ (conference home; dates/venue)
- https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/ (CFP, deadlines, reviewer-pool requirement)
- https://aaai.org/conference/aaai/aaai-27/submission-instructions/ (page limits, anonymity, author kit)
- https://aaai.org/conference/aaai/aaai-27/review-process/ (two-phase review, OpenReview, feedback window)
- https://aaai.org/conference/aaai/aaai-27/paper-modification-guidelines/ (reciprocal-reviewer lock after abstract deadline)
- https://openreview.net/group?id=AAAI.org%2F2027%2FConference (AAAI-27 OpenReview venue)
- https://aaai.org/conference/aaai/aaai-26/review-process/ and .../review-process-update/ (AAAI-26 comparison)
- https://aaai.org/conference/aaai/aaai-26/instructions-for-aaai-26-reviewers/ (reviewer form guidance)
- https://aaai.org/conference/aaai/aaai-26/aaai-26-faq-for-authors-rebuttal/ (2500-char single rebuttal, no URLs)
- https://arxiv.org/abs/2604.13940 (AAAI-26 AI Review Pilot paper)
- https://arxiv.org/pdf/2601.06884 (documents AAAI-25 review form fields verbatim)
- https://www.auai.org/uai2022/reviewing_instructions (provenance of the shared 1-10 scale)
- Mirror for kit files: https://github.com/Soumya-Chakraborty/legal-sum tree `4255655e` path `AuthorKit27/`
