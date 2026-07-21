```python
def balanced_brackets(s):
    depth = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for c in s:
        if c in "([{":
            depth.append(c)
        elif c in ")]}":
            if not depth:
                return False
            if depth.pop() != pairs[c]:
                return False
    return depth == []
```
