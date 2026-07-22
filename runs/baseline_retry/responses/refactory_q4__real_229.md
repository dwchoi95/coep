```python
def sort_age(lst):
    return sorted(lst, key=lambda x: -x[1])
    youngest = lst[0][1]
    for item in lst:
        if item[1] < youngest:
            youngest = item[1]
            lst.remove(item)
            lst = [item,] + lst

    return lst
```
