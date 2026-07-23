```python
def sort_age(lst):
    l = len(lst)
    for i in range(l):
        largest = lst[i]
        for j in range(i+1,l):
            if lst[j][1] > largest[1]:
                lst[i],lst[j] = lst[j],lst[i]
                largest = lst[i]
    return lst
```
