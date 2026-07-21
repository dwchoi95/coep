```python
def sort_list(lst):
    new = []
    while lst:
        biggest = lst[0]
        for i in lst:
            if i > biggest:
                biggest = i
        lst.remove(biggest)
        new.append(biggest)
    return new

def top_k(lst, k):
    a = sort_list(lst)
    return a[0:k]
```
