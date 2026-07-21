# Adversarial Review 2 — "Synthesize Once, Repair Many" (paper/main.tex)

Reviewer stance: skeptical AAAI reviewer, specialty unsound empirical claims.
Every number below was recomputed from `runs/summary.json`, `runs/baseline/results.json`,
`runs/coep/results/*.json`, `runs/coep/build_eval/*.json`, `runs/ablation_generic/results.json`,
and the harness code in `coep/` and `scripts/analyze.py`.

**Recommendation: reject in current form.** The arithmetic is almost entirely honest — nearly
every number in the abstract, tables, and RQ boxes reproduces from the committed raw data —
but three design-level problems (B1–B3) undermine the central empirical claims, and the
headline economics are computed against the weakest available comparator (B2).

---

## Part 1 — Number-by-number verification

Numbers that **check out exactly** against the data (verified by recomputation):

| Claim (paper) | Recomputed | Verdict |
|---|---|---|
| n = 10 assignments, 229 buggy, 179 eval | 10; 179 eval + 50 build = 229 | OK |
| Baseline repair rate 100.0 [97.9, 100] | 179/179; Wilson [.9790, 1.0] | OK |
| Baseline quality rate 92.7 (RPS≤0.35) | 166/179 = 92.74; 13 over-cap | OK |
| Baseline mean RPS 0.127 | 0.12747 | OK |
| CoEP-local 74.9 [68.0, 80.6] | 134/179 = 74.86; CI [.6803, .8065] | OK |
| CoEP-local mean RPS 0.058 | 0.05776; zero cap violations | OK |
| Fallback rate 25.1% | 45/179 = 25.14 | OK |
| Baseline 740 in / 51 out tokens | 740.46 / 51.40 mean | OK |
| Baseline $2.99e-3/sub; cached $1.53e-3 (−49%) | 0.535644/179 = 2.992e-3; 0.273821/179 = 1.530e-3; −48.9% | OK (but see M5) |
| Build 47,493 in / 74,407 out; $1.2586 total; $0.126/assignment; ≈42 baseline repairs | all reproduce ($0.12586 = 42.06×c) | OK |
| Fallback 739/54 tok, $3.02e-3 per escalation | 33,233/45 = 738.5; 2,418/45 = 53.7; 3.021e-3 | OK (but see M1) |
| 15 LLM build calls | rounds 1×7 + 2 + 3 + 3 = 15 | OK |
| N* ≈ 56; N*_cached ≈ 110 | 0.12586/(2.992e-3×0.7486) = 56.2; /(1.530e-3×0.7486) = 109.9 | Arithmetic OK (framing: B2, M5) |
| Per-assignment range 50% (balanced_brackets 10/20) to 95% (grade_stats 19/20) | matches per_problem | OK |
| Mutants: both variants 94/99 (95%) | generic 94/99, CoEP 94/99 | OK |
| Crafted: generic 17/80 (21%) vs CoEP 40/80 (50%) | matches by_kind | OK |
| McNemar discordant 23:0, p = 2.4e-7 | recomputed: 0:23, p = 2.384e-7; all 23 discordants are crafted | OK |
| Generic-only 62.0 [54.7, 68.8], mean 3.33 s | 111/179 = 62.01; CI and mean match | OK |
| Build-sample success 38/50 → 48/50; 7/10 single-shot 5/5; is_palindrome 0/5→5/5 in round 2 | all confirmed in `build_eval/*.json` | OK (but see M7) |
| 13/179 = 7.3% baseline over-cap; all 13 fall on submissions CoEP escalates | confirmed: over-cap ∩ CoEP-fixed = ∅ | OK |
| Hybrid quality 92.7% | 134 + 32 cap-compliant fallbacks = 166/179 | OK (circular; see M1) |

Numbers that do **not** check out, or are presented misleadingly, are itemized in Parts 2–3.

---

## Part 2 — Blocking findings

