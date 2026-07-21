```python
def grade_stats(scores):
    lo = scores[0]
    hi = scores[0]
    total = scores[0]
    for s in scores[1:]:
        if s < lo:
            lo = s
        if s > hi:
            hi = s
        total += s
    return [lo, hi, round(total / len(scores), 2)]
```
