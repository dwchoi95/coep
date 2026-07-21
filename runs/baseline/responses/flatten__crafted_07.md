```python
def flatten(nested, result=None):
    if result is None:
        result = []
    for item in nested:
        if isinstance(item, list):
            flatten(item, result)
        else:
            result.append(item)
    return result
```