### B1 [blocking] Generator–solver circularity: the benchmark was authored by the model under test
The git history shows the entire artifact — including all 100 "misconception-crafted"
buggy programs presented as "realistic novice attempts" — was authored by Claude
(`git log`: sole author `Claude <noreply@anthropic.com>`), the same model family that is
both the per-submission baseline and the CoEP builder. The paper's "contamination-free"
framing addresses training-set leakage of *public datasets*, but silently introduces a worse
problem: every evaluation item is, by construction, in-distribution for the model that must
repair it — the model is grading bugs it (or its sibling) wrote to match a taxonomy it knows.
The 100% baseline repair rate (B3) is the expected symptom. Nothing in the paper discloses
who authored the crafted bugs; the Ethical Statement says only "authored or generated for
this study." "Contamination-free" should be re-scoped to "not memorized verbatim," and the
authorship must be disclosed. Moreover the assignments themselves (fibonacci, gcd,
palindrome…) are the most heavily trained-on programs in existence; only the bug *instances*
are fresh. As written, the external-validity claim ("the price of a contamination-free
comparison") sells a weakness as a strength.

### B2 [blocking] The headline economics are computed against the weakest comparator; against the paper's own zero-cost ablation the story collapses
The generic-only ablation (no LLM, no build cost) fixes 62.0% locally. Wrap it in the same
hybrid fallback and it is a *deployable system with C = $0*: fallback fraction 0.380,
marginal cost 0.380 × 2.99e-3 = **$1.14e-3/sub, breaking even immediately**. CoEP's
marginal cost is $0.75e-3. The break-even of CoEP *against this free competitor* is
N* = C / (c·(f_gen − f_coep)) = 0.12586 / (2.992e-3 × (0.3799 − 0.2514)) ≈ **327
submissions per assignment** (≈640 against a cached fallback) — not 56, and roughly equal
to the ≈340/assignment the paper cites as a realistic ceiling. The asymptotic advantage of
synthesis over the free generic hybrid is 1.5×, not 4.0×. The paper presents the ablation
purely as a mechanism study (RQ3) and never prices it as a baseline, though it is the
obvious incumbent-killer the cost analysis must beat. All RQ2 headline numbers (56, 4.0×)
are baseline-vs-CoEP only. Either add the generic-hybrid row to Tables 1–2 and the
break-even analysis, or drastically soften the economic claims.

### B3 [blocking] Ceiling effect plus visible-test-only oracle: the benchmark cannot support the effectiveness claims
The baseline fixes 179/179. With the effectiveness axis saturated, "the hybrid matches the
baseline's 100% repair rate" is vacuous — *any* local method with LLM fallback matches it,
including one that always returns ⊥. All discriminative content in Table 1 is therefore in
the cost column, which inherits B2. Worse, the only correctness oracle is the same 14
visible tests used (a) in the repair prompt, (b) as CoEP's search objective
(`first_passing` enumerates candidates until the visible suite passes), and (c) as the
evaluation metric. CoEP directly optimizes the metric it is scored on; there is no hidden
test set, so patch overfitting — the classic failure of generate-and-validate APR — is
unmeasured and asymmetric (the baseline cannot execute tests; the local search can, and
does, thousands of times). The RPS cap bounds patch *size*, not semantic correctness. At
minimum: add held-out hidden tests, report semantic-correctness rates for both arms, and
include harder assignments where the baseline is below ceiling.

---

## Part 3 — Major findings

### M1 [major] The fallback arm was never executed; the hybrid row is derived, not measured
`analyze.py` (comment: "reusing the baseline run for those same instances") constructs the
hybrid by copying the baseline's responses for the 45 escalated submissions — confirmed:
fallback usage (33,233 in / 2,418 out) exactly equals the baseline tokens on those 45 keys.
The paper says "Escalated submissions follow the conventional per-submission LLM path,"
implying execution, and RQ1's "exactly matching ... as guaranteed by construction" is
literally circular: the hybrid's 100% rate and 92.7% quality are the baseline's own numbers
re-labeled. Reuse is defensible (identical prompts, single-sample protocol) but must be
disclosed; with a stochastic model, a fresh fallback run would not be guaranteed to
reproduce 45/45 repairs, so "the hybrid never does worse" is an assumption, not a result.

### M2 [major] The LLM-as-harness protocol is unverifiable and under-specified
All "LLM calls" were executed through "an agent harness constrained to behave as a
stateless single-shot endpoint." No model ID, sampling parameters, or API logs are given —
the Reproducibility Checklist's claim that "model version ... [is] stated in Experimental
Setup" is false ("Claude, July 2026 snapshot" is not a model ID; `costmodel.py` says
"Sonnet 5" — the paper never does). The baseline was processed in batches of ~10
same-assignment instances (`runs/baseline/batch_*.txt`, e.g. batch_00 = 10
balanced_brackets bugs); if a batch shared one agent session, later repairs saw earlier
ones — few-shot leakage within the arm and per-query token accounting that no longer
reflects real API usage. Statelessness cannot be audited from the committed artifacts.

