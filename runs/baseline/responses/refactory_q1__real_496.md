```python
def search(x, seq):
    length = len(seq)
    for i, elem in enumerate(seq):
        if x < elem:
            return i
        else:
            if x == elem:
                return i
            if (i == length-1):
                return i+1
    return length
```
