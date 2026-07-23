```python
def top_k(lst, k):
    l = []
    if k > len(lst):
        k = len(lst)
    if k == 0:
        return l
    a = max(lst)
    lst.remove(a)
    l.append(a)
    l.extend(top_k(lst, k-1))
    return l
```
