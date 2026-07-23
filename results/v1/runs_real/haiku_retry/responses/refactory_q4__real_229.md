```python
def sort_age(lst):
    for _ in range(len(lst)):
        oldest = lst[0]
        for item in lst:
            if item[1] > oldest[1]:
                oldest = item
        lst.remove(oldest)
        lst = [oldest] + lst
    return lst
```
