```python
def top_k(lst, k):
    new = []
    lst.sort()
    lst.reverse()
    for i in range(k):
        new.append(lst[i])
    return new
```
