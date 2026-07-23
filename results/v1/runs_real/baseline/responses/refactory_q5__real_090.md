```python
def top_k(lst, k):
    sort = []
    while lst:
        big = max(lst)
        sort.append(big)
        lst.remove(big)
    
    output = [n for n in sort if sort.index(n) < k]
    return output
```
