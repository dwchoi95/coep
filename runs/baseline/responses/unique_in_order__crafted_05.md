```python
def unique_in_order(lst):
    result = []
    prev = object()
    for x in lst:
        if x != prev:
            result.append(x)
        prev = x
    return result
```
