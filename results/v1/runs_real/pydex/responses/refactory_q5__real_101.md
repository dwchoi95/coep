```python
def top_k(lst, k):
    s = sort(lst)
    return s[:k]

def sort(lst):
    sort=[]
    while lst:
        largest=lst[0]
        for elem in lst:
            if elem > largest:
                largest = elem
        lst.remove(largest)
        sort.append(largest)
    return sort
```
