```python
def balanced_brackets(s):
    opens = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for c in s:
        if c in "([{":
            opens.append(c)
        elif c in ")]}":
            if not opens or opens.pop() != pairs[c]:
                return False
    return opens == []
```
