```python
def grade_stats(scores):
    first = min(scores)
    last = max(scores)
    mean = round(sum(scores) / len(scores), 2)
    return [first, last, mean]
```
