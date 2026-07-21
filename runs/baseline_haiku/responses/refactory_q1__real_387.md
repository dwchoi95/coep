```python
def search(x, seq):
    for i in range(len(seq)):
        if seq[i] < x:
            continue
        elif x <= seq[i]:
            return i
        else:
            return len(seq)+1
    return len(seq)
```
