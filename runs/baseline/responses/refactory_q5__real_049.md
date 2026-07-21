```python
def top_k(lst, k):
    sorted_lst = []
    while lst:
        biggest = lst[0]
        for n in lst:
            if n >= biggest:
                biggest = n
        lst.remove(biggest)
        sorted_lst.append(biggest)
    return sorted_lst[0:k]
```
