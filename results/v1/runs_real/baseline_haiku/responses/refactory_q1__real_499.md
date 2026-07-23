```python
def search(x, seq):
    seq = tuple(seq)
    if len(seq) == 0:
        return 0
    elif x > seq[len(seq)-1]:
        return len(seq)
    else:
        i = 0
        while i <= len(seq)-1:
            if x <= seq[i]:
                return i
            elif x > seq[i]:
                i += 1
```
