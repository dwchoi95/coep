```python
def search(x, seq):
    if len(seq) == 0:
        return 0
    elif seq == ():
        return 0
    else:
        for element in seq:
            if x <= element:
                return list(seq).index(element)
            elif x >= max(seq):
                return (list(seq).index(max(seq)))+1
```
