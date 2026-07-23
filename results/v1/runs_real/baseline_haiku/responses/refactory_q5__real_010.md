```python
def top_k(lst, k):
    n = len(lst) - k
    counter = 0
    while counter < n:
        lst.remove(min(lst))
        counter = counter + 1
    sort_list = []
    while lst != []:
        sort_list.append(max(lst))
        lst.remove(max(lst))
    return sort_list
```
