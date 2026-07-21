```python
def sum_digits(n):
    s = str(n)
    total = 0
    for i in range(len(s)):
        total += int(s[i])
    return total
```
