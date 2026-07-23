```python
def search(x, seq):
    if len(seq) == 0 or x > max(seq):
        return len(seq)
    else:
        for i in range(len(seq)):
            if x <= seq[i]:
                return i
                break
            else:
                continue
```
