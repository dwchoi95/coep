# CoEP: Cost-Effective Program Repair for Programming Assignments

CoEP repairs students' programming assignments by having an LLM synthesize an
**assignment-specific repair tool** once per assignment, instead of a patch for
every submission. Per assignment, a builder LLM:

- turns worked (buggy, reference) pairs into a Python module of
  misconception-named AST rewrite rules, refined against the test cases;
- writes an input generator, whose inputs the class's correct programs label by
  majority vote, which amplifies the instructor's tests T into T⁺.

The frozen tool then repairs each submission locally with no model, using its
rules and a hunk-level transplant from reference programs, and accepts a
candidate only if it passes T⁺. A per-submission query is sent only when the
tool abstains or its patch is larger than the program it repairs.

## Results

The benchmark is 2,970 buggy programs from 11 assignments: R1–R5 from a
first-year course and C1–C6 from Codeforces (ratings 800–2000). RR and RPS pool
the two builders.

- **RR** (repair rate): a repair counts only if the fixed program passes every
  instructor test.
- **RPS** (relative patch size): tree-edit distance from the buggy AST to the
  fixed AST, divided by the size of the buggy AST. Lower is better.
- **Cost**: model spend over the whole benchmark, given as
  `claude-sonnet-5 / gpt-5.4-mini`, one-off build included.

| Arm | RR | RPS | Cost |
|---|---|---|---|
| Refactory (reference-guided) | 85.9% | 0.500 | no model |
| PyDex (10 samples per submission) | 98.9% | 0.634 | $292.77 / $28.42 |
| LLM_Direct (CoEP's fallback query, sent for every submission) | 82.5% | 0.330 | $16.59 / $2.67 |
| **CoEP_L** (frozen tool, no model at repair time) | 98.4% | 0.481 | build only: $12.24 / $0.69 |
| **CoEP_LF** (+ fallback on escalation) | **99.4%** | **0.428** | **$13.74 / $1.04** |

On R1–R5 we also built a held-out suite: 100 tests per assignment that no arm
searched against. On it, CoEP_LF repairs 98.5% / 98.1% of the programs and
PyDex 96.4% / 97.2%. Without amplification, CoEP_LF repairs only 90.2% / 88.0%.

## Layout

| Path | Contents |
|---|---|
| `data/<pid>/` | buggy and correct programs, `problem.json` (description, instructor tests), `reference.py` |
| `data_aug/<pid>/problem.json` | the held-out suites for R1–R5 (instructor tests + 100 held-out tests) |
| `data_dtg/<model>/<pid>/` | CoEP's amplified suite T⁺ (`problem.json`), the builder-written generator (`gen.py`) and its cost |
| `tools/<pid>/<model>/` | the 22 synthesized tools (`fixer.py`, `cost.json`), plus learned rules in `sl/` |
| `tools_dtg/` | the same tools with the learned rules of the T⁺ pass |
| `tools_splits/` | tools built from the first 10/25/50/75% of each class |
| `results/v2/` | the numbers the paper reports (`run.py assemble`): per-submission logs and `summary.csv` per assignment, `stats.csv`, `augmented.csv`, `pool_ablation.json` |
| `results/<pid>/`, `results/dtg/` | the passes `results/v2/` is assembled from: instructor tests only, and T⁺ on R1–R5 |
| `results/splits/`, `results/splits_dt/` | splits by submission order (Codeforces) and seeded order (R1–R5), with `report.csv` |
| `results/heldout_pairs.csv` | per-program held-out verdicts behind the McNemar and Wilcoxon tests |
| `results/rules*.csv`, `labeling_guide.md` | the rule-name study: the sheet and three raters' labels |
| `baselines/pydex/` | our re-implementation of PyDex's few-shot semantic phase |

## Setup

```sh
python3 -m venv .venv && . .venv/bin/activate   # Python 3.13
pip install -r requirements.txt
python run.py augment link      # copy data/'s programs into data_dtg/ (not tracked)
```

API keys (`.env`, see `.env.example`) are needed only to build a tool or to run
an LLM arm.

## Checking the paper's numbers (no API key)

```sh
python run.py stats --ver v2                 # repair rates, Wilson intervals, exact McNemar
python run.py augment pairs --ver v2         # held-out repair rates vs PyDex
python run.py splits make                    # rebuild data_splits/ (deterministic)
python run.py splits report --dt             # generality on R1-R5 -> results/splits_dt/report.csv
python run.py splits report                  # and on Codeforces  -> results/splits/report.csv
```

Each assignment's `results/v2/<pid>/summary.csv` gives RR, RPS, turnaround,
tokens, and cost for every arm and builder, and the per-submission CSVs next to
it give each patch.

## Re-running

The frozen tool alone needs no model:

```sh
python run.py compare --problem refactory_q1 --data-root data_dtg/claude-sonnet-5 \
    --tools-root tools_dtg --ver rerun --model claude-sonnet-5 --no-llm
```

Everything else needs an API key:

```sh
python run.py build --problem <pid> --model <model>             # synthesize a tool
python run.py augment make-search --gen llm --model <model>     # the builder's generator -> T+
python run.py compare --problem <pid> --data-root data_dtg/<model> \
    --tools-root tools_dtg --ver dtg --model <model>             # CoEP_L and CoEP_LF on R1-R5
python run.py compare --problem <cf_pid> --model <model>        # Codeforces (T+ = T)
python run.py direct --problem <pid> --model <model>            # LLM_Direct
python run.py pydex --problem <pid> --model <model>             # PyDex
python run.py assemble                                          # -> results/v2/
```

The rule search and the tests run under wall clocks (3 s per search, 2 s per
test), so run the evaluation on an otherwise idle machine. Ours was a Mac
Studio (Apple M1 Ultra, 20 cores, 64 GB RAM, macOS 26.7).

## Data

- R1–R5 are the introductory-programming corpus released with Refactory.
- C1–C6 are Codeforces submissions mirrored by the open-r1 release.
- Each corpus keeps its own labels.
