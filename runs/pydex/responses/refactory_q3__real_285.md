```python
def remove_extras(lst):
    lst2 = []
    for x in lst:
        if lst2.count(x) < 1:
            lst2.append(x)
    return lst2
```
