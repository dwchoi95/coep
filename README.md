# CoEP: Use LLMs to Build Repair Tools, Not Patch Generation

Automated program repair for programming assignments in which **the model
writes the repair tool, not the patch**. Once per assignment a builder LLM
turns worked (buggy, reference) pairs into a Python module of
misconception-named AST rewrite rules; the frozen module then repairs
submissions locally with no model at all, and only what it abstains on takes a
conventional per-submission call.

Paper: `paper/main.pdf` (AAAI format, anonymized).

## Results

11 assignments, 2,970 buggy programs, both builders pooled. **RR** is the
repair rate, counting a repair only when the fixed program passes every test.
**RPS** is relative patch size, the tree-edit distance from the buggy to the
fixed AST normalized by buggy program size; lower is better.

| Arm | RR | RPS | cost over the benchmark |
|---|---|---|---|
| Refactory (reference-guided) | 85.93% | 0.500 | no model |
| PyDex (one LLM call per submission) | 98.94% | 0.634 | $292.77 / $28.42 |
| **CoEP_L** (frozen tool, no model at repair time) | **99.06%** | **0.463** | build only |
| **CoEP_LF** (+ fallback on abstentions and oversized patches) | **99.70%** | **0.410** | **$13.58 / $1.00** |

Costs are `claude-sonnet-5 / gpt-5.4-mini` and include the one-off build. An
assignment repays that build after 11 submissions against PyDex.

## Layout

```
src/core/          build-set selection, tool synthesis, the rule search,
                   reference transplant, escalation, self-learning
src/experiments/   one driver per stage, all reachable through run.py
src/prompts/       every prompt sent to a model, as Markdown
src/runner/        sandboxed test execution
data/<problem>/    buggy/, correct/, problem.json (tests + description)
tools/<problem>/<model>/     the synthesized repairer: fixer.py, cost.json,
                             and sl/learned.py for the self-learned rules
results/v2/        one row per (submission, arm, model), plus the summaries
                   built from those rows; everything the paper reports
paper/             main.tex, references.bib, generated tables and figures
```

## Recomputing the paper

Nothing below touches a model. Every number the paper reports is derived from
the committed logs in `results/v2/`:

```bash
pip install -r requirements.txt

python run.py tables      # splice the generated tables into paper/main.tex
python run.py figures     # regenerate paper/figures/*.pdf
python run.py numbers     # recompute each quantity and report whether that
                          # exact string still occurs in main.tex
python run.py stats       # Wilson intervals and exact McNemar over the logs
```

## Running the pipeline

```bash
cp .env.example .env      # provider keys; .env is gitignored

python run.py build   --problem refactory_q1     # synthesize the tool
python run.py compare --problem refactory_q1     # CoEP_L and CoEP_LF
python run.py pydex   --problem refactory_q1     # the per-submission baseline
python run.py repair  --problem refactory_q1 --file bug.py    # one submission
```

`run.py --list` prints every driver. `src/experiments/v1/` is the previous
campaign's code, kept runnable against `results/v1/` and not used by anything
current.

## Notes on the measurements

- **Refactory.** Its CS1 rows are the authors' published per-assignment
  figures; its Codeforces rows are our run of the released tool. The upstream
  tree under `baselines/refactory/` is gitignored apart from our wrapper, since
  it carries 36 MB of the authors' own data.
- **Already-passing submissions.** Both corpora label a few submissions buggy
  that pass every test. They are repair targets like any other and enter the
  search unshortcut, so the denominator is the pool as published and is
  identical across arms.
- **Held-out view.** The builder sees worked pairs drawn from the same buggy
  programs it is later measured on, 1,524 of the 2,970. Every result is also
  reported on the 1,446 submissions no builder ever saw.
- **Two builders.** Effectiveness is pooled over `claude-sonnet-5` and
  `gpt-5.4-mini`; cost is never pooled, since the two price schedules differ by
  an order of magnitude.
