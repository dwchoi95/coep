```python
def search(x, seq):
    if len(seq) == 0:
        return 0
    if x < seq[0]:
        return 0
    else:
        y = len(seq)
        for i in range(y-1):
            if x > seq[i] and x <= seq[i+1]:
                return i + 1
        return y
```
