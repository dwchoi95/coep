```python
def remove_extras(lst):
    for i in range(len(lst)-1, -1, -1):
        for j in range(i):
            if lst[i] == lst[j]:
                lst.pop(i)
                break
    return lst
```
