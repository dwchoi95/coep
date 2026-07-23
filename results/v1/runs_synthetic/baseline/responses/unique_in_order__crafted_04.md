```python
def unique_in_order(lst):
    lst = list(lst)
    i = 0
    while i < len(lst) - 1:
        if lst[i] == lst[i + 1]:
            lst.pop(i)
        else:
            i += 1
    return lst
```
