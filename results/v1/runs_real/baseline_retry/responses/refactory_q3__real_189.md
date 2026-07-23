```python
def remove_extras(lst):
    for i in lst:
        while lst.count(i) > 1:
            lst.reverse()
            lst.remove(i)
            lst.reverse()
    return lst
```
