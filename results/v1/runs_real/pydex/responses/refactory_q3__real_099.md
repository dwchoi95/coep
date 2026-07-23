```python
def remove_extras(lst):
    new_lst = []
    for item in lst:
        if new_lst.count(item) != 1:
            new_lst.append(item)
    return new_lst
```
