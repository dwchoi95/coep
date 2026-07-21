```python
def remove_extras(lst):
    i = 0
    while i < len(lst):
        for j in lst[0:i]:
            if lst[i] == j:
                del lst[i]
                i -= 1
                break
            else:
                continue
        i += 1
    return lst
    pass
```
