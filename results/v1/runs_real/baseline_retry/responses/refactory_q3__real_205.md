```python
def remove_extras(lst):
    for i in reversed(range(len(lst))):
        for j in lst[0:i]:
            if lst[i] == j:
                del lst[i]
                break
            else:
                continue
    return lst
    pass
```
