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
        new.append(lst[counter])
        lst.remove(lst[counter])
        
    return new
```
