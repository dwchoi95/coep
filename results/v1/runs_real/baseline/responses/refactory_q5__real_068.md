```python
def top_k(lst, k):
    new = []
    for i in range(k):
        new.append(lst.pop(lst.index(max(lst))))

    return new
```
