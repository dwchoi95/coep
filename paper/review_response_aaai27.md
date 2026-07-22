# AAAI-27 Review Response Log (round 2, real-data draft)

Both reviewers scored the restructured draft 5/10 (confidence 4). Per project
policy every actionable weakness was answered by **adding evidence or fixing
the text**, never by narrowing claims. Verbatim reviews:
`review_aaai27_r1.md`, `review_aaai27_r2.md`.

## Experiments added in response

**W (both): "Hybrid-vs-baseline comparison is enforcement-asymmetric /
structurally one-sided; PyDex's real protocol retries."**
→ Ran the **enforcement-parity arm**: frontier baseline + the same size
validator + one minimality-feedback retry on each of its 28 cap-busting
patches (`scripts/retry_arm.py`, `runs/baseline_retry/`).
Result: 25/28 retries recovered → 98.5% quality at $3.26e-3/submission.
Composing the *same* protocol as CoEP's fallback repairs the **identical
197/200** (discordant 0:0, per-assignment identical) at $1.78e-3 —
1.8× lower slope, break-even ≈173 submissions. Added to Table 2 (two rows),
RQ2 prose/box, intro, conclusion, and internal-validity discussion (the
one-sidedness of hybrid-vs-baseline tests is now stated explicitly, with the
parity arm as the symmetric comparison).

**W (R2): "90.5 vs 88.5 dominant-configuration claim untested."**
→ Computed exact McNemars: CoEP+cascade vs baseline 9:0, p=0.0039
(significant); vs cascade alone 4:0, p=0.125 → paper now claims superiority
only vs baseline, and "same quality at 1.8× lower marginal cost" vs cascade
with the discordant count reported as directional (n.s.).

**W (R2): "Clustered data treated as 200 iid samples."**
→ Metrics section now states submission-level tests come with per-assignment
directions; RQ1 reports the direction holds in all five assignments (+0..+4);
external validity notes the subsampling design.

**W (R2): "Cached baseline unimplementable below provider's 1,024-token
cacheable minimum."**
→ Verified: plain prompts are 439 tokens → caching cannot engage at all.
Reframed everywhere: the cached row is labeled a *no-minimum lower bound*;
caching *does* engage on the 1,705-token PyDex-style prompt (6.53→2.91e-3,
new table row) — redundancy is real but provider caching serves it at the
wrong granularity. This *strengthens* the anatomy argument.

**W (R1): "Refactory tool scores 90.5 here vs ~97 published — unexplained."**
→ Added: the tool's own oracle reports 91.0% on these exact runs (within one
point of our 90.5% test-pass), so re-validation is not hostile; the published
figure is on the full corpus with the original suites; the *quality* gap is
entirely patch size (its test-passing repairs average 0.386 RPS).

## Factual/wording corrections

- "Smallest patches of any arm" — **withdrawn** (R1/R2 correct): on the 87
  shared instances frontier accepted patches are smaller (0.093 vs 0.115).
  Rewritten: the local path's advantage is *enforcement* (zero unsafe
  outputs), not average patch size.
- "Most submissions never touch a model" (Fig. 1) → "half".
- "Milliseconds" → "under a second on average" (mean 0.85 s).
- "Exact token accounting" → "uniform token counts from the raw strings"
  (chars/3.6, released for exact re-tokenization) in all four places.
- "More than doubles the tool's 56.0%" → "clears it by 34 points".
- RQ2 now states explicitly that hybrid cost remains linear in enrollment
  (smaller slope + intercept, not zero marginal).
- Cost-anatomy table inlined to prose (page budget); content+ethics fit in
  exactly 7 pages, references on 8–9, checklist on 10; 0 errors/overfulls.

## Deliberately not adopted

- R1's suggestion that the frontier baseline's saturated test-pass rate makes
  the comparison uninformative: quality repair rate (the shared discipline)
  is the primary metric precisely because functional repair saturates; both
  reviews accept the metric itself.
- Dropping the 5-assignment corpus for a larger synthetic one: contradicts
  the (user-mandated) real-data design; instead uncertainty is quantified and
  the corpus's own per-offering volumes anchor the economics.

## Round 3 (post-revision fresh reviews)

**Scores: R1 7/10 (accept, conf 4); R2 7/10 (accept, conf 4).**
R2 independently recomputed all Wilson CIs, McNemar p-values, and the
cost/break-even arithmetic — all verified. Camera-ready items completed
immediately:

- **tau-sweep** (`scripts/tau_sweep.py`, Fig. tau): orderings stable across
  tau in [0.15, 0.50]; retry arm dominates everywhere; tool collapse at every
  threshold; CoEP curves conservative below 0.35 (frozen cap).
- **Full-corpus local eval** (`scripts/full_corpus_eval.py`): 841/1,660 =
  50.7% [48.3, 53.1] local coverage (per-assignment 27.9-71.4%), confirming
  the subsample estimate with a +-2.4pp interval; full-corpus hybrid slope
  1.35e-3.
- **Claim scoping**: "exceeds every per-submission configuration" -> "every
  deployed single-shot configuration"; "study's lowest marginal cost" ->
  "lowest among quality-competitive arms (only the 65%-quality Haiku arm is
  cheaper)".
- **Numeric consistency**: prompt decomposition fixed to 241+99+99=439 (77%
  identical); 0.8s unified via macro; 1.8-2.5x range unified; calibration
  wording aligned with Protocol; tie-vs-direction wording fixed ("never
  reversed; strictly better in three, tied in two").
- Redundant per-problem bar chart removed; content + ethics fit exactly 7pp.

Remaining camera-ready suggestions not blocking acceptance (multi-seed
builder replication, hidden-test control, amortize-into-prompt middle point,
k-sweep) are acknowledged in Discussion as priced extensions.
