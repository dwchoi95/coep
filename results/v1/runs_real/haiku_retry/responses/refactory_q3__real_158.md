```python
def remove_extras(lst):
    new_lst = lst.copy()
    for i in lst:
        n = new_lst.count(i)
        while True:
            if n <= 1:
                break
            else:
                idx = len(new_lst) - 1 - new_lst[::-1].index(i)
                new_lst.pop(idx)
                n -= 1
    return new_lst
```
