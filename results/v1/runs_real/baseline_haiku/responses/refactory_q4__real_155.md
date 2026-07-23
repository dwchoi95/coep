```python
def sort_age(lst):
    new = []
    while lst:
        curr = lst[0]
        for i in range(len(lst)):
            if lst[i][1]>curr[1]:
                curr = lst[i]
        lst.remove(curr)
        new.append(curr)
    return new
```
