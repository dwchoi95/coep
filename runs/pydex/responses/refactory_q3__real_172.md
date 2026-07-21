```python
def remove_extras(lst):
    i = 0
    while i < len(lst):
        j = i + 1
        while j < len(lst):
            if lst[i] == lst[j]:
                del lst[j]
            else:
                j += 1
        i += 1
    return lst
```
