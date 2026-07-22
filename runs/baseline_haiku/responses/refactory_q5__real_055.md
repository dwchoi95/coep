```python
def top_k(lst, k):
    values = []
    greatest = lst[0]
    while len(values) < k and len(lst) > 0:
        for item in lst:
            if item > greatest:
                greatest = item
        lst.remove(greatest)
        values.append(greatest)
        if len(lst) > 0:
            greatest = lst[0]
    return values
```
