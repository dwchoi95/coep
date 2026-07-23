```python
def top_k(lst, k):
    new = []
    n = len(lst)
    while len(lst) > n - k:
        top = max(lst) 
        new.append(top)
        lst.remove(top)
        
    return new
```
