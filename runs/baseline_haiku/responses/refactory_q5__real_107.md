```python
def top_k(lst, k):

    newlst = []
    for i in range(k):
        if lst:
            newlst.append(max(lst))
            lst.remove(max(lst))
    return newlst
```
