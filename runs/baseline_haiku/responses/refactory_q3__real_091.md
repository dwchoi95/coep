```python
def remove_extras(lst):
    result = []
    for item in lst:
        if item not in result:
            result.append(item)
    return result
```
