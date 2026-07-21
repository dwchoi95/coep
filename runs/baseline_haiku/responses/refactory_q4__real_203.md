```python
def sort_age(lst):
    sort = []
    while len(lst) > 0:
        smallest = lst[0]
        for i in lst:
            if i[1] > smallest[1]:
                smallest = i
        
        lst.remove(smallest)
        sort.append(smallest)
    return sort
```
