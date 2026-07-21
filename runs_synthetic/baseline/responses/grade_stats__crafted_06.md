```python
def grade_stats(scores):
    total = 0
    for s in scores:
        total += s
    mean = round(total / len(scores), 2)
    return [min(scores), max(scores), mean]
```
