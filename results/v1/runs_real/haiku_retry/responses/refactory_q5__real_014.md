```python
def top_k(lst, k):
    
    if lst == []:
        return lst
    
    lower = []
    higher = []
    plist = []
    
    pivot = lst[0]
    for e in lst:
        if e < pivot:
            lower.append(e)
        if e == pivot:
            plist.append(e)
        if e > pivot:
            higher.append(e)
    
    sorted_higher = top_k(higher, len(higher))
    sorted_lower = top_k(lower, len(lower))
    sort_list = sorted_higher + plist + sorted_lower
    
    return sort_list[:k]
```
