```python
def unique_in_order(lst):
    result = []
    for x in lst:
        if not result or x != result[-1]:
            result.append(x)
    return result
```
