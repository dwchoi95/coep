```python
def search(x, seq):
    for i in range(len(seq)):
        if seq[i] < x:
            continue
        elif x <= seq[i]:
            return i
    return len(seq)
```
