```python
def sort_age(lst):
    current=0
    tup=[]
    for i in lst:
        if i[1]>current:
            tup.append(i)
            current=i[1]
        else:
            tup.insert(0, i)
    return tup
```
