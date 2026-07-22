```python
def sort_age(lst):
    newlst=[]
    while lst:
        maximum = lst[0][1]
        max_item = lst[0]
        for i in lst:
            if i[1]>maximum:
                maximum = i[1]
                max_item = i
        newlst.append(max_item)
        lst.remove(max_item)

    return newlst
```
