```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) < k:
        m = max(temp)
        temp.remove(m)
        result.append(m)
    result.sort(reverse=True)
    return result
```
