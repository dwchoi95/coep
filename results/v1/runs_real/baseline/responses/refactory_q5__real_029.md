```python
def top_k(lst, k):
    sorted_list = []
    while lst:
        smallest = lst[0]
        for element in lst:
            if element < smallest:
                smallest = element
        lst.remove(smallest)
        sorted_list.append(smallest)
    list.reverse(sorted_list)
    return sorted_list[:k]
```
