```python
def top_k(lst, k):
    l = []
    if k > len(lst):
        return False
    else:
        while len(l) < k:
            a = max(lst)
            lst.remove(a)
            l.append(a)

        return l
```
