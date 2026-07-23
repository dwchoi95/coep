```python
def search(x, seq):
    if not seq:
        return 0
    if x <= seq[0]:
        return 0
    elif x > seq[len(seq)-1]:
        return len(seq)
    counter = 0
    for i in seq:
        counter = counter + 1
        if x > seq[counter]:
            continue
        elif x <= seq[counter]:
            return counter
```
