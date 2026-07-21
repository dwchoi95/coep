```python
def remove_extras(lst):
    i = 0
    while i < len(lst):
        found = False
        for j in lst[0:i]:
            if lst[i] == j:
                found = True
            else:
                continue
        if found:
            del lst[i]
        else:
            i += 1
    return lst
```
