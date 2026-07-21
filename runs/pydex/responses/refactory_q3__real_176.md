```python
def remove_extras(lst):
    i = 0
    while i < len(lst):
        if lst[i] in lst[i+1:]:
            lst.pop(i + 1 + lst[i+1:].index(lst[i]))
        else:
            i += 1
    return lst
```
