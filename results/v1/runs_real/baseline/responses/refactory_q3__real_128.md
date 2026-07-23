```python
def remove_extras(lst):
    i = -1
    while i >= (-len(lst)):
        if lst[i] in lst[:i]:
            lst.pop(i)
        else:
            i = i - 1
    return lst
```
