```python
def sort_age(lst):
    if lst == []:
        return []
    new = []
    small = lst[0]
    for i in range(1,len(lst)):
        if lst[i][1]>small[1]:
            small = lst[i]
    new.append(small)
    lst.remove(small)
    return sort_age(lst)
```
