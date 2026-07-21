```python
def flatten(nested):
    result = []
    i = 0
    while i < len(nested):
        item = nested[i]
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
        i += 1
    return result
```
