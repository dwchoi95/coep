```python
def sort_age(lst):
    list1 = []
    while lst:
        smallest = lst[0][1]
        s = (lst[0],)
        for i in range(1, len(lst)):
            if lst[i][1] < smallest:
                smallest = lst[i][1]
                s = (lst[i],)
        lst.remove(s[0])
        list1 = list(s) + list1
    return list1
```
