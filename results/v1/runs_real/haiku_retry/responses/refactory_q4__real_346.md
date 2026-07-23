```python
def sort_age(lst):
    result = []
    while lst:
        current=0
        max_item = None
        for i in lst:
            if i[1]>current:
                current = i[1]
                max_item = i
        result.append(max_item)
        lst.remove(max_item)
    return result
```
