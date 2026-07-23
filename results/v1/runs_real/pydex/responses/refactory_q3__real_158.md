```python
def remove_extras(lst):
    new_lst = lst[::-1]
    for i in lst:
        n = new_lst.count(i)
        while True:
            if n <= 1:
                break
            else:
                new_lst.remove(i)
                n -= 1
    return new_lst[::-1]
```
