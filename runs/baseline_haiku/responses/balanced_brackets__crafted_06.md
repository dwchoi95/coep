```python
def balanced_brackets(s):
    depth = 0
    for c in s:
        if c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                return False
            depth -= 1
    return depth == 0
```
