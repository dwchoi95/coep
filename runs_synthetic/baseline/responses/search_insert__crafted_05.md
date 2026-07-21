```python
def search_insert(lst, x):
    i = 0
    for v in lst:
        if v >= x:
            return i
        i += 1
    return len(lst)
```
