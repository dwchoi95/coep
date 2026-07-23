```python
def search(x, seq):
    if seq == ():
        return 0
    else:
        for element in seq:
            if x <= element:
                return list(seq).index(element)
    return len(seq)
```
