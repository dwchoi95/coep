```python
def remove_extras(lst):
    keep = []
    remove = []
    for i in lst :
        if i not in keep :
            keep.append(i)
        else :
            remove.append(i)
    return keep

    pass
```
