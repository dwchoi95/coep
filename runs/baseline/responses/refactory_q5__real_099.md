```python
def top_k(lst, k):
    l = []
    if k > len(lst):
        return False
    elif k == 0:
        return l
    else:
        a = max(lst)
        lst.remove(a)
        l.append(a)
        return l + top_k(lst, k-1)
```
