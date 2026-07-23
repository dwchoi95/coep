```python
def remove_extras(lst):
    for i in range(len(lst) - 1, -1, -1):
        if lst.count(lst[i]) > 1:
            del lst[i]
    return lst
```