### M3 [major] Latency accounting silently zeroes a 60 s timeout
`analyze.py` computes means with `r.get("seconds") or 0`: the gcd `crafted_06` instance hit
the 60 s `repairer_timeout` and has no `seconds` field, so it is averaged in as **0 s**.
True mean = (381.4 + 60)/179 ≈ **2.47 s**, not the reported 2.13 s ("observed mean 2.1 s");
gcd's reported per-problem mean 9.75 s is actually 10.26 s over completed runs (the 9.75
divides by 20 while summing 19). The abstract's "~2 s" also hides that gcd averages ~10 s
and that escalated submissions pay local latency (up to 60 s) *plus* the LLM round trip.
No baseline latency is measured at all, so the implied latency win has no comparator.

### M4 [major] "All cost ratios are tokenizer-independent" is false
This holds only for a *uniform* multiplicative miscount. chars/3.6 error is
content-dependent: the build cost is 86% output-priced code at $15/Mtok, the baseline is
93% input-priced prose+code at $3/Mtok. If code and prose tokenize at different
chars/token (they do, materially), C and c shift by different factors and N* = C/(c(1−f))
moves with them. `summary.json` confirms the fallback heuristic (not tiktoken) was the
active counter. Releasing raw strings mitigates but does not license the blanket claim;
report a sensitivity band or re-tokenize with a real tokenizer.

### M5 [major] The cached baseline is a best-case simulation presented as measurement, and its assumption is applied inconsistently
Abstract/intro: "in our measurements it removes 49% of the per-submission cost." It was
never measured: `analyze.py` *re-prices* the run assuming the prefix is cache-written once
per assignment and read with a 100% hit rate thereafter (5-minute TTL, per `costmodel.py`).
Fine as a favorable bound for the incumbent — but then N*_cached ≈ 110 and "the same
factor over the cached baseline" assume CoEP's *fallback* traffic (25% of volume, hence ≥4×
sparser inter-arrival) enjoys the same 100% hit rate, which the TTL makes doubtful. The
optimism is granted to both sides where it helps the narrative and never stress-tested.

### M6 [major] Independence assumptions of the statistics are violated
Wilson CIs and McNemar treat 179 instances as i.i.d., but they cluster in 10 assignments
(10–20 per cluster), and the 99 mutants are perturbations of only 3 reference solutions per
assignment. Per-assignment local rates range 50–95%, so intra-cluster correlation is
substantial; the reported CIs ([68.0, 80.6] etc.) are anticonservative. Cluster-robust or
assignment-level (n = 10) inference is needed; the crafted-bug McNemar (23:0) survives any
correction, but the CIs as printed do not.

### M7 [major] The refinement narrative is contradicted by the build logs
Claim: "feedback that includes the still-failing submissions (added in round 3) was what
unlocked the two hardest builders." The logs (`runs/coep/build_eval/`) show
unique_in_order went 0/5 → 4/5 in **round 2** and round 3 changed nothing (4/5 → 4/5,
same failing bug); flatten was flat in round 2 (3/5) and gained one in round 3. So round-3
feedback unlocked one builder, not two. Also, the RQ3 box's "turns unreliable single-shot
builders (7/10 usable) into reliable ones (10/10)" overreaches: two final repairers still
fail a build sample (48/50), and "usable/reliable" is never defined.

