```python
def remove_extras(lst):
    if not lst:
        return []
    seq = (lst[0],)
    for i in lst:
        if i not in seq:
            seq = seq + (i,)
    return list(seq)
```
