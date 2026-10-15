# archive/ (dev branch only)

Everything here was produced on the way to the paper's results but is not part
of them. Nothing outside archive/ reads from it, and the scripts in it predate
the current layout (data/, results/v2/, data_dtg/, ...), so they will not run
as they are. The release on main leaves this directory out.

| Path | What it is |
|---|---|
| `results/campaign/<pid>/` | the full summaries of the first campaign, with every arm it ran, MENTORED and BRAFAR included (and their per-submission logs) |
| `results/campaign/{stats,heldout,overall}.csv`, `pool_ablation.json`, `label_sheet.csv` | the campaign's aggregates before CoEP accepted against T⁺ on R1-R5 |
| `results/campaign/threshold_sweep.json` | 29 settings of the escalation threshold (the AAAI paper; its generator is not in the repo) |
| `results/dtg/` | the T⁺ pass on R1-R5, from which results/ was assembled |
| `results/dt/`, `data_dt/` | the same pass with our hand-written generators instead of the builder's (an exploratory comparison) |
| `results/dt_ctrl/` | CoEP on T alone, re-run alongside dt/ under the same machine load |
| `results/direct_claude/`, `direct_gpt/` | LLM_Direct's first query pass, before its candidates were judged on a quiet machine |
| `results/splits_no_amplification/` | the split runs on R1-R5 accepting against T alone, and their report |
| `results/splits_dt_report.csv`, `heldout_pairs_dt_dtg.csv`, `v2_heldout.csv` | reports superseded by results/splits/report.csv, results/heldout_pairs.csv and results/heldout.csv |
| `results/refactory_ours.json` | the authors' shipped Refactory run, re-measured; it reproduces the published R1-R5 rates to 0.05 points |
| `tools_no_amplification/` | the rules the Learn stage kept on R2 when accepting against T alone |
| `splits_eval_staging/` | self-learning staging copies that evaluation runs wrote into the split tools, and the copy of tools/ the "same" arm ran on |
| `baselines/adapters/` | our patches and run scripts for MENTORED and BRAFAR (not reported) |
| `scripts/` | drivers retired with the old layout: `assemble`, `collect_afg` (MENTORED/BRAFAR), `make_package` (the AAAI code-and-data package), `resummarize`, `evaluate`, `figures` |
| `paper_aaai/` | the AAAI submission's author kit, style files, figures, generated tables and supplement |
