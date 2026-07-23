```python
def unique_in_order(lst):
    result = []
    for i in range(len(lst)):
        if i == 0 or lst[i] != lst[i - 1]:
            result.append(lst[i])
    return result
```
