```python
def top_k(lst, k):
    arranged = []
    while k>0:
        arranged.append(max(lst))
        lst.remove(max(lst))
        k -= 1
    return arranged
```
