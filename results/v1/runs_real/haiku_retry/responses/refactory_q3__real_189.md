```python
def remove_extras(lst):
    seen = set()
    i = 0
    while i < len(lst):
        if lst[i] in seen:
            lst.pop(i)
        else:
            seen.add(lst[i])
            i += 1
    return lst
```
