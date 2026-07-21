```python
def sort_list(lst):
    result = []
    while lst:
        biggest = lst[0]
        for n in lst:
            if n > biggest:
                biggest = n
        lst.remove(biggest)
        result.append(biggest)
    return result

def top_k(lst, k):
    a = sort_list(lst)
    return a[0:k]
```
