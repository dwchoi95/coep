```python
def remove_extras(lst):
    # your code here
    for item in lst:
        while lst.count(item) != 1:
            lst.pop(lst.index(item, 1))
    return lst
```
