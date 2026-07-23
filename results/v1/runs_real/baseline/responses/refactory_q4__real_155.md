```python
def sort_age(lst):
    new = []
    while lst:
        curr = lst[0][1]
        counter = 0
        for i in range(len(lst)):
            if lst[i][1]>curr:
                curr = lst[i][1]
                counter = i
        person = lst[counter]
        lst.remove(person)
        new.append(person)
        
    return new
```
