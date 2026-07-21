# CoEP: Synthesize Once, Repair Many

Cost-effective automated program repair (APR) for programming assignments by
**per-assignment repairer synthesis**: an LLM agent writes, once per
assignment, a local rule/template-based repair program; student submissions
are then repaired locally at zero marginal LLM cost, with per-submission LLM
repair as fallback.

Paper: `paper/main.pdf` (AAAI-format draft; anonymized).

## Headline results (10 assignments, 229 buggy programs, 179 held-out)

| | Repair rate | RPS ≤ 0.35 | build $/assign. | marginal $/submission |
|---|---|---|---|---|
| Frontier per-submission | 100.0% | 92.7% | 0 | $2.99×10⁻³ |
| + provider prompt caching | 100.0% | 92.7% | 0 | $1.53×10⁻³ |
| Cheap-model (Haiku) per-subm. | 97.2% | 86.6% | 0 | $0.99×10⁻³ |
| Cascade (cheap→frontier) | 100.0% | 88.3% | 0 | $1.09×10⁻³ |
| Generic-only local | 62.0% | 62.0% | 0 | 0 |
| Generic-hybrid | 100.0% | 92.7% | 0 | $1.13×10⁻³ |
| **CoEP-local** | **74.9%** | 74.9% | $0.126 | **0** |
| **CoEP + frontier fallback** | **100.0%** | 92.7% | $0.126 | $0.76×10⁻³ |
| **CoEP + cascade fallback** | **100.0%** | 91.6% | $0.126 | **$0.29×10⁻³** |

Break-evens: ≈56 submissions vs. the frontier baseline; ≈342 vs. the strongest
zero-build competitor (generic-hybrid); ≈159 for CoEP+cascade vs. the cascade.
Asymptotic marginal-cost reduction 4.0× (10.2× with cascade fallback). On
misconception-crafted bugs, synthesized problem-specific rules lift local repair
from 21% (generic edit search) to 50% (p<10⁻⁶); a Haiku-tier builder reaches
51.4% local at $0.011/assignment build cost.

## Repository layout

```
coep/                 harness library
  sandbox.py          sandboxed / in-process test runners
  mutation.py         AST mutation engine (benchmark generation + repair operators)
  repairlib.py        repair-operator library used by synthesized repairers
  prompts.py          baseline + builder + refinement prompt construction
  evaluate.py         RPS (token-level relative patch size)
  costmodel.py        token/dollar accounting (Sonnet-tier pricing + caching)
benchmark/problems/<id>/
  problem.json        description + entry + 14 tests
  refs/               3 reference solutions
  buggy/              crafted_XX.py (misconception bugs) + mutant_XX.py
  repairer.py         the synthesized repairer (final round)
benchmark/splits.json build/eval split (seeded)
runs/
  baseline/           per-instance prompts, raw LLM responses, results.json
  baseline_haiku/     cheap-model arm (same prompts, Haiku-tier responses)
  coep/               builder prompts/responses per round, build/eval results
  coep_haiku/         Haiku-tier builder arm (robustness experiment)
  ablation_generic/   generic-only ablation results
  summary.json        aggregated metrics + statistics
scripts/              orchestration: make_dataset, gen_baseline_prompts,
                      collect_baseline, coep_build, ablation_generic, analyze,
                      validate_benchmark
paper/                AAAI LaTeX sources, figures, references, reviews
```

## Reproducing

```bash
pip install matplotlib numpy
python3 scripts/validate_benchmark.py            # refs pass, bugs fail
python3 scripts/make_dataset.py                  # mutants + splits (seeded)
python3 scripts/gen_baseline_prompts.py          # per-instance prompts
# ... run an LLM over runs/baseline/prompts/ -> runs/baseline/responses/ ...
python3 scripts/collect_baseline.py
python3 scripts/coep_build.py prompt  <pid>      # builder prompt (round k)
# ... run an LLM over the prompt -> runs/coep/responses/<pid>_round<k>.md ...
python3 scripts/coep_build.py install <pid>      # install + build-set eval
python3 scripts/coep_build.py evalfinal <pid>    # held-out evaluation
python3 scripts/ablation_generic.py
python3 scripts/analyze.py                       # summary + figures + numbers.tex
```

All raw prompts and model responses used in the paper are committed under
`runs/`, so every number is recomputable without any LLM access.

## Protocol notes

- Both paradigms use the same frontier model; every LLM interaction is a
  single-shot prompt→response exchange with no tool use or test access.
- Patches are always re-validated independently (sandboxed test run + RPS cap
  τ=0.35); a repairer cannot self-report success.
- Token counts use a fixed approximation (chars/3.6) applied identically to
  both arms; raw strings are included for exact re-tokenization.
