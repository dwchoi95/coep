```python
def flatten(nested):
    result = []
    num = ""
    for ch in str(nested):
        if ch.isdigit() or ch == "-":
            num += ch
        else:
            if num:
                result.append(int(num))
            num = ""
    if num:
        result.append(int(num))
    return result
```