### M8 [major] Single model, single run, no synthesis variance
Everything rests on one synthesis attempt per assignment by one model with n = 1 sampling.
Builder outcomes are demonstrably high-variance (three of ten first-shot builders were
broken, two producing *no patches at all*); a re-run could plausibly move the 74.9%
headline by many points. The Wilson CI captures bug-sampling variance only, not synthesis
variance, which is the variance that matters for the paradigm claim. No second model
family is tried, so "amortizing LLM reasoning" is demonstrated for exactly one
(model, benchmark) pair. The checklist frames this as "deployment matches one attempt" —
that justifies n = 1 per *submission*, not one build per *assignment*.

### M9 [major] Table 1 (cost anatomy) mislabels its rows; "79%" conflates two different quantities
The 583-token "shared" block is the *cacheable prefix* (preamble + description + tests),
but the prompt places ~99 tokens of byte-identical task instructions *after* the buggy
submission. Those 99 tokens are counted inside the row labeled "Buggy submission (varies)
157 (21%)" — the actually varying content is ≈58 tokens (8%). So: the table's row label is
factually wrong, "79% of prompt tokens are identical across submissions" (abstract) is the
wrong statistic for that sentence (the identical fraction is ≈92%; 79% is the *cacheable*
fraction), and the two should be separated. (Note this error *undersells* the redundancy —
see U1.)

---

## Part 4 — Minor findings

### m1 [minor] Asymptotic figures rounded in CoEP's favor
"4.0×" is 1/f = 3.98 and prices fallback at c = $2.99e-3; measured fallback is $3.02e-3
per escalation, giving 2.992/0.760 = 3.94×, and measured marginal cost is $0.76e-3, not
the tabled $0.75e-3 (analyze.py uses f·c instead of the measured fallback spend). Small,
but every rounding here lands on CoEP's side.

### m2 [minor] "Exactly as minimal ... (mean RPS 0.058 for both)"
Recomputed on the 134 shared instances: CoEP 0.0578, baseline 0.0584. Equal only after
rounding; drop "exactly."

### m3 [minor] "An order of magnitude below the ≈340 buggy submissions"
340/56 ≈ 6.1×. Not an order of magnitude.

### m4 [minor] Prompt fidelity and cap fairness
`render_tests` uses `json.dumps`, so the prompt shows `assert f("()") == true` —
invalid Python — in every test suite both arms see. Separately, the baseline is graded on
RPS ≤ 0.35 but its prompt only says "make the smallest change"; the numeric cap it is
scored against is never communicated, while CoEP enforces it mechanically. The 92.7%
"quality" comparison is thus partly an artifact of information asymmetry.

### m5 [minor] τ = 0.35 is unjustified and un-stress-tested
No sensitivity analysis; one baseline "failure" is at RPS 0.375, barely over. The
crafted-bug quality gap (13 rewrites) and the 92.7% figure move with τ.

### m6 [minor] Total measured spend is never stated plainly
In the experiment as actually run (≈18 eval submissions/assignment), CoEP cost
$1.2586 + $0.1360 = $1.39 vs the baseline's $0.54 — 2.6× *more*. The break-even algebra
implies this, and `summary.json` even records hybrid `usd_per_instance` = 7.79e-3 > 2.99e-3,
but no sentence in the paper says the savings are entirely an extrapolation beyond the
measured regime. Say it.

### m7 [minor] Speculative claim in RQ1 prose
"A property instructors can estimate in advance, and a natural signal for routing" — no
evidence is offered that instructors can predict per-assignment repairability.

### m8 [minor] Build cost heterogeneity hidden by the mean
$0.126/assignment is a mean over builders of 1–3 rounds; 3-round builders (flatten,
unique_in_order) cost several times the 1-round ones, so per-assignment break-even varies
correspondingly. Report the range.

