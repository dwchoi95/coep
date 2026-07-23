```python
def sort_age(lst):
    result = []
    while lst:
        youngest = lst[0]
        for item in lst:
            if item[1] < youngest[1]:
                youngest = item
        lst.remove(youngest)
        result = [youngest,] + result
    return result
```
