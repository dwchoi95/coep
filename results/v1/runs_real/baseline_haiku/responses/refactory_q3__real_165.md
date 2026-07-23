```python
def remove_extras(lst):
    i = 0
    while i < len(lst):
        if lst[i] in lst[:i]:
            lst.remove(lst[i])
        else:
            i = i + 1
    return lst
```
