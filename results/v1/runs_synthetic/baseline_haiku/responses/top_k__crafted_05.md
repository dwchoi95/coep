```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    for _ in range(min(k, len(temp))):
        m = max(temp)
        temp.remove(m)
        result.append(m)
    return result
```
