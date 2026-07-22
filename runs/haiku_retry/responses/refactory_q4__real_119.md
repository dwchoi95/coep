```python
def sort_age(lst):
    result = []
    while lst:
        first = lst[0][1]
        oldest = lst[0]
        for x in lst:
            if x[1] > first:
                first = x[1]
                oldest = x
        lst.remove(oldest)
        result.append(oldest)
    return result
```
