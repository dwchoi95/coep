```python
def top_k(lst, k):
    if lst == []:
        return []
    else:
        final = []
        while lst:
            if len(final) == k:
                break
            element = max(lst)
            final += [element,]
            lst.remove(element)
        return final
```
