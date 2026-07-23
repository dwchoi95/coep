```python
def flatten(nested):
    result = []
    stack = list(nested)
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        else:
            result.append(item)
    result.reverse()
    return result
```
