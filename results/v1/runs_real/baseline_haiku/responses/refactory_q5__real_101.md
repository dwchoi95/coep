```python
def top_k(lst, k):
    sort_result = sort(lst)
    return sort_result[:k]

def sort(lst):
    sort_list = []
    while lst:
        largest = lst[0]
        for elem in lst:
            if elem > largest:
                largest = elem
        lst.remove(largest)
        sort_list.append(largest)
    return sort_list
```
