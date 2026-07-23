```python
def search(x, seq):
    for i in range(len(seq)):
        if x <= seq[i]:
            return i
        elif seq[-1] < x:
            return len(seq)
    return 0
```
