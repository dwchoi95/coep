```python
def top_k(lst, k):
    new = []
    while len(new) < k:
        top = max(lst)
        new.append(top)
        lst.remove(top)
    return new
```
