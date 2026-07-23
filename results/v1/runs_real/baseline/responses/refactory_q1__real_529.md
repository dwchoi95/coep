```python
def search(x, seq):
    counter = -1
    if len(seq) == 0:
        return 0
    for i in seq:
        if x <= i:
            counter += 1
            return counter
        else:
            counter += 1
    if x > seq[counter]:
        return counter + 1
```
