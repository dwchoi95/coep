```python
def grade_stats(scores):
    highest = max(scores)
    lowest = min(scores)
    mean = round(sum(scores) / len(scores), 2)
    return [lowest, highest, mean]
```
