```python
def top_k(lst, k):
    lst2 = []
    for _ in range(k):
        if lst:
            max = lst[0]
            for i in lst:
                if i > max:
                    max = i
            lst.remove(max)
            lst2.append(max)
    return lst2
```
