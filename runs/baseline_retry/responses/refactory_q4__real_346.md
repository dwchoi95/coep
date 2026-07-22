```python
def sort_age(lst):
    return sorted(lst, key=lambda x: -x[1])
    current=0
    tup=()
    for i in lst:
        if i[1]>current:
            tup+=tuple(i)
            current=i[1]
        else:
            tup=tuple(i)+tup
    return tup
```
