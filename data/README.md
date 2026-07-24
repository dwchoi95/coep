# Dataset

11 problems, ~2,970 buggy programs, spanning two corpora and two execution modes.

## Codeforces (6 problems, mode=stdio)

From `open-r1/codeforces` (verifiable subset) + `open-r1/codeforces-submissions`,
real Python 3 student submissions. Filters: verifiable subset, Python 3,
`WA>=1 & AC>=1`, `official_tests_complete=True` (no truncated test), no
`generated_checker` (single valid output). One representative per Codeforces
rating band (blog/entry/68288 boundaries), chosen by most WRONG_ANSWER
submissions. Every WA/AC program was executed against the FULL official test
suite; false-positive counts are recorded in `_cf_verify.json`.

| problem | band          | rating | buggy | correct | tests | FP (buggy/correct) |
|---------|---------------|-------:|------:|--------:|------:|:------------------:|
| 110/A   | Newbie        |  800   | 440   | 353     | 34    | 0/0  |
| 131/A   | Pupil         | 1000   | 560   | 140     | 56    | 0/0  |
| 1011/B  | Apprentice    | 1200   | 69    | 164     | 31    | 0/2  |
| 125/A   | Specialist    | 1400   | 38    | 37      | 22    | 1/0  |
| 11/B    | Expert        | 1600   | 77    | 2       | 30    | 0/0  |
| 10/C    | Master        | 2000   | 3     | 2       | 40    | 0/0  |

`buggy/` = WRONG_ANSWER submissions; `correct/` = OK submissions (reference pool).

## Refactory (5 problems, mode=call)

From Hu et al., ASE 2019: real NUS CS1 submissions. `buggy/` = wrong, `correct/`
= correct student programs, `reference.py` = instructor solution.

| problem      | entry               | buggy | correct | tests |
|--------------|---------------------|------:|--------:|------:|
| refactory_q1 | search              | 575   | 768     | 11    |
| refactory_q2 | unique_day (+2)     | 435   | 291     | 9     |
| refactory_q3 | remove_extras       | 308   | 546     | 6     |
| refactory_q4 | sort_age            | 357   | 419     | 6     |
| refactory_q5 | top_k               | 108   | 418     | 5     |

## Schema

`data/<pid>/problem.json`: `{pid, source, mode, description, tests, ...}`.
- mode=stdio: tests are `{stdin, expected}`.
- mode=call:  tests are `{args, expected[, entry]}`; `entry` names the callee.

Import scripts: `data/_import/{codeforces,refactory}.py`. Audit: `data/_import/audit.py`
(writes `_manifest.json`). LSGen/PyDex importers are retained but their corpora
are not part of the final dataset (see PLAN.md).
