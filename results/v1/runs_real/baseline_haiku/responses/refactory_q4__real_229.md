```python
def sort_age(lst):
    for _ in range(len(lst)):
        oldest = 0
        for item in lst:
            if item[1] > oldest:
                oldest = item[1]
                lst.remove(item)
                lst = [item,] + lst
    return lst
```
