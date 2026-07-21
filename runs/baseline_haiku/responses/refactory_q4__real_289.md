```python
def sort_age(lst):
    new_list=[]
    while lst:
        largest=lst[0][1]
        person=lst[0]
        for i in lst:
            if i[1]>largest:
                largest = i[1]
                person=i
        new_list.append(person)
        lst.remove(person)
    return new_list
```
