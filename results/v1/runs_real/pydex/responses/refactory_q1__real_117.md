```python
def search(x, seq):
    if len(seq) == 0:
        return 0
    if x > seq[-1]:
        return len(seq)
    else:
        for i, elem in enumerate(seq):
            if elem >= x:
                return i
    return
```
