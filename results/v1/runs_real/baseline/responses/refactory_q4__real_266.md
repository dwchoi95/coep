```python
def sort_age(lst):
    sort = []
    while lst:
        smallest = lst[0]
        for x in lst:
            if x[1] > smallest[1]:
                smallest = x
        lst.remove(smallest)
        sort.append(smallest)
    return sort
```
