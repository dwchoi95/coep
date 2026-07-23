```python
def sort_age(lst):
    new_list=[]
    while lst:
        largest=lst[0][1]
        i_max = lst[0]
        for i in lst:
            if i[1]>largest:
                largest = i[1]
                i_max = i
        new_list.append(i_max)
        lst.remove(i_max)
    return new_list
```
