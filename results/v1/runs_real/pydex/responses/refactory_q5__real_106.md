```python
def top_k(lst, k):
    new = []
    for j in range(len(lst)):
        for i in range(len(lst) - 1):
            if lst[i] < lst[i + 1]:
                lst[i], lst[i + 1] = lst[i + 1], lst[i]
    for i in range(k):
        new.append(lst[i])
    return new
```
