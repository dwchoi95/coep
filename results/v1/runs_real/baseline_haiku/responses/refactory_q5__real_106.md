```python
def top_k(lst, k):
    new = []
    for i in range(len(lst)):
        for j in range(len(lst) - 1):
            if lst[j] < lst[j + 1]:
                lst[j], lst[j + 1] = lst[j + 1], lst[j]
    for i in range(k):
        new.append(lst[i])
    return new
```
