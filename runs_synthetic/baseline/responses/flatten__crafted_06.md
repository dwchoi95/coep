```python
def flatten(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            result += flatten(item)
        else:
            result += [item]
    return result
```
