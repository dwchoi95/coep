```python
def search(x, seq):
    for i in range(len(seq) - 1):
        if seq[i] < x < seq[i+1]:
            return i+1
    return sum(v < x for v in seq)
```
