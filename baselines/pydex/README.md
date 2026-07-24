# PyDex baseline (reproduction)

Reproduces the **PyDex** repair pipeline as a per-submission LLM baseline, driven
by our own model so model choice is not a confound and ATT/InT/OuT/Cost are
measured identically to CoEP.

> Zhang et al. *PyDex: Repairing Bugs in Introductory Python Assignments using
> LLMs.* OOPSLA 2024.

We reproduce the **algorithm**, not the original Codex sampling setup:

- **Multi-modal prompt** (`repair.md`): problem description + buggy program +
  execution feedback (failing-test input/expected/got, or the interpreter error).
- **Multi-sample generation + test-based selection**: sample candidates, execute
  all, take any that pass the full suite (ties → smallest edit / RPS), else carry
  the best partial forward.
- **Iterative refinement ("chaining")**: feed the surviving failures back and
  re-query, up to a round budget.

Our cheapest models (`claude-haiku-4-5`, `gpt-5.4-nano`) expose only the default
temperature, so with `samples=1` diversity comes from the feedback loop rather
than temperature sampling; `samples>1` issues independent calls.

## Use

```python
from baselines.pydex.pydex import repair
res = repair(buggy_src, problem, model="claude-haiku", rounds=4, samples=1)
# res.repaired, res.patch, res.calls, res.in_tokens, res.out_tokens, res.usd, res.seconds
```

`problem` is the unified `data/<p_id>/problem.json` schema. Cost and latency are
accumulated across every call so the arm is directly comparable to CoEP's
fallback and to Refactory.
