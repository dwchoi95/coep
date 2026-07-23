```python
def sort_age(lst):
    result = []
    while lst:
        first = lst[0][1]
        max_person = lst[0]
        for x in lst:
            if x[1] > first:
                first = x[1]
                max_person = x
        result.append(max_person)
        lst.remove(max_person)
    return result
```
