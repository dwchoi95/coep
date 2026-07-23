```python
def top_k(lst, k):
    result = []
    for x in lst:
        if len(result) < k:
            result.append(x)
        elif result and x > min(result):
            result.remove(min(result))
            result.append(x)
    return sorted(result, reverse=True)
```
