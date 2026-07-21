```python
def grade_stats(scores):
    lowest = min(scores)
    highest = max(scores)
    mean = round(sum(scores) / len(scores), 2)
    return [lowest, highest, mean]
```
