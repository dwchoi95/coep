```python
def search(x, seq):
    enumerated_list=enumerate(seq)
    for i,elem in enumerated_list:
        if x<=elem:
            return i
    return len(seq)
```