---

## Part 5 — Claims WEAKER than the evidence (legitimate strengthening available)

### U1 [undersold] The redundancy statistic is 92%, not 79%
Fixing M9: the byte-identical share of the baseline prompt is ≈92% (only ≈58 of 740 tokens
vary per submission). The motivating claim in the abstract is understated by 13 points;
report "92% identical, 79% cacheable-prefix."

### U2 [undersold] CoEP-local strictly dominates the generic ablation instance-by-instance
The discordance is 23:0 with zero instances fixed by generic-only but missed by CoEP —
strict dominance, a stronger and cleaner statement than the aggregate rates. (Similarly
available but unused: baseline-quality vs CoEP-local McNemar 32:0, p = 4.7e-10, in
`summary.json`.)

### U3 [undersold] Local latency is far better than "~2 s" for most assignments
Seven of ten assignments have mean local repair time ≤ 2 s, five ≤ 0.5 s (grade_stats and
top_k 0.03 s); the mean is dominated by gcd (~10 s). After fixing M3, report the median
(sub-second) alongside the corrected mean — a stronger operational claim than the current
one.

### U4 [undersold] Zero unsafe outputs from the local path
Across 179 instances the synthesized repairers produced no over-cap patch and no
test-failing "repair" (worst case is ⊥/timeout). The safety property RQ1 argues
qualitatively ("degrades to escalation, never to a wrong repair") is quantitatively
0/179 and worth stating as such.

### U5 [undersold] Aggregate patch minimality
CoEP-local's mean RPS on its repairs (0.058) is under half the baseline's aggregate
(0.127), and the baseline's rewrite tail hits exactly the pedagogically sensitive crafted
bugs (all 13 rewrites are crafted instances). The abstract mentions "patch quality"
parity but not that the local path's successful patches are, in aggregate, twice as small.

### U6 [undersold] The cached-baseline comparison is conservative toward the incumbent
If M5 is fixed by modeling realistic (<100%) cache-hit rates for *both* arms, the cached
baseline's cost rises while CoEP's local 75% is unaffected — CoEP's advantage over a
realistically-cached incumbent is larger than the reported 2×. The authors are entitled to
this point only after making the cache model symmetric.

---

## Summary table of findings

| ID | Severity | One-line |
|----|----------|----------|
| B1 | blocking | Benchmark authored by the model under test; "contamination-free" claim inverted |
| B2 | blocking | Break-even vs the free generic-only hybrid is ≈327 subs (not 56); 1.5× (not 4.0×); comparator omitted |
| B3 | blocking | 100% baseline = ceiling effect; visible-test-only oracle that CoEP directly optimizes; no hidden tests |
| M1 | major | Fallback arm never run; hybrid row reuses baseline responses; "matching" is circular |
| M2 | major | Agent-as-endpoint protocol unverifiable; batched same-assignment prompts; no model ID |
| M3 | major | 60 s timeout counted as 0 s; true mean latency 2.47 s not 2.1 s; no baseline latency |
| M4 | major | "Cost ratios tokenizer-independent" false for content-dependent tokenizer error |
| M5 | major | Cached baseline is best-case simulation labeled "measurement"; cache optimism applied asymmetrically |
| M6 | major | CIs/tests assume i.i.d.; data clustered by assignment and reference solution |
| M7 | major | Round-3 "unlocked two hardest builders" contradicted by build logs (one, and one plateaued at 4/5) |
| M8 | major | One model, one synthesis run; no synthesis variance despite demonstrated builder instability |
| M9 | major | Anatomy table mislabeled; 79% (cacheable) conflated with identical (92%) |
| m1–m8 | minor | Favorable roundings; "exactly"; "order of magnitude"; invalid-Python test rendering; τ untested; totals unstated; speculation; hidden build variance |
| U1–U6 | undersold | 92% redundancy; strict 23:0 dominance; sub-second medians; 0/179 unsafe outputs; 2× smaller patches; conservative cache comparison |
