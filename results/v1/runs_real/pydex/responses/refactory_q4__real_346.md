```python
def sort_age(lst):
    tup=[]
    while lst:
        current=lst[0]
        for i in lst:
            if i[1]>current[1]:
                current=i
        lst.remove(current)
        tup.append(current)
    return tup
```
