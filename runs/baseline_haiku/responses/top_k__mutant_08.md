```python
def top_k(lst, k):
    temp = list(lst)
    result = []
    while temp and len(result) < k:
        m = temp[1]
        for v in temp:
            if v >= m:
                m = v
        temp.remove(m)
        result.append(m)
    return result
```
