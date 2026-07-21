```python
def flatten(nested):
    result = []
    stack = list(nested)
    while stack:
        item = stack.pop(0)
        if isinstance(item, list):
            stack = item + stack
        else:
            result.append(item)
    return result
```
