```python
def top_k(lst, k):
    sort = []
    while lst:
        big = max(lst)
        sort.append(big)
        lst.remove(big)

    output = [n for i, n in enumerate(sort) if i < k]
    return output
```
