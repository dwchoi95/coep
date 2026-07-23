```python
def sort_age(lst):
    result = []
    while lst:
        first = lst[0]
        for x in lst:
            if x[1] > first[1]:
                first = x
        lst.remove(first)
        result.append(first)
    return result
```
