```python
def sort_age(lst):
    for i in range(1,len(lst)):
        while i > 0 and lst[i][1]<lst[i-1][1]:
            item = lst.pop(i)
            lst.insert(i-1,item)
            i -= 1
    lst.reverse()
    return lst
```
