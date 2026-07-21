```python
def top_k(lst, k):
    uniq = sorted(lst, reverse=True)
    return uniq[:k]
```
