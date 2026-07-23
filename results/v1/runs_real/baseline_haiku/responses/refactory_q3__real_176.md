```python
def remove_extras(lst):
    i = 0
    while i < len(lst)-1:
        if lst[i] in lst[i+1:]:
            lst.pop(i)
        else:
            i += 1
    return lst
```
