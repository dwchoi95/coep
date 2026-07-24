# PyDex baseline (reproduction)

Faithful reproduction of the **semantic phase** of PyDex (Zhang et al.,
OOPSLA 2024), driven by our own models so ATT/InT/OuT/$API are measured
identically to CoEP.

- **Prompt**: the multimodal zero-shot prompt of Fig. 6, laid out exactly as in
  the paper (buggy program first, then description, then tests, then
  `### Correct Program ###`); the few-shot prompt of Fig. 7 with
  failure-vector (1 - normalized Hamming) retrieval of the 3 most similar
  (p, p') pairs activates automatically when a `data/<pid>/pairs.json`
  example bank exists (our corpora carry no per-student edit histories, so the
  operative arm is zero-shot - the paper's own competitive ablation).
- **K candidates**: each prompt yields K=10 sampled candidates (default
  provider temperature), every call billed and timed regardless of outcome.
- **Oracle + selection**: candidates run on the full suite; any failure
  discards the candidate; the minimum token-edit-distance survivor is the
  repair. No iterative refinement exists in the semantic phase.

Driver: `python3 run.py pydex --problem <pid> --model {claude-haiku,gpt-nano}`
writes `results/<ver>/<pid>/{pydex,pydex_pc}.csv` + summary rows.
