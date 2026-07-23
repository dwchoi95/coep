```python
def remove_extras(lst):
    i = 0
    while i < len(lst):
        for j in range(i):
            if lst[i] == lst[j]:
                lst.pop(i)
                break
        else:
            i += 1
    return lst
```
