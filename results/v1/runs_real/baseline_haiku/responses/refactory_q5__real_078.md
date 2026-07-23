```python
def top_k(lst, k):
    sort = []
    while lst:
        big = max(lst)
        sort.append(big)
        lst.remove(big)
    return sort[:k]
```
