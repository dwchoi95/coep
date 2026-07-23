```python
def search(x, seq):
    if not seq:
        return 0
    for i in range(0, len(seq)):
        if seq[i] < x:
            continue
        elif seq[len(seq) - 1] < x:
            return len(seq)
        else:
            return i
    return len(seq)
```
