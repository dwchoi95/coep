```python
def remove_extras(lst):
    if not lst:
        return []
    result = (lst[0],)
    for e in lst:
        if e not in result:
            result += (e,)
        else:
            continue
    return list(result)
```
