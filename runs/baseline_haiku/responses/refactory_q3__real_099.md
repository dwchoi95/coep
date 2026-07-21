```python
def remove_extras(lst):
    for item in lst:
        while lst.count(item) != 1:
            lst.remove(item)
    return lst
```
