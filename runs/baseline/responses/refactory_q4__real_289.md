```python
def sort_age(lst):
    new_list=[]
    while lst:
        largest=lst[0]
        for i in lst:
            if i[1]>largest[1]:
                largest = i
        new_list.append(largest)
        lst.remove(largest)
    return new_list
```
