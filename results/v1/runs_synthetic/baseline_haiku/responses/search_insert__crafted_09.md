```python
def search_insert(lst, x):
    i = 0
    while i < len(lst) and lst[i] < x:
        i += 1
    return i
```
