```python
def sort_age(lst):
    for i in range(1,len(lst)):
        while i > 0 and lst[i][1]<lst[i-1][1]:
            lst.pop(i)
            lst.insert(i-1, lst[i])
            i = i - 1
    return lst
```
