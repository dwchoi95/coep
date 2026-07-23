```python
def remove_extras(lst):
    i = 1
    n = len(lst)
    while i < n:
        if lst[i] in lst[:i]:
            lst.pop(i)
        else:
            i += 1
        n = len(lst)
    return lst
    pass
```
