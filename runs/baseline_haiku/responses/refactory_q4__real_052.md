```python
def sort_age(lst):
    newlst=[]
    while lst:
        oldest = lst[0][1]
        person_oldest = lst[0]
        for person in lst:
            if person[1]>oldest:
                oldest=person[1]
                person_oldest=person
        newlst.append(person_oldest)
        lst.remove(person_oldest)
    return newlst
```
