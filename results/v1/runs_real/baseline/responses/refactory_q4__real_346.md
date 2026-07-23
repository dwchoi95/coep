```python
def sort_age(lst):
    tup=[]
    for i in lst:
        current=0
        while current<len(tup) and tup[current][1]>i[1]:
            current+=1
        tup.insert(current,i)
    return tup
```
