```python
def remove_extras(lst):
    new = []
    for i in lst:
        if new.count(i) == 0:
            new += [i]
    return new
```
