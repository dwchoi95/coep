```python
def remove_extras(lst):
    for i in range(len(lst)-1, 0, -1):
        if lst[i] in lst[:i]:
            lst.pop(i)
    return lst
```
