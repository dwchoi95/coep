```python
def sort_age(lst):
    sort=[]
    while lst:
        biggest=lst[0][1]
        person=lst[0]
        for i in lst:
            if i[1]>biggest:
                biggest=i[1]
                person=i
        lst.remove(person)
        sort.append(person)
    return sort
```
