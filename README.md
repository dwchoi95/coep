# CoEP: Cost-Effective Program Repair for Programming Assignments

CoEP repairs students' programming assignments by having an LLM synthesize an
**assignment-specific repair tool** once per assignment, instead of a patch for
every submission. Per assignment, a builder LLM does two things:

- It turns worked (buggy, reference) pairs into a Python module of
  misconception-named AST rewrite rules, refined against the test cases.
- It writes an input generator. The class's correct programs label the
  generator's inputs by majority vote, which amplifies the instructor's tests
  T into T⁺.

The frozen tool then repairs each submission locally, with no model, using its
rules and a hunk-level transplant from reference programs. It accepts a
candidate only if it passes T⁺. A per-submission query goes to the model only
when the tool abstains or when its patch is larger than the program it repairs.

## Results

The benchmark has 2,970 buggy programs from 11 assignments:

- **R1–R5:** a first-year course.
- **C1–C6:** Codeforces problems, rated 800–2000.

The columns are:

- **RR** (repair rate): a repair counts only if the fixed program passes every
  instructor test.
- **RPS** (relative patch size): the tree-edit distance from the buggy AST to
  the fixed one, divided by the size of the buggy AST. Lower is better.
- **Cost**: model spend over the whole benchmark for each builder
  (`claude-sonnet-5 / gpt-5.4-mini`), including the one-off build.

RR and RPS are pooled over the two builders.

| Arm | RR | RPS | Cost |
|---|---|---|---|
| Refactory (reference-guided) | 85.9% | 0.500 | no model |
| PyDex (10 samples per submission) | 98.9% | 0.634 | $292.77 / $28.42 |
| LLM_Direct (CoEP's fallback query, for every submission) | 82.5% | 0.330 | $16.59 / $2.67 |
| **CoEP_L** (frozen tool, no model at repair time) | 98.4% | 0.481 | build only: $12.24 / $0.69 |
| **CoEP_LF** (+ fallback on escalation) | **99.4%** | **0.428** | **$13.74 / $1.04** |

We also built a held-out suite for R1–R5: 100 tests per assignment that no arm
searched against. Results on it, per builder (`claude-sonnet-5 / gpt-5.4-mini`):

| Arm | Held-out RR |
|---|---|
| **CoEP_LF** | **98.5% / 98.1%** |
| PyDex | 96.4% / 97.2% |
| CoEP_LF without amplification | 90.2% / 88.0% |

## Layout

| Path | Contents |
|---|---|
| `benchmark/<pid>/` | the assignment: `buggy/`, `correct/`, `reference.py`, and `problem.json` (description and instructor tests T) |
| `benchmark/<pid>/heldout.json` | R1–R5: the 100 held-out tests |
| `benchmark/<pid>/amplified/<model>/` | R1–R5: the builder's input generator (`generator.py`), the amplified tests it yields (`tests.json`), and the builder call's cost |
| `tools/<pid>/<model>/` | the 22 synthesized tools (`fixer.py`, `cost.json`) and the rules their Learn stage kept (`sl/`) |
| `tools/splits/<scheme>/<f>/` | tools built from the first f of each class |
| `results/<pid>/` | per-submission logs for every arm (one CSV per arm) and `summary.csv` (RR, RPS, turnaround, tokens, cost) |
| `results/<pid>/no_amplification/` | R1–R5: CoEP and LLM_Direct accepting against T alone |
| `results/stats.csv`, `heldout.csv`, `heldout_pairs.csv`, `pool_ablation.json` | the statistical tests, the held-out verdicts, and the Synthesize ablation |
| `results/splits/` | the split runs and `report.csv` |
| `results/label_study/` | the rule-name study: the sheet, three raters' labels, and the labeling guide |
| `src/core/`, `src/runner/`, `src/prompts/`, `src/utils/` | CoEP itself |
| `src/experiments/` | one driver per experiment, dispatched by `run.py` |
| `baselines/pydex/` | our re-implementation of PyDex's few-shot semantic phase |

## Setup

```sh
python3 -m venv .venv && . .venv/bin/activate   # Python 3.13
pip install -r requirements.txt
```

API keys go in `.env` (see `.env.example`). You need them only to build a tool
or to run an LLM arm.

## Checking the paper's numbers (no API key)

```sh
python run.py stats              # repair rates, Wilson intervals, exact McNemar -> results/stats.csv
python run.py augment check      # every arm's repairs on the held-out suite -> results/heldout.csv
python run.py augment pairs      # held-out McNemar and patch-size Wilcoxon vs PyDex
python run.py splits make        # rebuild the splits (deterministic, into splits_work/)
python run.py splits report      # generality -> results/splits/report.csv
python run.py labelagree         # the rule-name study
python run.py augment amplify --model claude-sonnet-5   # relabel T_amp from the stored generator
```

## Re-running

The frozen tool alone needs no model:

```sh
python run.py compare --problem refactory_q1 --model claude-sonnet-5 --amplified \
    --no-llm --ver rerun          # -> results/rerun/refactory_q1/
```

Everything else needs an API key:

```sh
python run.py build   --problem <pid> --model <model>                 # synthesize a tool
python run.py augment amplify --model <model> --regenerate            # a new generator -> T+
python run.py compare --problem <pid> --model <model> --amplified     # CoEP_L and CoEP_LF
python run.py compare --problem <pid> --model <model> --amplified --framework-only   # -Syn
python run.py direct  --problem <pid> --model <model> --amplified     # LLM_Direct
python run.py pydex   --problem <pid> --model <model>                 # PyDex
python run.py pool --amplified --out results/pool_ablation.json       # Synthesize ablation
python run.py splits jobs --phase build                               # then --phase eval
```

`--amplified` has no effect on C1–C6, where T⁺ = T because their suites are
Codeforces' full official tests.

The rule search and the tests run under wall clocks (3 s per search, 2 s per
test), so run the evaluation on an otherwise idle machine. Ours was a Mac
Studio (Apple M1 Ultra, 20 cores, 64 GB RAM, macOS 26.7).

## Data

- **R1–R5:** the introductory-programming corpus released with Refactory.
- **C1–C6:** Codeforces submissions mirrored by the open-r1 release.

Each corpus keeps its own buggy/correct labels.
