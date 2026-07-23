```python
def sort_age(lst):
    if not lst:
        return []
    first = lst[0]
    result = [first]
    for x in lst[1:]:
        for i in range(len(result)):
            if x[1] > result[i][1]:
                result = result[:i] + [x] + result[i:]
                break
        else:
            result = result + [x]
    return result
```
