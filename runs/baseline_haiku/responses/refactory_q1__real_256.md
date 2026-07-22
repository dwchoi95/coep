```python
def search(x, seq):
    i = 0
    while i < len(seq):
        if x <= seq[i]:
            return i
        i = i + 1
    return len(seq)
```
