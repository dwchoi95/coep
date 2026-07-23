```python
def sort_age(lst):
    sort=[]
    while lst:
        smallest = lst[0]
        for i in range (1,len(lst)):
            if lst[i][1] > smallest[1]:
                smallest = lst[i]
        lst.remove(smallest)
        sort.append(smallest)
    return sort
```
